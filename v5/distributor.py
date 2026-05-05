# -*- coding: utf-8 -*-
"""
distributor.py
==============
Reparto de trayectorias entre el UR3e y el UR5e.

Su función principal es repartir esos trazos teniendo en cuenta:
    1. El alcance del UR3e.
    2. El alcance del UR5e.
    3. Un reparto aleatorio para que no siempre dibuje todo el mismo robot.

Criterios (en orden):
  1. ALCANCE: si todos los puntos de una trayectoria están fuera del alcance
     seguro del UR3e, se asigna obligatoriamente al UR5e.
  2. ALEATORIO: el resto se reparte aleatoriamente entre los dos robots,
     intentando equilibrar el número de trayectorias.

Uso independiente:
    from distributor import repartir_trayectorias
    t3, t5 = repartir_trayectorias(trayectorias)
"""

import math
import random
import logging
from typing import List, Tuple

# Importa desde config_solucion.py los alcances máximos útiles de cada robot.
    # UR3E_MAX_REACH:
    #     distancia máxima segura que se permite al UR3e desde el origen común.
    #
    # UR5E_MAX_REACH:
    #     distancia máxima segura que se permite al UR5e desde el origen común.
from config_solucion import UR3E_MAX_REACH, UR5E_MAX_REACH

log = logging.getLogger(__name__)

Punto       = Tuple[float, float] # en metros, relativo al origen común calibrado. (x, y)
Trayectoria = List[Punto]         # lista de puntos (x, y) que forma un trazo continuo.
                                    # [(x1, y1), (x2, y2), (x3, y3), ...]


def _distancia_max(trayectoria: Trayectoria) -> float:
    """
    Calcula la distancia máxima desde el origen (0,0)
    hasta cualquier punto de una trayectoria.

    Esta función sirve para saber cuánto se aleja un trazo
    respecto al centro/origen del papel.
    """
    
    # Recorre todos los puntos de la trayectoria.
    #
    # Para cada punto (x, y), calcula:
    # math.hypot(x, y)
    #
    # Eso equivale a:
    # raíz cuadrada de x² + y²
    #
    # Es decir, la distancia desde el origen (0,0)
    # hasta ese punto.
    #
    # max(...) devuelve la distancia más grande encontrada.
    return max(math.hypot(x, y) for x, y in trayectoria)


def _dentro_alcance(trayectoria: Trayectoria, reach: float) -> bool:
    """True si TODOS los puntos de la trayectoria están dentro del alcance dado."""
    return all(math.hypot(x, y) <= reach for x, y in trayectoria)


def repartir_trayectorias(
    trayectorias: List[Trayectoria],
    semilla: int | None = None,
) -> Tuple[List[Trayectoria], List[Trayectoria]]:
    """
    Reparte trayectorias entre UR3e y UR5e.

    Parameters
    ----------
    trayectorias : lista de trayectorias métricas
    semilla : semilla aleatoria opcional (para reproducibilidad en pruebas)

    Returns
    -------
    (trayectorias_ur3e, trayectorias_ur5e)
    """
    if semilla is not None:
        random.seed(semilla)

    solo_ur5e = []    # Lista de trayectorias que solo puede dibujar el UR5e (fuera del alcance del UR3e). 
    compartidas = []  # Lista de trayectorias que pueden dibujar ambos robots.

    # Comprobar cada trayectoria y clasificarla 
    for t in trayectorias:
        if not _dentro_alcance(t, UR3E_MAX_REACH): # Si la trayectoria tiene algún punto fuera del alcance del UR3e,
                                                     # se asigna al UR5e.
            solo_ur5e.append(t)
        else:
            compartidas.append(t)

    log.info(
        f"Trayectorias totales: {len(trayectorias)} | "
        f"Solo UR5e (fuera alcance UR3e): {len(solo_ur5e)} | "
        f"Repartibles: {len(compartidas)}"
    )
   
    if not compartidas:
        #Mostramos AVISO; no es un error
        log.warning("Ninguna trayectoria está dentro del alcance del UR3e. "
                    "Todo el dibujo lo hará el UR5e.")
        return [], solo_ur5e

    # Mezclar aleatoriamente las compartidas y dividir ~50/50 
        # Para evitar que siempre le toque al mismo robot dibujar las mismas partes del dibujo,
    random.shuffle(compartidas)
    mitad = max(1, len(compartidas) // 2) # max(1, ...) para asegurar que al menos una trayectoria va al UR3e

    # Asigna al UR3e la primera mitad de las trayectorias compartidas.
    ur3e_list = compartidas[:mitad]
    
    # Asigna al UR5e:
    # - la segunda mitad de las trayectorias compartidas
    # - más todas las trayectorias que el UR3e no podía alcanzar
    ur5e_list = compartidas[mitad:] + solo_ur5e

    # Verificar que el UR5e puede alcanzar todo lo que se le asigna
    fuera_ur5e = [t for t in ur5e_list if not _dentro_alcance(t, UR5E_MAX_REACH)]
    
    # Si hay trayectorias fuera del alcance del UR5e, muestra un aviso.
    if fuera_ur5e:
        log.warning(
            f"{len(fuera_ur5e)} trayectorias podrían estar fuera del alcance del UR5e. "
            "Revisa MAX_ANCHO_M en config.py o la posición del papel."
        )

    log.info(
        f"Reparto final → UR3e: {len(ur3e_list)} trayectorias | "
        f"UR5e: {len(ur5e_list)} trayectorias"
    )

    return ur3e_list, ur5e_list


def resumen_reparto(
    ur3e: List[Trayectoria],
    ur5e: List[Trayectoria],
) -> str:
    """Devuelve un string con el resumen del reparto para el log."""
    def puntos(lst):
        return sum(len(t) for t in lst)

    # Devuelve un texto formateado con:
    # - número de trazos del UR3e
    # - número de puntos del UR3e
    # - número de trazos del UR5e
    # - número de puntos del UR5e
    return (
        f"UR3e → {len(ur3e)} trazos, {puntos(ur3e)} puntos  |  "
        f"UR5e → {len(ur5e)} trazos, {puntos(ur5e)} puntos"
    )
