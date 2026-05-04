# -*- coding: utf-8 -*-
"""
urscript_generator_solucion.py
==============================
Genera URScript para dibujo colaborativo UR3e + UR5e.
CON DETECCIÓN DE FUERZA para evitar paradas de protección.

Funcionamiento de la fuerza:
  1. Al inicio, el robot desciende lentamente desde una altura segura
     comprobando force() en cada paso. Cuando detecta fuerza > F_UMBRAL,
     se detiene y registra z_contacto (la Z real de la superficie).
  2. Durante el dibujo, usa z_contacto como Z FIJA para todos los
     movimientos. No modifica la altura una vez detectada.

Comunicación:
  - El UR3e avisa al PC cuando termina.
  - El PC, al recibir LISTO, envía entonces el script al UR5e.
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

_Z_SUBIDA = float(Z_SUBIDA)
_F_UMBRAL = float(F_UMBRAL)
_V_BAJA = float(V_BAJA)


# =============================================================================
# BLOQUE: DETECTAR SUPERFICIE POR FUERZA
# =============================================================================
def _bloque_detectar_superficie(nombre_robot: str) -> List[str]:
    """
    Genera URScript para detectar la superficie del papel mediante fuerza.
    El robot debe estar posicionado por encima de la superficie antes de llamar.
    Define la variable URScript 'z_contacto' con la Z de contacto detectada.

    Proceso:
      1. zero_ftsensor() para poner a cero el sensor de fuerza.
      2. Descender lentamente con speedl comprobando force() < F_UMBRAL.
      3. Cuando force() >= F_UMBRAL → contacto detectado → stopl().
      4. Registrar z_contacto = posición Z actual del TCP.
      5. Subir a z_contacto + Z_SUBIDA.
    """
    L = []
    L.append(f"  # === Detección de superficie por fuerza: {nombre_robot} ===")
    L.append(f'  textmsg("{nombre_robot} - Detectando superficie por fuerza...")')
    L.append("")
    L.append("  zero_ftsensor()")
    L.append("  sleep(0.5)")
    L.append("")
    L.append("  i_f = 0")
    L.append(f"  while (force() < {_F_UMBRAL} and i_f < 2000):")
    L.append(f"    speedl([0, 0, -{_V_BAJA}, 0, 0, 0], 0.5, 0.02)")
    L.append("    i_f = i_f + 1")
    L.append("  end")
    L.append("  stopl(5.0)")
    L.append("  sleep(0.1)")
    L.append("")
    L.append("  if (i_f >= 2000):")
    L.append(f'    popup("{nombre_robot}: No se detectó superficie. Revisa posición del papel.", error=True)')
    L.append("    halt")
    L.append("  end")
    L.append("")
    L.append("  z_contacto = get_actual_tcp_pose()[2]")
    L.append(f'  textmsg("{nombre_robot} - Contacto detectado en Z = ", z_contacto)')
    L.append("")
    L.append(f"  movel(p[x0, y0, z_contacto+{_Z_SUBIDA:.5f}, rx, ry, rz], a=0.08, v={V_SUBIDA})")
    L.append("  sleep(0.2)")
    L.append("")
    return L


# =============================================================================
# BLOQUE: IR A ORIGEN CALIBRADO (CON DETECCIÓN DE FUERZA)
# =============================================================================
def _bloque_ir_a_origen_tcp(pose_origen, nombre_robot: str) -> List[str]:
    """
    Lleva el robot al origen calibrado del papel y detecta la superficie
    mediante fuerza. Define las variables URScript:
      x0, y0, z_mesa, rx, ry, rz  (del origen calibrado)
      z_contacto                    (Z real de la superficie, detectada por fuerza)
    """
    x, y, z, rx, ry, rz = pose_origen

    L = []
    L.append(f"  # === Ir al origen con detección de fuerza: {nombre_robot} ===")
    L.append(f'  textmsg("{nombre_robot} - yendo al origen calibrado")')
    L.append("")
    L.append(f"  x0 = {x:.5f}")
    L.append(f"  y0 = {y:.5f}")
    L.append(f"  z_mesa = {z:.5f}")
    L.append(f"  rx = {rx:.5f}")
    L.append(f"  ry = {ry:.5f}")
    L.append(f"  rz = {rz:.5f}")
    L.append("")

    # Mover a altura de aproximación (70mm por encima de z_mesa)
    L.append(f"  movel(p[x0, y0, z_mesa+0.07000, rx, ry, rz], a={A_HOME}, v={V_HOME})")
    L.append("  sleep(0.3)")
    L.append("")

    # Detectar superficie por fuerza
    L.extend(_bloque_detectar_superficie(nombre_robot))

    return L


# =============================================================================
# BLOQUE: DIBUJAR TRAYECTORIAS (Z FIJA DESDE DETECCIÓN)
# =============================================================================
def _bloque_dibujar(trayectorias: List[Trayectoria], nombre_robot: str,
                     espejo_x: bool = False, espejo_y: bool = False) -> List[str]:
    """
    Genera las líneas URScript del bloque de dibujo.

    Usa z_contacto (detectado por fuerza al inicio) como Z FIJA para todo
    el dibujo. No modifica la altura durante los trazos.
    Para cada trazo:
      1. Mover al inicio del trazo a z_contacto + Z_SUBIDA (por el aire).
      2. Bajar lento a z_contacto (movel normal, velocidad baja).
      3. Dibujar todos los puntos a z_contacto (movel normal).
      4. Subir a z_contacto + Z_SUBIDA.
    """
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

        # 1. Ir al inicio del trazo por el aire
        L.append(
            f"  movel(p[x0+{x0_t:.5f}, y0+{y0_t:.5f}, z_contacto+{_Z_SUBIDA:.5f}, rx, ry, rz],"
            f" a={A_HOME}, v={V_SUBIDA})"
        )

        # 2. Bajar al papel (z_contacto fija, velocidad lenta)
        L.append(
            f"  movel(p[x0+{x0_t:.5f}, y0+{y0_t:.5f}, z_contacto, rx, ry, rz],"
            f" a=0.01, v=0.0015)"
        )

        # 3. Dibujar el trazo a z_contacto fija
        for x, y in trayectoria[1:]:
            if espejo_x:
                x = -x
            if espejo_y:
                y = -y
            L.append(
                f"  movel(p[x0+{x:.5f}, y0+{y:.5f}, z_contacto, rx, ry, rz],"
                f" a={A_DIBUJO}, v={V_DIBUJO}, r=0.0005)"
            )

        # 4. Subir desde el último punto
        L.append(
            f"  movel(p[x0+{x_fin:.5f}, y0+{y_fin:.5f}, z_contacto+{_Z_SUBIDA:.5f}, rx, ry, rz],"
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
      2. Va al origen calibrado y DETECTA SUPERFICIE POR FUERZA.
      3. Dibuja a z_contacto fija.
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
    L.append(f'  socket_conn = socket_open("{PC_IP}", {PORT_UR3_DONE}, "pc_sync")')
    
    # En URScript, socket_open devuelve False si falla la conexión física
    L.append("  if (not socket_conn):")
    L.append('    textmsg("UR3e - Error: No se pudo conectar con el PC en la IP: ", "' + str(PC_IP) + '")')
    L.append('    popup("UR3e no pudo conectar con el PC. Verifica el Servidor Python.", error=True)')
    L.append("    halt")
    L.append("  else:")
    # Si conectó, enviamos el mensaje
    L.append(f'    socket_send_string("{SYNC_MSG}", "pc_sync")')
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
      2. Va al origen calibrado y DETECTA SUPERFICIE POR FUERZA.
      3. Dibuja a z_contacto fija.
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
