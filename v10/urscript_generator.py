# -*- coding: utf-8 -*-
"""
urscript_generator.py
=====================
Genera los tres scripts URScript.

Reglas de esta versión:
- X/Y de la pieza vienen del JSON y se usan tal cual.
- Para coger/devolver piezas se usa SIEMPRE UR5E_PICK_ORIENTATION.
- No se usa el ángulo de visión para orientar la muñeca.
- No se usa la orientación del DROP_ZONE para ir a las piezas.
- El robot entra desde HOME, va al punto alto sobre la pieza, baja por fuerza,
  simula coger/dejar y se retira por el mismo punto alto.
"""

from typing import List, Tuple
import logging

from config import (
    PC_IP,
    PORT_UR5_LISTO_UR3,
    PORT_UR3_LISTO_UR5,
    SYNC_MSG_LISTO,
    V_APROX,
    V_BAJA_UR5,
    V_TRASLADO,
    A_LENTO,
    A_RAPIDO,
    Z_APROX_UR5,
    Z_PIEZA_OFFSET,
    F_UMBRAL_UR5,
    SIMULAR_VENTOSA,
    VENTOSA_DO_PIN,
    VENTOSA_DELAY_ON,
    VENTOSA_DELAY_OFF,
    V_BAJA_UR3,
    V_DIBUJO,
    V_SUBIDA,
    A_DIBUJO,
    V_HOME,
    A_HOME,
    Z_PAPEL,
    Z_SUBIDA,
    F_UMBRAL_UR3,
    UR5E_DROP_APPROACH_POSE,
    UR5E_HOME_POSE,
    UR5E_PICK_ORIENTATION,
    UR3E_HOME_POSE,
)

from transform import obtener_drop_zones, formatear_pose

log = logging.getLogger(__name__)
Punto = Tuple[float, float]
Trayectoria = List[Punto]


def _pose_to_urscript(pose) -> str:
    p = [float(v) for v in pose]
    if len(p) != 6:
        raise ValueError("Una pose debe tener 6 valores [x,y,z,rx,ry,rz]")
    return "p[" + ", ".join(f"{v:.5f}" for v in p) + "]"


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


def _ir_home_ur5() -> List[str]:
    return [
        '  textmsg("UR5e: yendo a HOME")',
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",
        "  sleep(0.3)",
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
    dzx, dzy, dzz, drx_drop, dry_drop, drz_drop = [float(v) for v in dz5]
    xp, yp = float(x_pieza), float(y_pieza)

    rx_pick = float(UR5E_PICK_ORIENTATION[0])
    ry_pick = float(UR5E_PICK_ORIENTATION[1])
    rz_pick = float(UR5E_PICK_ORIENTATION[2])

    L = [
        "def ur5e_recoger_baldosa_simulada():",
        '  textmsg("=== UR5e PARTE 1: recoger baldosa simulada ===")',
        "",
        f"  q_home = {_pose_to_urscript(UR5E_HOME_POSE)}",
        "",
        "  # X/Y llegan DIRECTAMENTE del JSON. NO se corrige nada aquí.",
        f"  x_pick = {xp:.5f}",
        f"  y_pick = {yp:.5f}",
        "",
        "  # Orientacion real medida en tablet para coger piezas.",
        f"  rx_pick = {rx_pick:.5f}",
        f"  ry_pick = {ry_pick:.5f}",
        f"  rz_pick = {rz_pick:.5f}",
        "",
        "  # Orientacion propia de DROP_ZONE.",
        f"  rx_drop = {drx_drop:.5f}",
        f"  ry_drop = {dry_drop:.5f}",
        f"  rz_drop = {drz_drop:.5f}",
        "",
        f'  textmsg("UR5e TARGET JSON x={xp:.5f}, y={yp:.5f}")',
        f'  textmsg("UR5e ORIENT PICK rx={rx_pick:.5f}, ry={ry_pick:.5f}, rz={rz_pick:.5f}")',
        f'  textmsg("Angulo vision ignorado={angulo_deg:.2f}")',
        "",
        "  # 1) HOME -> punto alto justo encima de la pieza",
    ]

    L.extend(_ir_home_ur5())

    L += [
        f"  movej(p[x_pick, y_pick, {Z_APROX_UR5:.5f}, rx_pick, ry_pick, rz_pick], a={A_RAPIDO}, v={V_APROX})",
        "  sleep(0.3)",
    ]

    L.extend(_detectar_superficie_ur5("UR5e pieza original"))
    L.extend(_bloque_ventosa(True))

    L += [
        "",
        "  # 2) Retirada por el mismo punto alto de entrada",
        f"  movel(p[x_pick, y_pick, {Z_APROX_UR5:.5f}, rx_pick, ry_pick, rz_pick], a={A_LENTO}, v={V_APROX})",
        "  sleep(0.2)",
    ]

    L.extend(_ir_home_ur5())

    L += [
        "",
        "  # 3) HOME -> DROP_ZONE",
        f"  movej({_pose_to_urscript(UR5E_DROP_APPROACH_POSE)}, a={A_RAPIDO}, v={V_TRASLADO})",
        "  sleep(0.3)",
    ]

    L.extend(_detectar_superficie_ur5("UR5e deposito DROP_ZONE"))
    L.extend(_bloque_ventosa(False))

    L += [
        "",
        "  # 4) Retirada por el mismo punto alto de DROP_ZONE",
        f"  movel({_pose_to_urscript(UR5E_DROP_APPROACH_POSE)}, a={A_LENTO}, v={V_APROX})",
        "  sleep(0.2)",
    ]

    L.extend(_ir_home_ur5())

    L += [
        "",
        '  textmsg("UR5e: baldosa simulada en DROP_ZONE. Avisando al PC")',
    ]

    L.extend(_socket_aviso_pc(PORT_UR5_LISTO_UR3, "UR5e", "sync_ur5_ur3"))

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
        f"  q_home = {_pose_to_urscript(UR3E_HOME_POSE)}",
        f"  x0 = {x0:.5f}",
        f"  y0 = {y0:.5f}",
        f"  z0 = {z0:.5f}",
        f"  rx = {rx:.5f}",
        f"  ry = {ry:.5f}",
        f"  rz = {rz:.5f}",
        "",
        "  movej(q_home, a={:.5f}, v={:.5f})".format(A_HOME, V_HOME),
        "  sleep(0.3)",
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

    L.extend(_socket_aviso_pc(PORT_UR3_LISTO_UR5, "UR3e", "sync_ur3_ur5"))

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
    dzx, dzy, dzz, drx_drop, dry_drop, drz_drop = [float(v) for v in dz5]
    xp, yp = float(x_pieza), float(y_pieza)

    rx_pick = float(UR5E_PICK_ORIENTATION[0])
    ry_pick = float(UR5E_PICK_ORIENTATION[1])
    rz_pick = float(UR5E_PICK_ORIENTATION[2])

    L = [
        "def ur5e_devolver_baldosa_simulada():",
        '  textmsg("=== UR5e PARTE 2: devolver baldosa simulada ===")',
        f"  q_home = {_pose_to_urscript(UR5E_HOME_POSE)}",
        f"  x_pick = {xp:.5f}",
        f"  y_pick = {yp:.5f}",
        f"  rx_pick = {rx_pick:.5f}",
        f"  ry_pick = {ry_pick:.5f}",
        f"  rz_pick = {rz_pick:.5f}",
        f"  rx_drop = {drx_drop:.5f}",
        f"  ry_drop = {dry_drop:.5f}",
        f"  rz_drop = {drz_drop:.5f}",
        "",
        "  # 1) HOME -> DROP_ZONE",
    ]

    L.extend(_ir_home_ur5())

    L += [
        f"  movej({_pose_to_urscript(UR5E_DROP_APPROACH_POSE)}, a={A_RAPIDO}, v={V_APROX})",
        "  sleep(0.3)",
    ]

    L.extend(_detectar_superficie_ur5("UR5e recogida DROP_ZONE"))
    L.extend(_bloque_ventosa(True))

    L += [
        "",
        "  # 2) Retirada por el mismo punto alto de DROP_ZONE",
        f"  movel({_pose_to_urscript(UR5E_DROP_APPROACH_POSE)}, a={A_LENTO}, v={V_APROX})",
        "  sleep(0.2)",
    ]

    L.extend(_ir_home_ur5())

    L += [
        "",
        "  # 3) HOME -> punto original leído del JSON",
        f'  textmsg("UR5e DEVOLVER TARGET JSON x={xp:.5f}, y={yp:.5f}")',
        f"  movej(p[x_pick, y_pick, {Z_APROX_UR5:.5f}, rx_pick, ry_pick, rz_pick], a={A_RAPIDO}, v={V_TRASLADO})",
        "  sleep(0.3)",
    ]

    L.extend(_detectar_superficie_ur5("UR5e deposito original"))
    L.extend(_bloque_ventosa(False))

    L += [
        "",
        "  # 4) Retirada por el mismo punto alto de la pieza",
        f"  movel(p[x_pick, y_pick, {Z_APROX_UR5:.5f}, rx_pick, ry_pick, rz_pick], a={A_LENTO}, v={V_APROX})",
        "  sleep(0.2)",
    ]

    L.extend(_ir_home_ur5())

    L += [
        "",
        '  textmsg("UR5e: baldosa devuelta simuladamente. Avisando al PC")',
    ]

    L.extend(_socket_aviso_pc(PORT_UR5_LISTO_UR3, "UR5e DEVOLVER", "sync_ur5_devuelto"))

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