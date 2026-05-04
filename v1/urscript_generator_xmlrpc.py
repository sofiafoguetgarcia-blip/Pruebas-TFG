# -*- coding: utf-8 -*-
"""
urscript_generator.py
=====================
Genera URScript para UR3e + UR5e con sincronización XML-RPC vía PC.

UR5e:
  - guarda HOME
  - crea cliente XML-RPC hacia el PC
  - espera hasta que can_ur5_start() devuelva 1
  - dibuja

UR3e:
  - guarda HOME
  - dibuja
  - vuelve a HOME
  - llama ur3_done() al PC por XML-RPC
"""

import logging
from typing import List, Tuple

from config_xmlrpc import (
    V_BAJA, V_DIBUJO, V_SUBIDA, A_DIBUJO,
    Z_SUBIDA, Z_PAPEL, F_UMBRAL,
    V_HOME, A_HOME,
    SYNC_TIMEOUT,
    PC_IP, XMLRPC_PORT,
)

log = logging.getLogger(__name__)

Punto = Tuple[float, float]
Trayectoria = List[Punto]

_Z_PAPEL = float(Z_PAPEL)
_Z_AIRE = float(Z_PAPEL + Z_SUBIDA)
_XMLRPC_URL = f"http://{PC_IP}:{XMLRPC_PORT}/RPC2"


# =============================================================================
# BLOQUE COMPARTIDO: DETECCIÓN DE MESA SIN FORCE_MODE
# =============================================================================
def _bloque_detectar_mesa() -> List[str]:
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
    L.append('  textmsg("Mesa detectada. z_mesa=", z_mesa)')
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
    L = []
    total = len(trayectorias)
    L.append(f"  # === FASE 2: Dibujo {nombre_robot} - {total} trazos ===")

    for idx, trayectoria in enumerate(trayectorias):
        if len(trayectoria) < 2:
            continue

        x0_t, y0_t = trayectoria[0]
        x_fin, y_fin = trayectoria[-1]

        L.append("")
        L.append(f"  # --- Trazo {idx + 1} / {total} ---")
        L.append(f'  textmsg("{nombre_robot} trazo {idx + 1} de {total}")')

        L.append(
            f"  movel(p[x0+{x0_t:.5f}, y0+{y0_t:.5f}, z_mesa+{_Z_AIRE:.5f}, rx, ry, rz],"
            f" a={A_HOME}, v={V_SUBIDA})"
        )
        L.append(
            f"  movel(p[x0+{x0_t:.5f}, y0+{y0_t:.5f}, z_mesa+{_Z_PAPEL:.5f}, rx, ry, rz],"
            f" a=0.01, v=0.0015)"
        )

        for x, y in trayectoria[1:]:
            L.append(
                f"  movel(p[x0+{x:.5f}, y0+{y:.5f}, z_mesa+{_Z_PAPEL:.5f}, rx, ry, rz],"
                f" a={A_DIBUJO}, v={V_DIBUJO}, r=0.0005)"
            )

        L.append(
            f"  movel(p[x0+{x_fin:.5f}, y0+{y_fin:.5f}, z_mesa+{_Z_AIRE:.5f}, rx, ry, rz],"
            f" a={A_HOME}, v={V_SUBIDA})"
        )

    L.append("")
    L.append(f'  textmsg("{nombre_robot} dibujo completado")')
    return L


# =============================================================================
# SCRIPT UR3e
# =============================================================================
def generar_script_ur3e(trayectorias: List[Trayectoria]) -> str:
    trayectorias = [t for t in trayectorias if len(t) >= 2]
    if not trayectorias:
        raise ValueError("UR3e: no hay trayectorias con al menos 2 puntos.")

    log.info(f"Generando script UR3e - {len(trayectorias)} trayectorias")

    L = []
    L.append("def ur3e_dibujar():")
    L.append('  textmsg("=== UR3e inicio ===")')
    L.append("")
    L.append("  q_home = get_actual_joint_positions()")
    L.append('  textmsg("UR3e HOME guardado")')
    L.append("")

    L.extend(_bloque_detectar_mesa())
    L.extend(_bloque_dibujar(trayectorias, "UR3e"))

    L.append("  # === Volver a HOME ===")
    L.append('  textmsg("UR3e volviendo a HOME")')
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")
    L.append("")

    L.append("  # === Avisar al PC por XML-RPC ===")
    L.append(f'  textmsg("UR3e conectando XML-RPC PC")')
    L.append(f'  sync = rpc_factory("xmlrpc", "{_XMLRPC_URL}")')
    L.append("  ok = sync.ur3_done()")
    L.append('  textmsg("UR3e aviso enviado al PC", ok)')
    L.append('  textmsg("UR3e programa terminado")')
    L.append("end")
    L.append("")
    L.append("ur3e_dibujar()")
    return "\n".join(L)


# =============================================================================
# SCRIPT UR5e
# =============================================================================
def generar_script_ur5e(trayectorias: List[Trayectoria]) -> str:
    trayectorias = [t for t in trayectorias if len(t) >= 2]
    if not trayectorias:
        raise ValueError("UR5e: no hay trayectorias con al menos 2 puntos.")

    log.info(f"Generando script UR5e - {len(trayectorias)} trayectorias")

    L = []
    L.append("def ur5e_dibujar():")
    L.append('  textmsg("=== UR5e inicio: esperando PC ===")')
    L.append("")
    L.append("  q_home = get_actual_joint_positions()")
    L.append('  textmsg("UR5e HOME guardado")')
    L.append("")

    L.append("  # === Esperar permiso del PC por XML-RPC ===")
    L.append(f'  sync = rpc_factory("xmlrpc", "{_XMLRPC_URL}")')
    L.append(f"  timeout_max = {SYNC_TIMEOUT}")
    L.append("  t = 0")
    L.append("  start = 0")
    L.append('  textmsg("UR5e esperando can_ur5_start()")')
    L.append("  while (t < timeout_max) and (start == 0):")
    L.append("    start = sync.can_ur5_start()")
    L.append("    if start == 0:")
    L.append("      sleep(1.0)")
    L.append("      t = t + 1")
    L.append("      if t % 10 == 0:")
    L.append('        textmsg("UR5e esperando segundos=", t)')
    L.append("      end")
    L.append("    end")
    L.append("  end")
    L.append("")
    L.append("  if start == 0:")
    L.append('    popup("UR5e timeout esperando START XML-RPC", error=True)')
    L.append("    halt")
    L.append("  end")
    L.append('  textmsg("UR5e autorizado. Empieza dibujo")')
    L.append("")

    L.extend(_bloque_detectar_mesa())
    L.extend(_bloque_dibujar(trayectorias, "UR5e"))

    L.append("  # === Volver a HOME ===")
    L.append('  textmsg("UR5e volviendo a HOME")')
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")
    L.append('  textmsg("UR5e programa terminado")')
    L.append("end")
    L.append("")
    L.append("ur5e_dibujar()")
    return "\n".join(L)


def guardar_script(script: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    log.info(f"URScript guardado en: {path}")
