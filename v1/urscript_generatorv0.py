# -*- coding: utf-8 -*-
"""
urscript_generator.py
=====================
Genera los dos programas URScript para el sistema de dibujo colaborativo.

Robot 1 — UR3e:
  1. Lee joints actuales → guarda como HOME
  2. Detecta mesa con force_mode
  3. Dibuja sus trayectorias
  4. Vuelve a HOME
  5. Abre socket TCP hacia el UR5e y envía "LISTO" (visible en log tablet)

Robot 2 — UR5e:
  1. Lee joints actuales → guarda como HOME
  2. Espera mensaje "LISTO" en un socket servidor (puerto PORT_SYNC)
     Mientras espera, hace un textmsg cada segundo visible en la tablet.
  3. Detecta mesa con force_mode
  4. Dibuja sus trayectorias
  5. Vuelve a HOME

Estrategia de Z (igual que proyecto single-robot):
  - URScript guarda SOLO z_mesa como escalar.
  - Todos los offsets de Z están resueltos en Python como literales.
  - No hay aritmética de poses en URScript → imposible corrupción por aliasing.
"""

import logging
from typing import List, Tuple

from config_v0 import (
    V_BAJA, V_DIBUJO, V_SUBIDA, A_DIBUJO,
    Z_SUBIDA, Z_PAPEL, F_UMBRAL,
    V_HOME, A_HOME,
    UR5E_IP, PORT_SYNC, SYNC_TIMEOUT, SYNC_MSG,
)

log = logging.getLogger(__name__)

Punto       = Tuple[float, float]
Trayectoria = List[Punto]

_Z_PAPEL  = float(Z_PAPEL)
_Z_AIRE   = float(Z_PAPEL + Z_SUBIDA)
_Z_REPOSO = float(Z_PAPEL + 0.05)


# =============================================================================
# BLOQUE COMPARTIDO: DETECCIÓN DE MESA
# =============================================================================
def _bloque_detectar_mesa() -> List[str]:
    """
    Detecta la mesa bajando con speedl, sin force_mode.
    Evita el error de singularidad del UR3e.
    Resultado: x0, y0, z_mesa, rx, ry, rz.
    """
    L = []
    L.append("  # === FASE 1: Detectar mesa sin force_mode ===")
    L.append("  zero_ftsensor()")
    L.append("  sleep(0.5)")
    L.append('  textmsg("Bajando a detectar mesa...")')
    L.append("")
    L.append("  i = 0")
    L.append("  max_iter = 3500")
    L.append(f"  v_baja = {V_BAJA}")
    L.append(f"  f_umbral = {F_UMBRAL}")
    L.append("")
    L.append("  while (get_tcp_force()[2] < f_umbral) and (get_tcp_force()[2] > -f_umbral) and (i < max_iter):")
    L.append("    speedl([0, 0, -v_baja, 0, 0, 0], 0.03, 0.02)")
    L.append("    i = i + 1")
    L.append("  end")
    L.append("")
    L.append("  if i >= max_iter:")
    L.append('    popup("No se detecto contacto con la mesa. Abortando.", error=True)')
    L.append("    halt")
    L.append("  end")
    L.append("")
    L.append("  stopl(1.0)")
    L.append("  sleep(0.1)")
    L.append("  p_mesa = get_actual_tcp_pose()")
    L.append("")
    L.append("  x0     = p_mesa[0]")
    L.append("  y0     = p_mesa[1]")
    L.append("  z_mesa = p_mesa[2]")
    L.append("  rx     = p_mesa[3]")
    L.append("  ry     = p_mesa[4]")
    L.append("  rz     = p_mesa[5]")
    L.append("")
    L.append('  textmsg("Mesa detectada. z_mesa = ", z_mesa)')
    L.append("")
    L.append(f"  movel(p[x0, y0, z_mesa+{_Z_PAPEL:.5f}, rx, ry, rz], a=0.03, v=0.003)")
    L.append("  sleep(0.2)")
    L.append(f"  movel(p[x0, y0, z_mesa+{_Z_AIRE:.5f}, rx, ry, rz], a=0.08, v={V_SUBIDA})")
    L.append("")
    return L


# =============================================================================
# BLOQUE COMPARTIDO: DIBUJAR TRAYECTORIAS
# =============================================================================
def _bloque_dibujar(trayectorias: List[Trayectoria], nombre_robot: str) -> List[str]:
    """Genera las líneas URScript del bloque de dibujo."""
    L = []
    total = len(trayectorias)
    L.append(f"  # === FASE 2: Dibujo — {nombre_robot} — {total} trazos ===")

    for idx, trayectoria in enumerate(trayectorias):
        if len(trayectoria) < 2:
            continue

        x0_t, y0_t = trayectoria[0]
        x_fin, y_fin = trayectoria[-1]

        L.append("")
        L.append(f"  # --- Trazo {idx + 1} / {total} ---")
        L.append(f'  textmsg("{nombre_robot} — Trazo {idx + 1} de {total}")')

        # Volar al inicio
        L.append(
            f"  movel(p[x0+{x0_t:.5f}, y0+{y0_t:.5f}, z_mesa+{_Z_AIRE:.5f}, rx, ry, rz],"
            f" a={A_HOME}, v={V_SUBIDA})"
        )
        # Bajar al papel
        L.append(
            f"  movel(p[x0+{x0_t:.5f}, y0+{y0_t:.5f}, z_mesa+{_Z_PAPEL:.5f}, rx, ry, rz],"
            f" a=0.01, v=0.0015)"
        )
        # Trazar
        for x, y in trayectoria[1:]:
            L.append(
                f"  movel(p[x0+{x:.5f}, y0+{y:.5f}, z_mesa+{_Z_PAPEL:.5f}, rx, ry, rz],"
                f" a={A_DIBUJO}, v={V_DIBUJO}, r=0.0005)"
            )
        # Subir desde el último punto conocido
        L.append(
            f"  movel(p[x0+{x_fin:.5f}, y0+{y_fin:.5f}, z_mesa+{_Z_AIRE:.5f}, rx, ry, rz],"
            f" a={A_HOME}, v={V_SUBIDA})"
        )

    L.append("")
    L.append(f'  textmsg("{nombre_robot} — Dibujo completado.")')
    return L


# =============================================================================
# SCRIPT UR3e
# =============================================================================
def generar_script_ur3e(trayectorias: List[Trayectoria]) -> str:
    """
    Genera el URScript completo para el UR3e.

    Flujo:
      HOME guardado → detectar mesa → dibujar → volver a HOME → avisar a UR5e
    """
    trayectorias = [t for t in trayectorias if len(t) >= 2]
    if not trayectorias:
        raise ValueError("UR3e: no hay trayectorias con al menos 2 puntos.")

    log.info(f"Generando script UR3e — {len(trayectorias)} trayectorias")

    L = []
    L.append("def ur3e_dibujar():")
    L.append(f'  textmsg("=== UR3e: inicio del programa ===")')
    L.append("")

    # --- Guardar HOME (joints actuales) ---
    L.append("  # Guardar posición actual como HOME")
    L.append("  q_home = get_actual_joint_positions()")
    L.append(f'  textmsg("UR3e HOME guardado: ", q_home)')
    L.append("")

    # --- Fase 1: detectar mesa ---
    L.extend(_bloque_detectar_mesa())

    # --- Fase 2: dibujar ---
    L.extend(_bloque_dibujar(trayectorias, "UR3e"))

    # --- Volver a HOME ---
    L.append("  # === Volver a HOME ===")
    L.append(f'  textmsg("UR3e — Volviendo a HOME...")')
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")
    L.append(f'  textmsg("UR3e — En HOME. Avisando al UR5e...")')
    L.append("")

    # --- Avisar al UR5e por socket ---
    # El robot abre una conexión TCP hacia el UR5e en PORT_SYNC y envía SYNC_MSG.
    # Esto queda registrado en la tablet del UR3e como textmsg.
    L.append("  # === Avisar al UR5e (socket directo robot→robot) ===")
    L.append(f'  textmsg("UR3e → Abriendo socket hacia UR5e {UR5E_IP}:{PORT_SYNC}")')
    L.append(f"  socket_open(\"{UR5E_IP}\", {PORT_SYNC})")
    L.append(f'  socket_send_string("{SYNC_MSG}")')
    L.append("  sleep(0.5)")
    L.append("  socket_close()")
    L.append(f'  textmsg("UR3e → Mensaje LISTO enviado al UR5e. Programa terminado.")')
    L.append(f'  textmsg("UR3e — Programa terminado."')
    L.append("")
    L.append("end")
    L.append("")
    L.append("ur3e_dibujar()")

    return "\n".join(L)


# =============================================================================
# SCRIPT UR5e
# =============================================================================
def generar_script_ur5e(trayectorias: List[Trayectoria]) -> str:
    """
    Genera el URScript completo para el UR5e.

    Flujo:
      HOME guardado → esperar socket del UR3e → detectar mesa → dibujar → HOME
    """
    trayectorias = [t for t in trayectorias if len(t) >= 2]
    if not trayectorias:
        raise ValueError("UR5e: no hay trayectorias con al menos 2 puntos.")

    log.info(f"Generando script UR5e — {len(trayectorias)} trayectorias")

    L = []
    L.append("def ur5e_dibujar():")
    L.append(f'  textmsg("=== UR5e: inicio del programa — esperando aviso del UR3e ===")')
    L.append("")

    # --- Guardar HOME ---
    L.append("  # Guardar posición actual como HOME")
    L.append("  q_home = get_actual_joint_positions()")
    L.append(f'  textmsg("UR5e HOME guardado: ", q_home)')
    L.append("")

    # --- Esperar aviso del UR3e ---
    # El UR5e actúa como servidor: abre un socket_server en PORT_SYNC
    # y espera hasta recibir el mensaje SYNC_MSG del UR3e.
    # Un contador muestra en la tablet que está esperando (visible en log).
    L.append("  # === Esperar aviso del UR3e (servidor socket) ===")
    L.append(f"  socket_open(\"0.0.0.0\", {PORT_SYNC}, \"sync_server\")")
    L.append(f'  textmsg("UR5e → Escuchando en puerto {PORT_SYNC}. Esperando UR3e...")')
    L.append("")
    L.append(f"  timeout_max = {SYNC_TIMEOUT}")
    L.append("  t = 0")
    L.append("  recibido = False")
    L.append("")
    L.append("  while t < timeout_max:")
    L.append(f'    msg = socket_read_string(\"sync_server\", timeout=1.0)')
    L.append(f'    if msg == "{SYNC_MSG}":')
    L.append(f'      textmsg("UR5e → Recibido LISTO del UR3e. Comenzando dibujo.")')
    L.append("      recibido = True")
    L.append("      t = timeout_max  # salir del bucle")
    L.append("    else:")
    L.append("      t = t + 1")
    L.append(f'      if t % 10 == 0:')
    L.append(f'        textmsg("UR5e esperando UR3e, segundos: ", t)')
    L.append("      end")
    L.append("    end")
    L.append("  end")
    L.append("")
    L.append("  socket_close(\"sync_server\")")
    L.append("")
    '''L.append("  if recibido == False:")
    L.append(f'    popup("UR5e: Timeout esperando al UR3e ({SYNC_TIMEOUT}s). Abortando.", error=True)')
    L.append("    halt")
    L.append("  end")'''

    L.append("  # === Espera simple antes de empezar ===")
    L.append('  textmsg("UR5e esperando 25 segundos antes de empezar...")')
    L.append("  sleep(300.0)")
    L.append('  textmsg("UR5e empieza dibujo.")')
    L.append("")

    # --- Fase 1: detectar mesa ---
    L.extend(_bloque_detectar_mesa())

    # --- Fase 2: dibujar ---
    L.extend(_bloque_dibujar(trayectorias, "UR5e"))

    # --- Volver a HOME ---
    L.append("  # === Volver a HOME ===")
    L.append(f'  textmsg("UR5e — Volviendo a HOME...")')
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")
    L.append(f'  textmsg("UR5e — En HOME. Programa completado.")')
    L.append("")
    L.append("end")
    L.append("")
    L.append("ur5e_dibujar()")

    return "\n".join(L)


def guardar_script(script: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    log.info(f"URScript guardado en: {path}")
