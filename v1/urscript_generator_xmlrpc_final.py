# -*- coding: utf-8 -*-
"""
urscript_generator.py
=====================
Genera scripts URScript para dibujo colaborativo UR3e + UR5e con XML-RPC.
"""

import logging
from typing import List, Tuple

from config_xmlrpc_final import (
    V_DIBUJO, V_SUBIDA, A_DIBUJO,
    Z_SUBIDA, Z_PAPEL,
    V_HOME, A_HOME,
    XMLRPC_URL,
    UR3E_TCP_ORIGEN, UR5E_TCP_ORIGEN,
    UR3E_ESPEJO_X, UR3E_ESPEJO_Y,
    UR5E_ESPEJO_X, UR5E_ESPEJO_Y,
)

log = logging.getLogger(__name__)

Punto = Tuple[float, float]
Trayectoria = List[Punto]

_Z_PAPEL = float(Z_PAPEL)
_Z_AIRE = float(Z_PAPEL + Z_SUBIDA)
_Z_REPOSO = float(Z_PAPEL + 0.05)


def _p(pose):
    return f"p[{pose[0]:.5f}, {pose[1]:.5f}, {pose[2]:.5f}, {pose[3]:.5f}, {pose[4]:.5f}, {pose[5]:.5f}]"


def _bloque_xmlrpc() -> List[str]:
    L = []
    L.append(f'  rpc = rpc_factory("xmlrpc", "{XMLRPC_URL}")')
    L.append('  textmsg("XML-RPC creado hacia PC")')
    L.append("")
    return L


def _bloque_ir_a_origen(pose_origen, nombre_robot: str) -> List[str]:
    """Va al origen calibrado del robot de forma segura."""
    x, y, z, rx, ry, rz = pose_origen

    z_alta = z + 0.120
    z_aire = z + _Z_AIRE

    L = []
    L.append(f"  # === Ir a origen calibrado {nombre_robot} ===")
    L.append(f'  textmsg("{nombre_robot}: yendo a origen calibrado")')
    L.append(f"  x0 = {x:.5f}")
    L.append(f"  y0 = {y:.5f}")
    L.append(f"  z0 = {z:.5f}")
    L.append(f"  rx = {rx:.5f}")
    L.append(f"  ry = {ry:.5f}")
    L.append(f"  rz = {rz:.5f}")
    L.append("")
    L.append(f"  movel(p[x0, y0, {z_alta:.5f}, rx, ry, rz], a={A_HOME}, v={V_HOME})")
    L.append("  sleep(0.2)")
    L.append(f"  movel(p[x0, y0, {z_aire:.5f}, rx, ry, rz], a={A_HOME}, v={V_SUBIDA})")
    L.append("  sleep(0.2)")
    L.append("")
    return L


def _bloque_dibujar(
    trayectorias: List[Trayectoria],
    nombre_robot: str,
    espejo_x: bool = False,
    espejo_y: bool = False,
) -> List[str]:
    L = []
    total = len(trayectorias)
    L.append(f"  # === Dibujo {nombre_robot}: {total} trazos ===")

    for idx, trayectoria in enumerate(trayectorias):
        if len(trayectoria) < 2:
            continue

        def conv(pt):
            x, y = pt
            if espejo_x:
                x = -x
            if espejo_y:
                y = -y
            return x, y

        x_ini, y_ini = conv(trayectoria[0])
        x_fin, y_fin = conv(trayectoria[-1])

        L.append("")
        L.append(f"  # --- Trazo {idx + 1} / {total} ---")
        L.append(f'  textmsg("{nombre_robot}: trazo {idx + 1} de {total}")')

        # Ir por el aire al inicio del trazo.
        L.append(
            f"  movel(p[x0+{x_ini:.5f}, y0+{y_ini:.5f}, z0+{_Z_AIRE:.5f}, rx, ry, rz], "
            f"a={A_HOME}, v={V_SUBIDA})"
        )

        # Bajar al papel.
        L.append(
            f"  movel(p[x0+{x_ini:.5f}, y0+{y_ini:.5f}, z0+{_Z_PAPEL:.5f}, rx, ry, rz], "
            f"a=0.01, v=0.0015)"
        )

        # Dibujar manteniendo Z constante.
        for pt in trayectoria[1:]:
            x, y = conv(pt)
            L.append(
                f"  movel(p[x0+{x:.5f}, y0+{y:.5f}, z0+{_Z_PAPEL:.5f}, rx, ry, rz], "
                f"a={A_DIBUJO}, v={V_DIBUJO}, r=0.0005)"
            )

        # Subir al terminar el trazo.
        L.append(
            f"  movel(p[x0+{x_fin:.5f}, y0+{y_fin:.5f}, z0+{_Z_AIRE:.5f}, rx, ry, rz], "
            f"a={A_HOME}, v={V_SUBIDA})"
        )

    L.append("")
    L.append(f'  textmsg("{nombre_robot}: dibujo completado")')
    return L


def generar_script_ur3e(trayectorias: List[Trayectoria]) -> str:
    trayectorias = [t for t in trayectorias if len(t) >= 2]
    if not trayectorias:
        raise ValueError("UR3e: no hay trayectorias con al menos 2 puntos.")

    log.info(f"Generando script UR3e — {len(trayectorias)} trayectorias")

    L = []
    L.append("def ur3e_dibujar():")
    L.append('  textmsg("=== UR3e: inicio ===")')
    L.append("  q_home = get_actual_joint_positions()")
    L.append('  textmsg("UR3e HOME guardado")')
    L.append("")
    L.extend(_bloque_xmlrpc())
    L.extend(_bloque_ir_a_origen(UR3E_TCP_ORIGEN, "UR3e"))
    L.extend(_bloque_dibujar(trayectorias, "UR3e", UR3E_ESPEJO_X, UR3E_ESPEJO_Y))
    L.append("")
    L.append('  textmsg("UR3e: volviendo a HOME")')
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")
    L.append('  textmsg("UR3e: avisando al PC con ur3_done")')
    L.append("  ok = rpc.ur3_done()")
    L.append('  textmsg("UR3e: ur3_done enviado")')
    L.append('  textmsg("UR3e: programa terminado")')
    L.append("end")
    L.append("")
    L.append("ur3e_dibujar()")

    return "\n".join(L)


def generar_script_ur5e(trayectorias: List[Trayectoria]) -> str:
    trayectorias = [t for t in trayectorias if len(t) >= 2]
    if not trayectorias:
        raise ValueError("UR5e: no hay trayectorias con al menos 2 puntos.")

    log.info(f"Generando script UR5e — {len(trayectorias)} trayectorias")

    L = []
    L.append("def ur5e_dibujar():")
    L.append('  textmsg("=== UR5e: inicio, esperando UR3e ===")')
    L.append("  q_home = get_actual_joint_positions()")
    L.append('  textmsg("UR5e HOME guardado")')
    L.append("")
    L.extend(_bloque_xmlrpc())
    L.append('  textmsg("UR5e: esperando permiso del PC")')
    L.append("  while rpc.can_ur5_start() == False:")
    L.append("    sleep(1.0)")
    L.append("  end")
    L.append('  textmsg("UR5e: permiso recibido, empieza")')
    L.append("")
    L.extend(_bloque_ir_a_origen(UR5E_TCP_ORIGEN, "UR5e"))
    L.extend(_bloque_dibujar(trayectorias, "UR5e", UR5E_ESPEJO_X, UR5E_ESPEJO_Y))
    L.append("")
    L.append('  textmsg("UR5e: volviendo a HOME")')
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")
    L.append('  textmsg("UR5e: avisando al PC con ur5_done")')
    L.append("  ok = rpc.ur5_done()")
    L.append('  textmsg("UR5e: programa terminado")')
    L.append("end")
    L.append("")
    L.append("ur5e_dibujar()")

    return "\n".join(L)


def guardar_script(script: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    log.info(f"URScript guardado en: {path}")
