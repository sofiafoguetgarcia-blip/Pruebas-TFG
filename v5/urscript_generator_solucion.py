# -*- coding: utf-8 -*-
"""
urscript_generator_solucion.py
==============================
Genera URScript para dibujo colaborativo UR3e + UR5e.

Cambios principales de esta versión:
  1. La mesa/papel se detecta UNA sola vez por fuerza al inicio.
  2. El dibujo NO se hace en z_contacto exacta, sino en:
         z_dibujo = z_contacto + Z_PAPEL
     Esto evita que el lápiz se clave y salte protective stop.
  3. El origen de cálculo ya no está obligado a salir del UR5e. Desde main.py
     puedes elegir --base-origen ur3e o --base-origen ur5e.
"""

import logging
from typing import List, Tuple

from config_solucion import (
    V_BAJA, V_DIBUJO, V_SUBIDA, A_DIBUJO,
    Z_SUBIDA, Z_PAPEL, F_UMBRAL,
    V_HOME, A_HOME,
    PC_IP, PORT_UR3_DONE, SYNC_MSG,
)
from transform_ur5_to_ur3 import obtener_origenes, formatear_pose

log = logging.getLogger(__name__)

Punto = Tuple[float, float]
Trayectoria = List[Punto]

_Z_SUBIDA = float(Z_SUBIDA)
_Z_PAPEL = float(Z_PAPEL)
_F_UMBRAL = float(F_UMBRAL)
_V_BAJA = float(V_BAJA)


def _bloque_detectar_superficie(nombre_robot: str) -> List[str]:
    """
    Detecta la superficie una sola vez y define:
      - z_contacto: Z real donde se ha detectado contacto.
      - z_dibujo: Z segura de dibujo, ligeramente por encima de z_contacto.
    """
    L = []
    L.append(f"  # === Detección única de superficie por fuerza: {nombre_robot} ===")
    L.append(f'  textmsg("{nombre_robot} - Detectando superficie una sola vez...")')
    L.append("  zero_ftsensor()")
    L.append("  sleep(0.5)")
    L.append("  i_f = 0")
    L.append(f"  while (force() < {_F_UMBRAL:.3f} and i_f < 2000):")
    L.append(f"    speedl([0, 0, -{_V_BAJA:.5f}, 0, 0, 0], 0.25, 0.02)")
    L.append("    i_f = i_f + 1")
    L.append("  end")
    L.append("  stopl(3.0)")
    L.append("  sleep(0.2)")
    L.append("  if (i_f >= 2000):")
    L.append(f'    popup("{nombre_robot}: No se detectó superficie. Revisa posición inicial y F_UMBRAL.", error=True)')
    L.append("    halt")
    L.append("  end")
    L.append("  z_contacto = get_actual_tcp_pose()[2]")
    L.append(f"  z_dibujo = z_contacto + {_Z_PAPEL:.5f}")
    L.append(f'  textmsg("{nombre_robot} - z_contacto=", z_contacto)')
    L.append(f'  textmsg("{nombre_robot} - z_dibujo=", z_dibujo)')
    L.append(f"  movel(p[x0, y0, z_dibujo+{_Z_SUBIDA:.5f}, rx, ry, rz], a=0.03, v={V_SUBIDA})")
    L.append("  sleep(0.2)")
    return L


def _bloque_ir_a_origen_tcp(pose_origen, nombre_robot: str) -> List[str]:
    """
    Va al origen calibrado y detecta la superficie una vez.
    """
    x, y, z, rx, ry, rz = [float(v) for v in pose_origen]
    L = []
    L.append(f"  # === Ir al origen calibrado: {nombre_robot} ===")
    L.append(f'  textmsg("{nombre_robot} - yendo al origen calibrado")')
    L.append(f"  x0 = {x:.5f}")
    L.append(f"  y0 = {y:.5f}")
    L.append(f"  z_mesa = {z:.5f}")
    L.append(f"  rx = {rx:.5f}")
    L.append(f"  ry = {ry:.5f}")
    L.append(f"  rz = {rz:.5f}")
    L.append("  # Primero se acerca por arriba; nunca va directamente a la Z baja.")
    L.append(f"  movel(p[x0, y0, z_mesa+0.06000, rx, ry, rz], a={A_HOME}, v={V_HOME})")
    L.append("  sleep(0.3)")
    L.extend(_bloque_detectar_superficie(nombre_robot))
    return L


def _bloque_dibujar(
    trayectorias: List[Trayectoria],
    nombre_robot: str,
    espejo_x: bool = False,
    espejo_y: bool = False,
) -> List[str]:
    """
    Dibuja usando SIEMPRE z_dibujo fija. No vuelve a detectar contacto entre trazos.
    """
    L = []
    total = len(trayectorias)
    L.append(f"  # === Dibujo - {nombre_robot} - {total} trazos ===")

    for idx, trayectoria in enumerate(trayectorias):
        if len(trayectoria) < 2:
            continue

        x0_t, y0_t = trayectoria[0]
        x_fin, y_fin = trayectoria[-1]

        if espejo_x:
            x0_t, x_fin = -x0_t, -x_fin
        if espejo_y:
            y0_t, y_fin = -y0_t, -y_fin

        L.append("")
        L.append(f"  # --- Trazo {idx + 1} / {total} ---")
        L.append(f'  textmsg("{nombre_robot} - Trazo {idx + 1} de {total}")')

        # 1. Ir al inicio por el aire.
        L.append(
            f"  movel(p[x0+{x0_t:.5f}, y0+{y0_t:.5f}, z_dibujo+{_Z_SUBIDA:.5f}, rx, ry, rz],"
            f" a={A_HOME}, v={V_SUBIDA})"
        )

        # 2. Bajar suave hasta la Z de dibujo, NO hasta z_contacto.
        L.append(
            f"  movel(p[x0+{x0_t:.5f}, y0+{y0_t:.5f}, z_dibujo, rx, ry, rz],"
            f" a=0.006, v=0.002)"
        )

        # 3. Trazar a z_dibujo fija.
        for x, y in trayectoria[1:]:
            if espejo_x:
                x = -x
            if espejo_y:
                y = -y
            L.append(
                f"  movel(p[x0+{x:.5f}, y0+{y:.5f}, z_dibujo, rx, ry, rz],"
                f" a={A_DIBUJO}, v={V_DIBUJO}, r=0.0002)"
            )

        # 4. Subir desde el último punto.
        L.append(
            f"  movel(p[x0+{x_fin:.5f}, y0+{y_fin:.5f}, z_dibujo+{_Z_SUBIDA:.5f}, rx, ry, rz],"
            f" a={A_HOME}, v={V_SUBIDA})"
        )

    L.append("")
    L.append(f'  textmsg("{nombre_robot} - Dibujo completado")')
    return L


def generar_script_ur3e(trayectorias: List[Trayectoria], base_origen: str = "ur3e") -> str:
    """
    Genera script del UR3e.
    base_origen decide si el origen común se basa en UR3e o UR5e.
    """
    trayectorias = [t for t in trayectorias if len(t) >= 2]
    if not trayectorias:
        raise ValueError("UR3e: no hay trayectorias con al menos 2 puntos.")

    origen_ur3e, _ = obtener_origenes(base_origen)
    log.info(f"UR3e origen usado ({base_origen=}): {formatear_pose(origen_ur3e)}")

    L = []
    L.append("def ur3e_dibujar():")
    L.append('  textmsg("=== UR3e: inicio del programa ===")')
    L.append("  q_home = get_actual_joint_positions()")
    L.append('  textmsg("UR3e HOME guardado")')
    L.extend(_bloque_ir_a_origen_tcp(origen_ur3e, "UR3e"))
    L.extend(_bloque_dibujar(trayectorias, "UR3e", espejo_x=False, espejo_y=False))
    L.append('  textmsg("UR3e - Volviendo a HOME")')
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")
    L.append('  textmsg("UR3e - En HOME. Avisando al PC")')
    L.append(f'  socket_conn = socket_open("{PC_IP}", {PORT_UR3_DONE}, "pc_sync")')
    L.append("  if (not socket_conn):")
    L.append(f'    textmsg("UR3e - Error conectando con PC {PC_IP}:{PORT_UR3_DONE}")')
    L.append('    popup("UR3e no pudo conectar con el servidor Python del PC.", error=True)')
    L.append("    halt")
    L.append("  else:")
    L.append(f'    socket_send_string("{SYNC_MSG}", "pc_sync")')
    L.append("    sleep(0.2)")
    L.append('    socket_close("pc_sync")')
    L.append('    textmsg("UR3e - LISTO enviado")')
    L.append("  end")
    L.append('  textmsg("UR3e - Programa terminado")')
    L.append("end")
    L.append("ur3e_dibujar()")
    return "\n".join(L)


def generar_script_ur5e(trayectorias: List[Trayectoria], base_origen: str = "ur3e") -> str:
    """
    Genera script del UR5e.
    base_origen decide si el origen común se basa en UR3e o UR5e.
    """
    trayectorias = [t for t in trayectorias if len(t) >= 2]
    if not trayectorias:
        raise ValueError("UR5e: no hay trayectorias con al menos 2 puntos.")

    _, origen_ur5e = obtener_origenes(base_origen)
    log.info(f"UR5e origen usado ({base_origen=}): {formatear_pose(origen_ur5e)}")

    L = []
    L.append("def ur5e_dibujar():")
    L.append('  textmsg("=== UR5e: inicio del programa ===")')
    L.append("  q_home = get_actual_joint_positions()")
    L.append('  textmsg("UR5e HOME guardado")')
    L.extend(_bloque_ir_a_origen_tcp(origen_ur5e, "UR5e"))
    L.extend(_bloque_dibujar(trayectorias, "UR5e", espejo_x=True, espejo_y=False))
    L.append('  textmsg("UR5e - Volviendo a HOME")')
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")
    L.append('  textmsg("UR5e - En HOME. Programa completado")')
    L.append("end")
    L.append("ur5e_dibujar()")
    return "\n".join(L)


def guardar_script(script: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    log.info(f"URScript guardado en: {path}")
