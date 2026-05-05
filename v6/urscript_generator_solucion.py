# -*- coding: utf-8 -*-
"""
urscript_generator_solucion.py
==============================
Genera URScript para dibujo colaborativo UR3e + UR5e.

Lo que hace es generar texto URScript.
Ese texto luego se envía al robot desde robot_comm_solucion.py.

URScript es el lenguaje que entiende la tablet/controlador de Universal Robots.
"""

import logging
from typing import List, Tuple

# Importa parámetros globales desde config_solucion.py.
# Estos valores controlan velocidades, aceleraciones, alturas y comunicación.
from config_solucion import (
    V_BAJA, V_DIBUJO, V_SUBIDA, A_DIBUJO,
    Z_SUBIDA, Z_PAPEL, F_UMBRAL,
    V_HOME, A_HOME,
    PC_IP, PORT_UR3_DONE, SYNC_MSG,
)

# Importa funciones de transformación entre UR3e y UR5e.
from transform_ur5_to_ur3 import obtener_origenes, formatear_pose

log = logging.getLogger(__name__)

Punto = Tuple[float, float] # en metros, relativo al origen común calibrado. (x, y)
Trayectoria = List[Punto]   # lista de puntos (x, y) que forma un trazo continuo.
                                    # [(x1, y1), (x2, y2), (x3, y3), ...]


_Z_SUBIDA = float(Z_SUBIDA) # Convierte Z_SUBIDA a float.
                                # Esto evita problemas si el valor viene como entero o de otro tipo numérico.
_Z_PAPEL = float(Z_PAPEL)   # Es el pequeño margen sobre la superficie detectada.
_F_UMBRAL = float(F_UMBRAL) # Es el umbral de fuerza para detectar contacto.
_V_BAJA = float(V_BAJA)     # Velocidad baja para movimientos delicados.


def _bloque_detectar_superficie(nombre_robot: str) -> List[str]:
    """
    Genera el bloque URScript que detecta la superficie.

    Importante:
         NO detecta la superficie en Python.

    Lo que hace es crear líneas de texto URScript.
    Luego esas líneas se ejecutan dentro del robot.

    Define en URScript:
    - z_contacto: altura exacta donde el robot detecta contacto.
    - z_dibujo: altura real usada para dibujar.
    """
    
    # Crea una lista vacía.
    # En esta lista se irán metiendo líneas de URScript como texto.
    L = [] 
    
    
    L.append(f"  # === Detección única de superficie por fuerza: {nombre_robot} ===")
    L.append(f'  textmsg("{nombre_robot} - Detectando superficie una sola vez...")')
    
    
    L.append("  zero_ftsensor()")           # Pone a cero el sensor de fuerza/par.
                                                # Así la lectura de fuerza empieza limpia antes de bajar.
    L.append("  sleep(0.5)")                # Espera medio segundo para que el sensor se estabilice después de resetearlo.    
    L.append("  i_f = 0")                   # contador para evitar q el UR baje continuamente en busca de contacto
    
    # Bucle URScript:
    # mientras la fuerza sea menor que el umbral y no se haya pasado el límite,
    # el robot sigue bajando lentamente.
    L.append(f"  while (force() < {_F_UMBRAL:.3f} and i_f < 2000):")
    L.append(f"    speedl([0, 0, -{_V_BAJA:.5f}, 0, 0, 0], 0.25, 0.02)") # Baja en Z con speedl.
    L.append("    i_f = i_f + 1")
    L.append("  end")
    L.append("  stopl(3.0)")              # Detiene el movimiento con una desaceleración de 3.0 m/s².
    L.append("  sleep(0.2)")
    
    # Comprueba si el contador llegó al límite.
    # Si llegó a 2000, significa que no detectó contacto.
    L.append("  if (i_f >= 2000):")
    L.append(f'    popup("{nombre_robot}: No se detectó superficie. Revisa posición inicial y F_UMBRAL.", error=True)')
    L.append("    halt")
    L.append("  end")
    
    # Guarda la Z real actual del TCP.
    # Esa Z corresponde al punto donde se detectó contacto
    L.append("  z_contacto = get_actual_tcp_pose()[2]")
    
    # Calcula la Z de dibujo.
    # No se dibuja en z_contacto exacta porque eso puede clavar el lápiz.
    # Se dibuja un poco por encima.
    L.append(f"  z_dibujo = z_contacto + {_Z_PAPEL:.5f}")
    

    L.append(f'  textmsg("{nombre_robot} - z_contacto=", z_contacto)')
    L.append(f'  textmsg("{nombre_robot} - z_dibujo=", z_dibujo)')
    
    # Sube el robot a una altura segura sobre la Z de dibujo.
    # Esto prepara el robot para desplazarse al primer trazo sin rozar.
    L.append(f"  movel(p[x0, y0, z_dibujo+{_Z_SUBIDA:.5f}, rx, ry, rz], a=0.03, v=0.001)")
    L.append("  sleep(0.2)")
    return L


def _bloque_ir_a_origen_tcp(pose_origen, nombre_robot: str) -> List[str]:
    """
    Genera el bloque URScript para ir al origen calibrado.

    Primero coloca el robot sobre el origen del papel.
    Después llama al bloque de detección de superficie.
    """
    
    # Convierte los 6 valores de la pose a float.
    # pose_origen tiene formato:
    # [x, y, z, rx, ry, rz]
    x, y, z, rx, ry, rz = [float(v) for v in pose_origen]
    
    L = []
    L.append(f"  # === Ir al origen calibrado: {nombre_robot} ===")
    L.append(f'  textmsg("{nombre_robot} - yendo al origen calibrado")')
    
    # Guarda la X, Y y Z del origen en variables URScript.
    L.append(f"  x0 = {x:.5f}")
    L.append(f"  y0 = {y:.5f}")
    L.append(f"  z_mesa = {z:.5f}")
    
    # Guarda los ángulos de orientación rx, ry, rz en variables URScript.
    L.append(f"  rx = {rx:.5f}")
    L.append(f"  ry = {ry:.5f}")
    L.append(f"  rz = {rz:.5f}")
    
    
    # Esto evita ir directamente a la mesa.
    # Primero se coloca encima y luego baja buscando contacto por fuerza.
    L.append("  # Primero se acerca por arriba; nunca va directamente a la Z baja.")
    L.append(f"  movej(p[x0, y0, z_mesa+0.08000, rx, ry, rz], a={A_HOME}, v={V_HOME})")
    L.append("  sleep(0.3)")
    
    # Añade al script todas las líneas de detección de superficie.
    L.extend(_bloque_detectar_superficie(nombre_robot))
    
    return L


def _bloque_dibujar(
    trayectorias: List[Trayectoria],
    nombre_robot: str,
    espejo_x: bool = False,
    espejo_y: bool = False,
) -> List[str]:
    """
      Genera el bloque URScript de dibujo.

    Usa siempre z_dibujo fija.
    No vuelve a detectar contacto entre trazos.
    """
    L = []
    total = len(trayectorias) # número total de trayectorias a dibujar, para mostrar en mensajes.
    L.append(f"  # === Dibujo - {nombre_robot} - {total} trazos ===") 

    for idx, trayectoria in enumerate(trayectorias): # Recorre todas las trayectorias.
        
        # Si una trayectoria tiene menos de 2 puntos, no se puede dibujar.
        if len(trayectoria) < 2:
            continue

        x0_t, y0_t = trayectoria[0]     # Primer punto del trazo.
                                            # Es donde el robot empezará a dibujar.
        x0_t = 0.0
        y0_t = 0.0
        x_fin, y_fin = trayectoria[-1]  # Último punto del trazo.
                                            # Usado para saber dónde levantar el lápiz al final.

        # Si se activa espejo_x, se invierte la X.
        # Esto sirve cuando un robot está enfrentado al otro
        if espejo_x:
            x0_t, x_fin = -x0_t, -x_fin
            
        # Si se activa espejo_y, se invierte la Y.   
        if espejo_y:
            y0_t, y_fin = -y0_t, -y_fin

        L.append("")
        L.append(f"  # --- Trazo {idx + 1} / {total} ---")
        L.append(f'  textmsg("{nombre_robot} - Trazo {idx + 1} de {total}")')

        # Movimiento 1:
            # va al inicio del trazo por el aire.
            #
            # x0 e y0 son el origen común del papel.
            # x0_t e y0_t son el desplazamiento del trazo respecto a ese origen.
            #
            # z_dibujo + Z_SUBIDA significa lápiz levantado.
        L.append(
            f"  movej(p[x0+{x0_t:.5f}, y0+{y0_t:.5f}, z_dibujo+{_Z_SUBIDA:.5f}, rx, ry, rz],"
            f" a={A_HOME}, v={V_SUBIDA})"
        )

        # Movimiento 2:
            # baja desde el aire hasta la Z de dibujo.
            #
            # IMPORTANTE: baja a z_dibujo, no a z_contacto.
            # Así no clava el lápiz.
        L.append(
            f"  movej(p[x0+{x0_t:.5f}, y0+{y0_t:.5f}, z_dibujo, rx, ry, rz],"
            f" a={A_DIBUJO}, v={V_DIBUJO})"
        )

        # Movimiento 3:
            # recorre todos los puntos restantes del trazo.
        for x, y in trayectoria[1:]:
            
            # Si el robot necesita espejo en X, invierte x.
            if espejo_x:
                x = -x
                
            # Si el robot necesita espejo en Y, invierte y.
            if espejo_y:
                y = -y
                
            # Añade un movimiento lineal hasta el siguiente punto.
            #
            # Usa z_dibujo fija.
            # r=0.0001 es el radio de suavizado entre movimientos. 
                # Si es 0, el robot hace un cambio brusco de dirección al llegar a cada punto.
                # Con un pequeño radio, el robot hace una curva suave entre puntos, lo que mejora la calidad del dibujo y reduce vibraciones.
            L.append(
                f"  movel(p[x0+{x:.5f}, y0+{y:.5f}, z_dibujo, rx, ry, rz],"
                f" a={A_DIBUJO}, v={V_DIBUJO}, r=0.001)" 
            )

        # Movimiento 4:
        # al acabar el trazo, sube el lápiz desde el último punto.
        L.append(
            f"  movel(p[x0+{x_fin:.5f}, y0+{y_fin:.5f}, z_dibujo+{_Z_SUBIDA:.5f}, rx, ry, rz],"
            f" a={A_HOME}, v={V_SUBIDA})"
        )

    L.append("")
    L.append(f'  textmsg("{nombre_robot} - Dibujo completado")')
    return L


def generar_script_ur3e(trayectorias: List[Trayectoria], base_origen: str = "ur3e") -> str:
    """
    Genera el script completo del UR3e.

    Este script:
        1. Guarda la posición actual como HOME.
        2. Va al origen calibrado del UR3e.
        3. Detecta la mesa una sola vez.
        4. Dibuja sus trayectorias.
        5. Vuelve a HOME.
        6. Avisa al PC con el mensaje LISTO.
    """
    trayectorias = [t for t in trayectorias if len(t) >= 2] # Filtra trayectorias inválidas.
                                                                 # Solo deja trayectorias con al menos 2 puntos.
                                                                 
    # Si después de filtrar no queda ninguna trayectoria, lanza error.
    if not trayectorias:
        raise ValueError("UR3e: no hay trayectorias con al menos 2 puntos.")

    # Obtiene los orígenes equivalentes para ambos robots.
    
    # Si base_origen="ur3e", usa el origen calibrado del UR3e
    # y calcula el equivalente para UR5e.
    
    # Aquí solo nos quedamos con origen_ur3e.
    origen_ur3e, _ = obtener_origenes(base_origen)
    log.info(f"UR3e origen usado ({base_origen=}): {formatear_pose(origen_ur3e)}")

    L = []
    
    # Inicio de una función URScript llamada ur3e_dibujar.
    L.append("def ur3e_dibujar():")
    
    L.append('  textmsg("=== UR3e: inicio del programa ===")')
    
    L.append("  q_home = get_actual_joint_positions()")                                        # Guarda las articulaciones actuales como HOME.
    
    L.append('  textmsg("UR3e HOME guardado")')
    
    L.extend(_bloque_ir_a_origen_tcp(origen_ur3e, "UR3e"))                                     # Añade el bloque para ir al origen calibrado y detectar superficie.
    
    
    L.extend(_bloque_dibujar(trayectorias, "UR3e", espejo_x=False, espejo_y=False))            # Añade el bloque de dibujo del UR3e.
                                                                                                 # espejo_x=False y espejo_y=False porque para el UR3e se usa
                                                                                                 # el sistema de coordenadas tal cual.  
    
    L.append('  textmsg("UR3e - Volviendo a HOME")')
    
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")                                       # Vuelve a la posición HOME guardada al inicio.         
    
    L.append('  textmsg("UR3e - En HOME. Avisando al PC")')
    
    # Abre un socket desde el robot hacia el PC.
        # El PC debe estar escuchando en PC_IP:PORT_UR3_DONE.
        # "pc_sync" es el nombre interno de la conexión.
    L.append(f'  socket_conn = socket_open("{PC_IP}", {PORT_UR3_DONE}, "pc_sync")')
    L.append("  if (not socket_conn):") # Si no se pudo conectar, muestra un mensaje de error en el robot.
    L.append(f'    textmsg("UR3e - Error conectando con PC {PC_IP}:{PORT_UR3_DONE}")')
    L.append('    popup("UR3e no pudo conectar con el servidor Python del PC.", error=True)')
    L.append("    halt")
    L.append("  else:") # Si la conexión fue exitosa, envía el mensaje de sincronización al PC.
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
    Genera el script completo del UR5e.

    Este script:
    1. Guarda la posición actual como HOME.
    2. Va al origen calibrado/equivalente del UR5e.
    3. Detecta la mesa una sola vez.
    4. Dibuja sus trayectorias.
    5. Vuelve a HOME.

    El UR5e no avisa al PC porque en tu flujo actual
    es el segundo robot que se ejecuta.
    """
    trayectorias = [t for t in trayectorias if len(t) >= 2]                          # Filtra trayectorias inválidas.
    if not trayectorias:                                                             # Si no queda ninguna trayectoria válida, lanza error.
        raise ValueError("UR5e: no hay trayectorias con al menos 2 puntos.")

    _, origen_ur5e = obtener_origenes(base_origen)
    log.info(f"UR5e origen usado ({base_origen=}): {formatear_pose(origen_ur5e)}")

    L = []
    L.append("def ur5e_dibujar():")
    L.append('  textmsg("=== UR5e: inicio del programa ===")')
    L.append("  q_home = get_actual_joint_positions()")                              # Guarda las articulaciones actuales como HOME.
    L.append('  textmsg("UR5e HOME guardado")')
    L.extend(_bloque_ir_a_origen_tcp(origen_ur5e, "UR5e"))                           # Añade el bloque para ir al origen calibrado/equivalente y detectar superficie.   
    
    # Añade el bloque de dibujo del UR5e.
        # espejo_x=True porque el UR5e está colocado enfrentado al UR3e
        # y su eje X queda invertido respecto al sistema común.
    L.extend(_bloque_dibujar(trayectorias, "UR5e", espejo_x=True, espejo_y=False))
    L.append('  textmsg("UR5e - Volviendo a HOME")')
    L.append(f"  movej(q_home, a={A_HOME}, v={V_HOME})")
    L.append('  textmsg("UR5e - En HOME. Programa completado")')
    L.append("end")
    L.append("ur5e_dibujar()")
    return "\n".join(L)

    
def guardar_script(script: str, path: str) -> None:
    """
    Guarda el URScript generado en un archivo.

    Esto permite revisar el script antes de enviarlo al robot.
    """

    # Abre el archivo en modo escritura.
    # encoding="utf-8" permite guardar caracteres especiales.
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    log.info(f"URScript guardado en: {path}")
    
