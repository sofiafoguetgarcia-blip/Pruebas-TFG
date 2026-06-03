# -*- coding: utf-8 -*-
"""
urscript_generator.py
=====================
Genera los scripts URScript que se envian a los robots.

En este proyecto el UR5e mantiene la manipulacion de baldosas:
1. Recoge la baldosa usando las coordenadas X/Y del JSON.
2. La deja en la zona compartida.
3. Espera en HOME mientras trabaja el UR3e.
4. Recoge la baldosa de la zona compartida y la devuelve al origen.

El UR3e ya no dibuja trayectorias de una imagen. Ahora lleva un pincel:
1. Sale de HOME cuando el PC le envia el script.
2. Va al cuenco de pintura.
3. Moja el pincel y limpia el exceso en los laterales del cuenco.
4. Va a la zona compartida.
5. Detecta la superficie de la baldosa por fuerza.
6. Pinta la baldosa completa con pasadas suaves.
7. Vuelve a HOME y avisa al PC.
"""

from typing import List, Tuple
import logging
import math

from config import (
    PC_IP,
    PORT_UR5_LISTO_UR3, PORT_UR3_LISTO_UR5,
    SYNC_MSG_LISTO,
    V_APROX, V_BAJA_UR5, V_TRASLADO,
    A_LENTO, A_RAPIDO,
    Z_APROX_UR5,
    F_UMBRAL_UR5,
    SIMULAR_VENTOSA,
    VENTOSA_TIPO_SALIDA, VENTOSA_DO_PIN, VENTOSA_DELAY_ON, VENTOSA_DELAY_OFF,
    V_BAJA_UR3,
    V_HOME,
    A_HOME,
    F_UMBRAL_UR3,
    UR5E_DROP_APPROACH_POSE, UR5E_HOME_POSE, UR5E_PICK_ORIENTATION,
    UR3E_HOME_POSE,
    UR3E_PAINT_BOWL_POSE,
    UR3E_BOWL_APPROACH_Z_OFFSET,
    UR3E_BOWL_FORCE_THRESHOLD,
    UR3E_BOWL_MAX_ITER,
    UR3E_BOWL_CONTACT_OFFSET,
    UR3E_BOWL_LIFT_AFTER_DIP,
    UR3E_DIP_REPETITIONS,
    UR3E_WIPE_OFFSET_Y,
    UR3E_WIPE_Z_OFFSET,
    UR3E_WIPE_REPETITIONS,
    PAINT_MARGIN_M,
    PAINT_PASS_SPACING_M,
    PAINT_SAFE_Z_OFFSET,
    PAINT_CONTACT_OFFSET_M,
    V_PINTURA,
    V_PINCEL_SUBIDA,
    A_PINTURA,
    A_PINCEL,
)

from transform import obtener_drop_zones, formatear_pose

log = logging.getLogger(__name__)

Punto = Tuple[float, float]


def _pose_to_urscript(pose) -> str:
    """Convierte una lista de 6 valores en la sintaxis URScript: p[x,y,z,rx,ry,rz]."""
    p = [float(v) for v in pose]
    if len(p) != 6:
        raise ValueError("Una pose debe tener 6 valores [x,y,z,rx,ry,rz]")
    return "p[" + ", ".join(f"{v:.5f}" for v in p) + "]"


def _modo_ventosa_texto() -> str:
    """Devuelve una descripcion breve del modo de ventosa para los logs URScript."""
    if SIMULAR_VENTOSA:
        return "SIMULACION"
    return f"REAL ({VENTOSA_TIPO_SALIDA}, pin={VENTOSA_DO_PIN})"


def _parametros_pick_ur5(x_pieza: float, y_pieza: float) -> Tuple[float, float, float, float, float]:
    """Normaliza coordenadas de pieza y orientacion fija de recogida del UR5e."""
    xp = float(x_pieza)
    yp = float(y_pieza)
    rx_pick = float(UR5E_PICK_ORIENTATION[0])
    ry_pick = float(UR5E_PICK_ORIENTATION[1])
    rz_pick = float(UR5E_PICK_ORIENTATION[2])
    return xp, yp, rx_pick, ry_pick, rz_pick


def _pose_pick_ur5(z_expr: str = None) -> str:
    """Pose URScript del UR5e sobre la pieza usando x_pick, y_pick y orientacion fija."""
    z = z_expr if z_expr is not None else f"{Z_APROX_UR5:.5f}"
    return f"p[x_pick, y_pick, {z}, rx_pick, ry_pick, rz_pick]"


def _pose_pintura_ur3(x_expr: str, y_expr: str, z_expr: str) -> str:
    """Pose del UR3e para pintar respecto al centro de la zona compartida."""
    return f"p[{x_expr}, {y_expr}, {z_expr}, rx, ry, rz]"


def _socket_aviso_pc(port: int, nombre: str, canal: str) -> List[str]:
    """Genera el bloque URScript para avisar al PC de que una fase ha terminado."""
    return [
        f"  # Avisamos al PC de que esta fase ha terminado: {nombre}",
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
    """Genera el bloque URScript para activar o desactivar la ventosa del UR5e."""
    accion = "ON" if on else "OFF"
    estado_ur = "True" if on else "False"
    delay = VENTOSA_DELAY_ON if on else VENTOSA_DELAY_OFF
    pin = int(VENTOSA_DO_PIN)

    if SIMULAR_VENTOSA:
        if on:
            return [
                '  textmsg("SIMULACION ventosa: activando vacio (ON) - pieza cogida")',
                f"  sleep({VENTOSA_DELAY_ON:.2f})",
            ]
        return [
            '  textmsg("SIMULACION ventosa: liberando vacio (OFF) - pieza soltada")',
            f"  sleep({VENTOSA_DELAY_OFF:.2f})",
        ]

    tipo = VENTOSA_TIPO_SALIDA.strip().upper()
    if tipo == "DO_CONTROLADOR":
        instruccion = f"set_digital_out({pin}, {estado_ur})"
    elif tipo == "TOOL_DO":
        instruccion = f"set_tool_digital_out({pin}, {estado_ur})"
    else:
        raise ValueError(
            f"VENTOSA_TIPO_SALIDA desconocido: '{VENTOSA_TIPO_SALIDA}'. "
            "Usa 'DO_CONTROLADOR' o 'TOOL_DO'."
        )

    return [
        f'  textmsg("Ventosa {accion}: {instruccion}")',
        f"  {instruccion}",
        f"  sleep({delay:.2f})",
    ]


def _ir_home_ur5() -> List[str]:
    """Genera las lineas URScript para que el UR5e vaya a HOME."""
    return [
        '  textmsg("UR5e: yendo a HOME")',
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",
        "  sleep(0.3)",
    ]


def _detectar_superficie_ur5(nombre: str) -> List[str]:
    """Bloque de bajada por fuerza del UR5e para coger o dejar una baldosa."""
    return [
        f'  textmsg("{nombre}: detectando superficie por fuerza")',
        "  zero_ftsensor()",
        "  sleep(0.5)",
        "  i_f = 0",
        f"  while (force() < {F_UMBRAL_UR5:.3f} and i_f < 30000):",
        f"    speedl([0, 0, -{V_BAJA_UR5:.5f}, 0, 0, 0], 0.05, 0.008)",
        "    i_f = i_f + 1",
        "  end",
        "  stopl(0.2)",
        "  sleep(0.1)",
        "  if (i_f >= 30000):",
        f'    popup("{nombre}: no se detecto contacto. Revisa posicion/Z/fuerza.", error=True)',
        "    halt",
        "  end",
        "  z_contacto = get_actual_tcp_pose()[2]",
        "  z_trabajo = z_contacto",
        f'  textmsg("{nombre}: z_contacto=", z_contacto)',
    ]


def _ir_home_ur3() -> List[str]:
    """Genera las lineas URScript para que el UR3e vaya a HOME."""
    return [
        '  textmsg("UR3e: yendo a HOME")',
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",
        "  sleep(0.3)",
    ]


def _detectar_superficie_ur3_pintura() -> List[str]:
    """Detecta por fuerza la superficie de la baldosa y calcula z_pintura."""
    return [
        '  textmsg("UR3e: detectando superficie de la baldosa para pintar")',
        "  zero_ftsensor()",
        "  sleep(0.5)",
        "  i_f = 0",
        f"  while (force() < {F_UMBRAL_UR3:.3f} and i_f < 10000):",
        f"    speedl([0, 0, -{V_BAJA_UR3:.5f}, 0, 0, 0], 0.15, 0.02)",
        "    i_f = i_f + 1",
        "  end",
        "  stopl(1.0)",
        "  sleep(0.2)",
        "  if (i_f >= 10000):",
        '    popup("UR3e: no se detecto la superficie de la baldosa.", error=True)',
        "    halt",
        "  end",
        "  z_contacto = get_actual_tcp_pose()[2]",
        f"  z_pintura = z_contacto + {PAINT_CONTACT_OFFSET_M:.5f}",
        '  textmsg("UR3e: z_contacto=", z_contacto)',
        '  textmsg("UR3e: z_pintura=", z_pintura)',
    ]


def _bloque_mojar_y_limpiar_pincel() -> List[str]:
    """
    Rutina de mojado y limpieza del pincel.
    """

    bx, by, bz, brx, bry, brz = [float(v) for v in UR3E_PAINT_BOWL_POSE]

    z_aprox = bz + float(UR3E_BOWL_APPROACH_Z_OFFSET)

    y_left = by - float(UR3E_WIPE_OFFSET_Y)
    y_right = by + float(UR3E_WIPE_OFFSET_Y)

    L = [
        '  textmsg("UR3e: yendo al cuenco de pintura")',

        f"  movej(p[{bx:.5f}, {by:.5f}, {z_aprox:.5f}, {brx:.5f}, {bry:.5f}, {brz:.5f}], a={A_PINCEL}, v={V_PINCEL_SUBIDA})",

        "  sleep(0.2)",

        "",
        '  textmsg("UR3e: buscando fondo del cuenco por fuerza")',

        "  zero_ftsensor()",
        "  sleep(0.5)",

        "  i_bowl = 0",

        # umbral aumentado para evitar falsas detecciones
        "  while (force() < 2.0 and i_bowl < 20000):",

        f"    speedl([0, 0, -{V_BAJA_UR3:.5f}, 0, 0, 0], 0.10, 0.015)",

        "    i_bowl = i_bowl + 1",

        "  end",

        "  stopl(1.0)",
        "  sleep(0.15)",

        "  if (i_bowl >= 20000):",
        '    popup("UR3e: no se detecto el fondo del cuenco.", error=True)',
        "    halt",
        "  end",

        "",
        "  z_cuenco_contacto = get_actual_tcp_pose()[2]",

        # baja 10 mm mas despues de detectar contacto
        "  z_mojado = z_cuenco_contacto - 0.010",

        # limpieza mas alta
        "  z_limpieza = z_cuenco_contacto + 0.020",

        # subida mas alta
        "  z_salida_cuenco = z_cuenco_contacto + 0.050",
        '  textmsg("UR3e: contacto cuenco=", z_cuenco_contacto)',
        "",
    ]

    for i in range(int(UR3E_DIP_REPETITIONS)):

        L += [
            f'  textmsg("UR3e: mojando pincel {i+1}/{int(UR3E_DIP_REPETITIONS)}")',
            f"  movel(p[{bx:.5f}, {by:.5f}, z_mojado, {brx:.5f}, {bry:.5f}, {brz:.5f}], a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
            "  sleep(0.4)",
            f"  movel(p[{bx:.5f}, {by:.5f}, z_salida_cuenco, {brx:.5f}, {bry:.5f}, {brz:.5f}], a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
            "  sleep(0.15)",
        ]

    L += [
        "",
        '  textmsg("UR3e: limpiando exceso de pintura")',
        f"  movel(p[{bx:.5f}, {by:.5f}, z_limpieza, {brx:.5f}, {bry:.5f}, {brz:.5f}], a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
        f"  movel(p[{bx:.5f}, {y_left:.5f}, z_limpieza, {brx:.5f}, {bry:.5f}, {brz:.5f}], a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
    ]

    for _ in range(int(UR3E_WIPE_REPETITIONS)):

        L += [
            f"  movel(p[{bx:.5f}, {y_right:.5f}, z_limpieza, {brx:.5f}, {bry:.5f}, {brz:.5f}], a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
            f"  movel(p[{bx:.5f}, {y_left:.5f}, z_limpieza, {brx:.5f}, {bry:.5f}, {brz:.5f}], a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
        ]

    L += [
        "",
        f"  movel(p[{bx:.5f}, {by:.5f}, z_salida_cuenco, {brx:.5f}, {bry:.5f}, {brz:.5f}], a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
        f"  movej(p[{bx:.5f}, {by:.5f}, {z_aprox:.5f}, {brx:.5f}, {bry:.5f}, {brz:.5f}], a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
        "  sleep(0.2)",
    ]

    return L


def _generar_pasadas_pintura(ancho_m: float, alto_m: float) -> List[Punto]:
    """Calcula las pasadas paralelas para cubrir la baldosa completa."""
    ancho_util = max(float(ancho_m) - 2.0 * PAINT_MARGIN_M, PAINT_PASS_SPACING_M)
    alto_util = max(float(alto_m) - 2.0 * PAINT_MARGIN_M, PAINT_PASS_SPACING_M)

    x_min = -ancho_util / 2.0
    x_max = ancho_util / 2.0
    y_min = -alto_util / 2.0
    y_max = alto_util / 2.0

    n_pasadas = max(2, int(math.ceil(alto_util / PAINT_PASS_SPACING_M)) + 1)
    if n_pasadas == 1:
        ys = [0.0]
    else:
        ys = [y_min + i * (alto_util / (n_pasadas - 1)) for i in range(n_pasadas)]

    pasadas: List[Punto] = []
    for i, y in enumerate(ys):
        if i % 2 == 0:
            pasadas.append((x_min, y))
            pasadas.append((x_max, y))
        else:
            pasadas.append((x_max, y))
            pasadas.append((x_min, y))
    return pasadas


def generar_script_ur5e_recoger(
    x_pieza: float,
    y_pieza: float,
    angulo_deg: float = 0.0
) -> str:
    """Genera el script para que el UR5e recoja la baldosa y la lleve a la zona compartida."""
    _, dz5 = obtener_drop_zones()
    _, _, _, drx_drop, dry_drop, drz_drop = [float(v) for v in dz5]
    xp, yp, rx_pick, ry_pick, rz_pick = _parametros_pick_ur5(x_pieza, y_pieza)

    L = [
        "def ur5e_recoger_baldosa():",
        '  textmsg("=== UR5e PARTE 1: recoger baldosa ===")',
        f'  textmsg("Ventosa: {_modo_ventosa_texto()}")',
        "",
        f"  q_home = {_pose_to_urscript(UR5E_HOME_POSE)}",
        f"  x_pick = {xp:.5f}",
        f"  y_pick = {yp:.5f}",
        f"  rx_pick = {rx_pick:.5f}",
        f"  ry_pick = {ry_pick:.5f}",
        f"  rz_pick = {rz_pick:.5f}",
        f"  rx_drop = {drx_drop:.5f}",
        f"  ry_drop = {dry_drop:.5f}",
        f"  rz_drop = {drz_drop:.5f}",
        f'  textmsg("UR5e TARGET JSON x={xp:.5f}, y={yp:.5f}")',
        f'  textmsg("Angulo vision ignorado={angulo_deg:.2f}")',
        "",
    ]

    L.extend(_ir_home_ur5())
    L += [
        "  # Ir al punto alto encima de la pieza",
        f"  movej({_pose_pick_ur5()}, a={A_RAPIDO}, v={V_APROX})",
        "  sleep(0.3)",
    ]

    L.extend(_detectar_superficie_ur5("UR5e pieza original"))
    L.extend(_bloque_ventosa(True))

    L += [
        "  # Subir y volver a HOME con la pieza",
        f"  movel({_pose_pick_ur5()}, a={A_LENTO}, v={V_APROX})",
        "  sleep(0.2)",
    ]
    L.extend(_ir_home_ur5())

    L += [
        "  # Ir a la zona compartida y dejar la pieza",
        f"  movej({_pose_to_urscript(UR5E_DROP_APPROACH_POSE)}, a={A_RAPIDO}, v={V_TRASLADO})",
        "  sleep(0.3)",
    ]
    L.extend(_detectar_superficie_ur5("UR5e deposito DROP_ZONE"))
    L.extend(_bloque_ventosa(False))

    L += [
        "  # Retirarse y volver a HOME. El UR5e queda reposando hasta que termine el UR3e.",
        f"  movel({_pose_to_urscript(UR5E_DROP_APPROACH_POSE)}, a={A_LENTO}, v={V_APROX})",
        "  sleep(0.2)",
    ]
    L.extend(_ir_home_ur5())

    L += ['  textmsg("UR5e: baldosa en DROP_ZONE. Avisando al PC")']
    L.extend(_socket_aviso_pc(PORT_UR5_LISTO_UR3, "UR5e", "sync_ur5_ur3"))
    L += [
        '  textmsg("UR5e PARTE 1 finalizada")',
        "end",
        "ur5e_recoger_baldosa()",
    ]
    return "\n".join(L)


def generar_script_ur3e_pintar(ancho_baldosa_m: float, alto_baldosa_m: float) -> str:
    """Genera el script para que el UR3e moje el pincel y pinte la baldosa completa."""
    dz3, _ = obtener_drop_zones()
    x0, y0, z0, rx, ry, rz = [float(v) for v in dz3]

    pasadas = _generar_pasadas_pintura(ancho_baldosa_m, alto_baldosa_m)
    log.info(f"UR3e usara DROP_ZONE: {formatear_pose(dz3)}")
    log.info(f"Pasadas de pintura generadas: {len(pasadas) // 2}")

    bx, by, bz, brx, bry, brz = [float(v) for v in UR3E_PAINT_BOWL_POSE]
    p_cuenco_aprox = [
        bx,
        by,
        bz + UR3E_BOWL_APPROACH_Z_OFFSET,
        brx,
        bry,
        brz,
    ]

    x_ini, y_ini = pasadas[0]

    L = [
        "def ur3e_pintar_baldosa():",
        '  textmsg("=== UR3e: pintar baldosa con pincel ===")',
        f"  q_home = {_pose_to_urscript(UR3E_HOME_POSE)}",
        "",
        "  # Centro de la zona compartida tal como la ve el UR3e",
        f"  x0 = {x0:.5f}",
        f"  y0 = {y0:.5f}",
        f"  z0 = {z0:.5f}",
        f"  rx = {rx:.5f}",
        f"  ry = {ry:.5f}",
        f"  rz = {rz:.5f}",
        "",
        "  # Posicion aproximada sobre el cuenco de pintura",
        f"  p_cuenco_aprox = {_pose_to_urscript(p_cuenco_aprox)}",
        "",
        "  # Primero HOME",
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",
        "  sleep(0.3)",
        "",
        "  # Pasamos por la zona compartida alta antes de ir al cuenco",
        f"  movej(p[x0, y0, z0+{PAINT_SAFE_Z_OFFSET:.5f}, rx, ry, rz], a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
        "  sleep(0.2)",
        "",
        "  # Desde una posicion segura vamos al cuenco",
        f"  movej(p_cuenco_aprox, a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
        "  sleep(0.2)",
    ]

    L.extend(_bloque_mojar_y_limpiar_pincel())

    L += [
        "",
        '  textmsg("UR3e: volviendo a la zona compartida en alto")',
        f"  movej(p[x0, y0, z0+{PAINT_SAFE_Z_OFFSET:.5f}, rx, ry, rz], a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
        "  sleep(0.2)",
        "",
        "  # Ir al primer punto real de pintura en alto",
        f"  movej({_pose_pintura_ur3(f'x0+{x_ini:.5f}', f'y0+{y_ini:.5f}', f'z0+{PAINT_SAFE_Z_OFFSET:.5f}')}, a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
        "  sleep(0.2)",
    ]

    # Ahora detecta la superficie justo en el primer punto de pintura
    L.extend(_detectar_superficie_ur3_pintura())

    total_pasadas = len(pasadas) // 2
    L += [
        "",
        f"  # Pintura completa de la baldosa: {total_pasadas} pasadas suaves",
    ]

    for i in range(0, len(pasadas), 2):
        n = i // 2 + 1
        x_ini, y_ini = pasadas[i]
        x_fin, y_fin = pasadas[i + 1]

        L += [
            "",
            f"  # Pasada {n} de {total_pasadas}",
            f'  textmsg("UR3e: pasada de pintura {n}/{total_pasadas}")',
            f"  movej({_pose_pintura_ur3(f'x0+{x_ini:.5f}', f'y0+{y_ini:.5f}', f'z_pintura+{PAINT_SAFE_Z_OFFSET:.5f}')}, a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
            f"  movel({_pose_pintura_ur3(f'x0+{x_ini:.5f}', f'y0+{y_ini:.5f}', 'z_pintura')}, a={A_PINTURA}, v={V_PINTURA})",
            f"  movel({_pose_pintura_ur3(f'x0+{x_fin:.5f}', f'y0+{y_fin:.5f}', 'z_pintura')}, a={A_PINTURA}, v={V_PINTURA}, r=0.001)",
            f"  movel({_pose_pintura_ur3(f'x0+{x_fin:.5f}', f'y0+{y_fin:.5f}', f'z_pintura+{PAINT_SAFE_Z_OFFSET:.5f}')}, a={A_PINCEL}, v={V_PINCEL_SUBIDA})",
        ]

    L += [
        "",
        '  textmsg("UR3e: pintura terminada. Volviendo a HOME")',
        f"  movej(q_home, a={A_HOME}, v={V_HOME})",
    ]

    L.extend(_socket_aviso_pc(PORT_UR3_LISTO_UR5, "UR3e", "sync_ur3_ur5"))

    L += [
        '  textmsg("UR3e finalizado")',
        "end",
        "ur3e_pintar_baldosa()",
    ]

    return "\n".join(L)


def generar_script_ur5e_devolver(x_pieza: float, y_pieza: float) -> str:
    """Genera el script para que el UR5e devuelva la baldosa a su posicion original."""
    _, dz5 = obtener_drop_zones()
    _, _, _, drx_drop, dry_drop, drz_drop = [float(v) for v in dz5]
    xp, yp, rx_pick, ry_pick, rz_pick = _parametros_pick_ur5(x_pieza, y_pieza)

    L = [
        "def ur5e_devolver_baldosa():",
        '  textmsg("=== UR5e PARTE 2: devolver baldosa ===")',
        f'  textmsg("Ventosa: {_modo_ventosa_texto()}")',
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
    ]

    L.extend(_ir_home_ur5())
    L += [
        "  # Recoger la baldosa de la zona compartida",
        f"  movej({_pose_to_urscript(UR5E_DROP_APPROACH_POSE)}, a={A_RAPIDO}, v={V_APROX})",
        "  sleep(0.3)",
    ]
    L.extend(_detectar_superficie_ur5("UR5e recogida DROP_ZONE"))
    L.extend(_bloque_ventosa(True))

    L += [
        "  # Subir y volver a HOME",
        f"  movel({_pose_to_urscript(UR5E_DROP_APPROACH_POSE)}, a={A_LENTO}, v={V_APROX})",
        "  sleep(0.2)",
    ]
    L.extend(_ir_home_ur5())

    L += [
        "  # Ir a la posicion original de la pieza y depositarla",
        f'  textmsg("UR5e DEVOLVER TARGET JSON x={xp:.5f}, y={yp:.5f}")',
        f"  movej({_pose_pick_ur5()}, a={A_RAPIDO}, v={V_TRASLADO})",
        "  sleep(0.3)",
    ]
    L.extend(_detectar_superficie_ur5("UR5e deposito original"))
    L.extend(_bloque_ventosa(False))

    L += [
        "  # Retirarse y volver a HOME",
        f"  movel({_pose_pick_ur5()}, a={A_LENTO}, v={V_APROX})",
        "  sleep(0.2)",
    ]
    L.extend(_ir_home_ur5())

    L += ['  textmsg("UR5e: baldosa devuelta. Avisando al PC")']
    L.extend(_socket_aviso_pc(PORT_UR5_LISTO_UR3, "UR5e DEVOLVER", "sync_ur5_devuelto"))
    L += [
        '  textmsg("UR5e PARTE 2 finalizada")',
        "end",
        "ur5e_devolver_baldosa()",
    ]
    return "\n".join(L)


def guardar_script(script: str, path: str) -> None:
    """Guarda el script en un archivo de texto para poder revisarlo antes de enviarlo."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    log.info(f"URScript guardado: {path}")
