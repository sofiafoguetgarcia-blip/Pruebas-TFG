# -*- coding: utf-8 -*-
"""
urscript_generator.py
=====================
Genera URScript para dibujo colaborativo UR3e + UR5e.

Comunicación estable:
  - El UR3e avisa al PC cuando termina.
  - El PC, al recibir LISTO, envía entonces el script al UR5e.
  - El UR5e NO abre sockets ni espera como servidor.
"""

import logging
from typing import List, Tuple

from config_solucion import (
    V_BAJA, V_DIBUJO, V_SUBIDA, A_DIBUJO,
    Z_SUBIDA, Z_PAPEL, F_UMBRAL,
    V_HOME, A_HOME,
    PC_IP, PORT_UR3_DONE, SYNC_MSG,
    UR5E_TCP_ORIGEN,
)
from transform_ur5_to_ur3 import convertir_pose_ur5_a_ur3, formatear_pose

log = logging.getLogger(__name__)

Punto = Tuple[float, float]
Trayectoria = List[Punto]

_Z_PAPEL = float(Z_PAPEL)
_Z_AIRE = float(Z_PAPEL + Z_SUBIDA)
_Z_REPOSO = float(Z_PAPEL + 0.05)


# =============================================================================
# BLOQUE: IR A ORIGEN CALIBRADO
# =============================================================================
def _bloque_ir_a_origen_tcp(pose_origen, nombre_robot: str) -> List[str]:
    """
    Lleva el robot al origen calibrado del papel.
    No detecta mesa ni usa force_mode.
    Usa UR3E_TCP_ORIGEN / UR5E_TCP_ORIGEN.
    """
    x, y, z, rx, ry, rz = pose_origen

    L = []
    L.append(f"  # === Ir al origen calibrado del papel: {nombre_robot} ===")
    L.append(f'  textmsg("{nombre_robot} - yendo al origen calibrado")')
    L.append("")
    L.append(f"  x0 = {x:.5f}")
    L.append(f"  y0 = {y:.5f}")
    L.append(f"  z_mesa = {z:.5f}")
    L.append(f"  rx = {rx:.5f}")
    L.append(f"  ry = {ry:.5f}")
    L.append(f"  rz = {rz:.5f}")
    L.append("")
    L.append(f"  movel(p[x0, y0, z_mesa+{_Z_AIRE:.5f}, rx, ry, rz], a={A_HOME}, v={V_HOME})")
    L.append("  sleep(0.2)")
    L.append(f"  movel(p[x0, y0, z_mesa+{_Z_PAPEL:.5f}, rx, ry, rz], a=0.03, v=0.003)")
    L.append("  sleep(0.2)")
    L.append(f"  movel(p[x0, y0, z_mesa+{_Z_AIRE:.5f}, rx, ry, rz], a=0.08, v={V_SUBIDA})")
    L.append("")
    return L


# =============================================================================
# BLOQUE: DIBUJAR TRAYECTORIAS
# =============================================================================
def _bloque_dibujar(trayectorias: List[Trayectoria], nombre_robot: str, espejo_x: bool = False, espejo_y: bool = False) -> List[str]:
    """Genera las líneas URScript del bloque de dibujo."""
    L = []
    total = len(trayectorias)
    L.append(f"  # === FASE 2: Dibujo - {nombre_robot} - {total} trazos ===")

    for idx, trayectoria in enumerate(trayectorias):
        if len(trayectoria) < 2:
            continue

        x0_t, y0_t = trayectoria[0]
        x_fin, y_fin = trayectoria[-1]

        if espejo_x:
            x0_t = -x0_t
            x_fin = -x_fin
        if espejo_y:
            y0_t = -y0_t
            y_fin = -y_fin

        L.append("")
        L.append(f"  # --- Trazo {idx + 1} / {total} ---")
        L.append(f'  textmsg("{nombre_robot} - Trazo {idx + 1} de {total}")')

        # Ir al inicio del trazo por el aire
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
            if espejo_x:
                x = -x
            if espejo_y:
                y = -y
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
    L.append(f'  textmsg("{nombre_robot} - Dibujo completado")')
    return L


# =============================================================================
# SCRIPT UR3e
# =============================================================================
def generar_script_ur3e(trayectorias: List[Trayectoria]) -> str:
    """
    UR3e:
      1. Guarda HOME inicial.
      2. Va al origen calibrado UR3E_TCP_ORIGEN.
      3. Dibuja sus trayectorias.
      4. Vuelve a HOME.
      5. Avisa al PC con LISTO.
    """
    trayectorias = [t for t in trayectorias if len(t) >= 2]
    if not trayectorias:
        raise ValueError("UR3e: no hay trayectorias con al menos 2 puntos.")

    log.info(f"Generando script UR3e — {len(trayectorias)} trayectorias")

    L = []
    L.append("def ur3e_dibujar():")
    L.append('  textmsg("=== UR3e: inicio del programa ===")')
    L.append("")

    L.append("  # Guardar posición actual como HOME")
    L.append("  q_home = get_actual_joint_positions()")
    L.append('  textmsg("UR3e HOME guardado")')
    L.append("")

    # El punto del UR5e está tomado como referencia correcta.
    # Aquí calculamos automáticamente la pose equivalente para el UR3e.
    ur3e_origen_calculado = convertir_pose_ur5_a_ur3(UR5E_TCP_ORIGEN)
    log.info(f"UR3e origen calculado desde UR5e: {formatear_pose(ur3e_origen_calculado)}")

    L.extend(_bloque_ir_a_origen_tcp(ur3e_origen_calculado, "UR3e"))
    L.extend(_bloque_dibujar(trayectorias, "UR3e", espejo_x=False, espejo_y=False))

    L.append("  # === Volver a HOME ===")
    L.append('  textmsg("UR3e - Volviendo a HOME")')
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")
    L.append('  textmsg("UR3e - En HOME. Avisando al PC")')
    L.append("")

    L.append("  # === Avisar al PC de que UR3e ha terminado ===")
    
    # Intentar abrir la conexión (Se asigna el nombre "pc_sync")
    # El éxito se verifica con socket_open() dentro de una variable
    L.append(f'  socket_conn = socket_open("{PC_IP}", {PORT_UR3_DONE}, "pc_sync")')
    
    # En URScript, socket_open devuelve False si falla la conexión física
    L.append("  if (not socket_conn):")
    L.append('    textmsg("UR3e - Error: No se pudo conectar con el PC en la IP: ", "' + str(PC_IP) + '")')
    L.append('    popup("UR3e no pudo conectar con el PC. Verifica el Servidor Python.", error=True)')
    L.append("    halt")
    L.append("  else:")
    # Si conectó, enviamos el mensaje
    L.append(f'    socket_send_string("{SYNC_MSG}", "pc_sync")')
    # Importante: No cerrar inmediatamente, dar tiempo a que los paquetes salgan
    L.append("    sleep(0.2)") 
    L.append('    socket_close("pc_sync")')
    L.append('    textmsg("UR3e - LISTO enviado al PC correctamente")')
    L.append("  end")
    
    L.append("")
    L.append('  textmsg("UR3e - Programa terminado")')
    L.append("end")
    L.append("")
    L.append("ur3e_dibujar()")

    return "\n".join(L)


# =============================================================================
# SCRIPT UR5e
# =============================================================================
def generar_script_ur5e(trayectorias: List[Trayectoria]) -> str:
    """
    UR5e:
      1. Guarda HOME inicial.
      2. Va al origen calibrado UR5E_TCP_ORIGEN.
      3. Dibuja sus trayectorias.
      4. Vuelve a HOME.

    No espera por socket. El PC lo envía solo cuando recibe LISTO del UR3e.
    """
    trayectorias = [t for t in trayectorias if len(t) >= 2]
    if not trayectorias:
        raise ValueError("UR5e: no hay trayectorias con al menos 2 puntos.")

    log.info(f"Generando script UR5e — {len(trayectorias)} trayectorias")

    L = []
    L.append("def ur5e_dibujar():")
    L.append('  textmsg("=== UR5e: inicio del programa ===")')
    L.append("")

    L.append("  # Guardar posición actual como HOME")
    L.append("  q_home = get_actual_joint_positions()")
    L.append('  textmsg("UR5e HOME guardado")')
    L.append("")

    L.extend(_bloque_ir_a_origen_tcp(UR5E_TCP_ORIGEN, "UR5e"))

    # Si el UR5e dibuja en espejo, cambia espejo_x o espejo_y aquí.
    L.extend(_bloque_dibujar(trayectorias, "UR5e", espejo_x=True, espejo_y=False))

    L.append("  # === Volver a HOME ===")
    L.append('  textmsg("UR5e - Volviendo a HOME")')
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")
    L.append('  textmsg("UR5e - En HOME. Programa completado")')
    L.append("end")
    L.append("")
    L.append("ur5e_dibujar()")

    return "\n".join(L)


def guardar_script(script: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    log.info(f"URScript guardado en: {path}")
