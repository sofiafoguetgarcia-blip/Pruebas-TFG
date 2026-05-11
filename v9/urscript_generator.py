# -*- coding: utf-8 -*-
"""
urscript_generator.py
=====================
Genera los tres scripts URScript:
1) UR5e recoge simuladamente la baldosa y la lleva a DROP_ZONE.
2) UR3e dibuja en DROP_ZONE.
3) UR5e recoge simuladamente la baldosa de DROP_ZONE y la devuelve.
"""

from typing import List, Tuple
import logging

from config import (
    PC_IP, PORT_UR5_LISTO_UR3, PORT_UR3_LISTO_UR5, SYNC_MSG_LISTO,
    V_APROX, V_BAJA_UR5, V_TRASLADO, V_DEPOSITO, A_LENTO, A_RAPIDO,
    Z_APROX_UR5, Z_SUBIDA_UR5, Z_PIEZA_OFFSET, F_UMBRAL_UR5,
    SIMULAR_VENTOSA, VENTOSA_DO_PIN, VENTOSA_DELAY_ON, VENTOSA_DELAY_OFF,
    V_BAJA_UR3, V_DIBUJO, V_SUBIDA, A_DIBUJO, V_HOME, A_HOME,
    Z_PAPEL, Z_SUBIDA, F_UMBRAL_UR3,
    UR5E_DROP_APPROACH_POSE, UR5E_HOME_POSE,
)

from transform import obtener_drop_zones, formatear_pose

log = logging.getLogger(__name__)
Punto = Tuple[float, float]
Trayectoria = List[Punto]


def _socket_aviso_pc(port: int, nombre: str, canal: str) -> List[str]:
    return [
        f"  # === Aviso al PC: {nombre} ===",
        f'  socket_ok = socket_open("{PC_IP}", {port}, "{canal}")',
        "  if (not socket_ok):",
        f'    popup("{nombre}: no pudo avisar al PC", error=True)',
        "    halt",
        "  else:",
        f'    socket_send_string("{SYNC_MSG_LISTO}", "{canal}")',
        "    sleep(0.2)",
        "    sleep(0.2)",
        f'    socket_close("{canal}")',
        f'    textmsg("{nombre}: LISTO enviado al PC")',
        "  end",
    ]


def _bloque_ventosa(on: bool) -> List[str]:
    if SIMULAR_VENTOSA:
        if on:
            return [
                '  textmsg("SIMULACION: ventosa ON / pieza cogida")',
                f"  sleep({VENTOSA_DELAY_ON:.2f})",
            ]
        return [
            '  textmsg("SIMULACION: ventosa OFF / pieza soltada")',
            f"  sleep({VENTOSA_DELAY_OFF:.2f})",
        ]

    estado = "True" if on else "False"
    delay = VENTOSA_DELAY_ON if on else VENTOSA_DELAY_OFF

    return [
        f"  set_digital_out({int(VENTOSA_DO_PIN)}, {estado})",
        f"  sleep({delay:.2f})",
    ]


def _detectar_superficie_ur5(nombre: str) -> List[str]:
    return [
        f'  textmsg("{nombre}: detectando superficie por fuerza")',
        "  zero_ftsensor()",
        "  sleep(0.5)",
        "  i_f = 0",
        f"  while (force() < {F_UMBRAL_UR5:.3f} and i_f < 8000):",
        f"    speedl([0, 0, -{V_BAJA_UR5:.5f}, 0, 0, 0], 0.15, 0.02)",
        "    i_f = i_f + 1",
        "  end",
        "  stopl(2.0)",
        "  sleep(0.2)",
        "  if (i_f >= 8000):",
        f'    popup("{nombre}: no se detecto contacto. Revisa posicion/Z/fuerza.", error=True)',
        "    halt",
        "  end",
        "  z_contacto = get_actual_tcp_pose()[2]",
        f"  z_trabajo = z_contacto + {Z_PIEZA_OFFSET:.5f}",
        f'  textmsg("{nombre}: z_contacto=", z_contacto)',
    ]


def _detectar_superficie_ur3() -> List[str]:
    return [
        '  textmsg("UR3e: detectando superficie una sola vez")',
        "  zero_ftsensor()",
        "  sleep(0.5)",
        "  i_f = 0",
        f"  while (force() < {F_UMBRAL_UR3:.3f} and i_f < 8000):",
        f"    speedl([0, 0, -{V_BAJA_UR3:.5f}, 0, 0, 0], 0.15, 0.02)",
        "    i_f = i_f + 1",
        "  end",
        "  stopl(3.0)",
        "  sleep(0.2)",
        "  if (i_f >= 8000):",
        '    popup("UR3e: no se detecto superficie. Revisa posicion/Z/fuerza.", error=True)',
        "    halt",
        "  end",
        "  z_contacto = get_actual_tcp_pose()[2]",
        f"  z_dibujo = z_contacto + {Z_PAPEL:.5f}",
        '  textmsg("UR3e: z_contacto=", z_contacto)',
        '  textmsg("UR3e: z_dibujo=", z_dibujo)',
        f"  movel(p[x0, y0, z_dibujo+{Z_SUBIDA:.5f}, rx, ry, rz], a=0.03, v=0.010)",
    ]


def generar_script_ur5e_recoger(
    x_pieza: float,
    y_pieza: float,
    angulo_deg: float = 0.0
) -> str:
    _, dz5 = obtener_drop_zones()

    dzx, dzy, dzz, drx, dry, drz = [float(v) for v in dz5]

    xp, yp = float(x_pieza), float(y_pieza)

    L = [
        "def ur5e_recoger_baldosa_simulada():",
        '  textmsg("=== UR5e PARTE 1: recoger baldosa simulada ===")',

        # HOME FIJO: no se vuelve a guardar la posición actual
        f"  q_home = p[{UR5E_HOME_POSE[0]:.5f}, {UR5E_HOME_POSE[1]:.5f}, {UR5E_HOME_POSE[2]:.5f}, {UR5E_HOME_POSE[3]:.5f}, {UR5E_HOME_POSE[4]:.5f}, {UR5E_HOME_POSE[5]:.5f}]",

        f"  rx = {drx:.5f}",
        f"  ry = {dry:.5f}",
        f"  rz = {drz:.5f}",

        f'  textmsg("UR5e: posicion baldosa vision x={xp:.4f}, y={yp:.4f}")',

        "",
        "  # Ir primero a HOME antes de buscar la pieza",
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",
        "  sleep(0.5)",

        "",
        "  # Ir por arriba de la baldosa detectada",
        f"  movej(p[{xp:.5f}, {yp:.5f}, {Z_APROX_UR5:.5f}, rx, ry, rz], a={A_RAPIDO}, v={V_APROX})",
        "  sleep(0.3)",
    ]

    L.extend(_detectar_superficie_ur5("UR5e pieza original"))

    L.extend(_bloque_ventosa(True))

    L += [
        "",
        "  # Subir como si llevara la baldosa",
        f"  movel(p[{xp:.5f}, {yp:.5f}, z_contacto+{Z_SUBIDA_UR5:.5f}, rx, ry, rz], a={A_LENTO}, v={V_APROX})",
        "  sleep(0.2)",

        "",
        "  # Volver a HOME antes de ir a la zona compartida",
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",
        "  sleep(0.5)",

        "",
        "  # Ir al punto approach alto de la zona compartida",
        f"  movej(p[{UR5E_DROP_APPROACH_POSE[0]:.5f}, {UR5E_DROP_APPROACH_POSE[1]:.5f}, {UR5E_DROP_APPROACH_POSE[2]:.5f}, {UR5E_DROP_APPROACH_POSE[3]:.5f}, {UR5E_DROP_APPROACH_POSE[4]:.5f}, {UR5E_DROP_APPROACH_POSE[5]:.5f}], a={A_RAPIDO}, v={V_TRASLADO})",
        "  sleep(0.3)",
    ]

    L.extend(_detectar_superficie_ur5("UR5e deposito DROP_ZONE"))

    L.extend(_bloque_ventosa(False))

    L += [
        "",
        "  # Retirada del UR5e para dejar libre la zona compartida",
        f"  movel(p[{dzx:.5f}, {dzy:.5f}, z_contacto+{Z_SUBIDA_UR5:.5f}, {drx:.5f}, {dry:.5f}, {drz:.5f}], a={A_LENTO}, v={V_APROX})",

        "",
        "  # Volver a HOME despues de dejar la baldosa",
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",
        "  sleep(0.3)",

        '  textmsg("UR5e: baldosa simulada en DROP_ZONE. Avisando al PC")',
    ]

    L.extend(
        _socket_aviso_pc(
            PORT_UR5_LISTO_UR3,
            "UR5e",
            "sync_ur5_ur3"
        )
    )

    L += [
        '  textmsg("UR5e PARTE 1 finalizada")',
        "end",
        "ur5e_recoger_baldosa_simulada()",
    ]

    return "\n".join(L)


def generar_script_ur3e_dibujar(trayectorias: List[Trayectoria]) -> str:
    trayectorias = [t for t in trayectorias if len(t) >= 2]

    if not trayectorias:
        raise ValueError("No hay trayectorias válidas para el UR3e.")

    dz3, _ = obtener_drop_zones()

    x0, y0, z0, rx, ry, rz = [float(v) for v in dz3]

    log.info(f"UR3e usará DROP_ZONE: {formatear_pose(dz3)}")

    L = [
        "def ur3e_dibujar_en_baldosa():",
        '  textmsg("=== UR3e: dibujo en baldosa ===")',

        # Para el UR3e se mantiene HOME actual
        "  q_home = get_actual_joint_positions()",

        f"  x0 = {x0:.5f}",
        f"  y0 = {y0:.5f}",
        f"  z0 = {z0:.5f}",

        f"  rx = {rx:.5f}",
        f"  ry = {ry:.5f}",
        f"  rz = {rz:.5f}",

        "  # Ir al centro de la baldosa por arriba",
        f"  movej(p[x0, y0, z0+0.08000, rx, ry, rz], a={A_HOME}, v={V_HOME})",
        "  sleep(0.3)",
    ]

    L.extend(_detectar_superficie_ur3())

    total = len(trayectorias)

    L.append(f"  # === DIBUJO: {total} trazos ===")

    for idx, tray in enumerate(trayectorias):

        x_ini, y_ini = tray[0]

        x_fin, y_fin = tray[-1]

        L += [
            "",
            f"  # Trazo {idx + 1}/{total}",
            f'  textmsg("UR3e: trazo {idx + 1} de {total}")',

            f"  movej(p[x0+{x_ini:.5f}, y0+{y_ini:.5f}, z_dibujo+{Z_SUBIDA:.5f}, rx, ry, rz], a={A_HOME}, v={V_SUBIDA})",

            f"  movel(p[x0+{x_ini:.5f}, y0+{y_ini:.5f}, z_dibujo, rx, ry, rz], a={A_DIBUJO}, v={V_DIBUJO})",
        ]

        for x, y in tray[1:]:

            L.append(
                f"  movel(p[x0+{x:.5f}, y0+{y:.5f}, z_dibujo, rx, ry, rz], a={A_DIBUJO}, v={V_DIBUJO}, r=0.001)"
            )

        L.append(
            f"  movel(p[x0+{x_fin:.5f}, y0+{y_fin:.5f}, z_dibujo+{Z_SUBIDA:.5f}, rx, ry, rz], a={A_HOME}, v={V_SUBIDA})"
        )

    L += [
        '  textmsg("UR3e: dibujo terminado. Volviendo a HOME")',
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",
    ]

    L.extend(
        _socket_aviso_pc(
            PORT_UR3_LISTO_UR5,
            "UR3e",
            "sync_ur3_ur5"
        )
    )

    L += [
        '  textmsg("UR3e finalizado")',
        "end",
        "ur3e_dibujar_en_baldosa()",
    ]

    return "\n".join(L)


def generar_script_ur5e_devolver(
    x_pieza: float,
    y_pieza: float
) -> str:
    _, dz5 = obtener_drop_zones()

    dzx, dzy, dzz, drx, dry, drz = [float(v) for v in dz5]

    xp, yp = float(x_pieza), float(y_pieza)

    L = [
        "def ur5e_devolver_baldosa_simulada():",
        '  textmsg("=== UR5e PARTE 2: devolver baldosa simulada ===")',

        # HOME FIJO: no se vuelve a guardar la posición actual
        f"  q_home = p[{UR5E_HOME_POSE[0]:.5f}, {UR5E_HOME_POSE[1]:.5f}, {UR5E_HOME_POSE[2]:.5f}, {UR5E_HOME_POSE[3]:.5f}, {UR5E_HOME_POSE[4]:.5f}, {UR5E_HOME_POSE[5]:.5f}]",

        f"  rx = {drx:.5f}",
        f"  ry = {dry:.5f}",
        f"  rz = {drz:.5f}",

        "",
        "  # Ir primero a HOME antes de recoger en DROP_ZONE",
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",
        "  sleep(0.5)",

        "",
        "  # Ir al approach alto de DROP_ZONE",
        f"  movej(p[{UR5E_DROP_APPROACH_POSE[0]:.5f}, {UR5E_DROP_APPROACH_POSE[1]:.5f}, {UR5E_DROP_APPROACH_POSE[2]:.5f}, {UR5E_DROP_APPROACH_POSE[3]:.5f}, {UR5E_DROP_APPROACH_POSE[4]:.5f}, {UR5E_DROP_APPROACH_POSE[5]:.5f}], a={A_RAPIDO}, v={V_APROX})",
        "  sleep(0.3)",
    ]

    L.extend(_detectar_superficie_ur5("UR5e recogida DROP_ZONE"))

    L.extend(_bloque_ventosa(True))

    L += [
        "",
        "  # Subir desde DROP_ZONE con la baldosa",
        f"  movel(p[{dzx:.5f}, {dzy:.5f}, z_contacto+{Z_SUBIDA_UR5:.5f}, {drx:.5f}, {dry:.5f}, {drz:.5f}], a={A_LENTO}, v={V_APROX})",
        "  sleep(0.2)",

        "",
        "  # Volver a HOME antes de devolver la pieza al origen",
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",
        "  sleep(0.5)",

        "",
        "  # Ir por arriba de la posicion original detectada por vision",
        f"  movej(p[{xp:.5f}, {yp:.5f}, {Z_APROX_UR5:.5f}, rx, ry, rz], a={A_RAPIDO}, v={V_TRASLADO})",
        "  sleep(0.3)",
    ]

    L.extend(_detectar_superficie_ur5("UR5e deposito original"))

    L.extend(_bloque_ventosa(False))

    L += [
        "",
        "  # Subir desde la posicion original",
        f"  movel(p[{xp:.5f}, {yp:.5f}, z_contacto+{Z_SUBIDA_UR5:.5f}, rx, ry, rz], a={A_LENTO}, v={V_APROX})",

        "",
        "  # Volver a HOME final",
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",

        '  textmsg("UR5e: baldosa devuelta simuladamente. Avisando al PC")',
    ]

    L.extend(
        _socket_aviso_pc(
            PORT_UR5_LISTO_UR3,
            "UR5e DEVOLVER",
            "sync_ur5_devuelto"
        )
    )

    L += [
        '  textmsg("UR5e PARTE 2 finalizada")',
        "end",
        "ur5e_devolver_baldosa_simulada()",
    ]

    return "\n".join(L)


def guardar_script(script: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)

    log.info(f"URScript guardado: {path}")