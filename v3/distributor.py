# -*- coding: utf-8 -*-
"""
distributor.py
==============
Reparto de trayectorias entre el UR3e y el UR5e.

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

from config_solucion import UR3E_MAX_REACH, UR5E_MAX_REACH

log = logging.getLogger(__name__)

Punto       = Tuple[float, float]
Trayectoria = List[Punto]


def _distancia_max(trayectoria: Trayectoria) -> float:
    """Distancia máxima desde el origen (0,0) de cualquier punto de la trayectoria."""
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

    solo_ur5e = []     # fuera del alcance del UR3e → forzosamente al UR5e
    compartidas = []   # pueden ir a cualquiera de los dos

    for t in trayectorias:
        if not _dentro_alcance(t, UR3E_MAX_REACH):
            solo_ur5e.append(t)
        else:
            compartidas.append(t)

    log.info(
        f"Trayectorias totales: {len(trayectorias)} | "
        f"Solo UR5e (fuera alcance UR3e): {len(solo_ur5e)} | "
        f"Repartibles: {len(compartidas)}"
    )

    if not compartidas:
        log.warning("Ninguna trayectoria está dentro del alcance del UR3e. "
                    "Todo el dibujo lo hará el UR5e.")
        return [], solo_ur5e

    # Mezclar aleatoriamente las compartidas y dividir ~50/50
    random.shuffle(compartidas)
    mitad = max(1, len(compartidas) // 2)

    ur3e_list = compartidas[:mitad]
    ur5e_list = compartidas[mitad:] + solo_ur5e

    # Verificar que el UR5e puede alcanzar todo lo que se le asigna
    fuera_ur5e = [t for t in ur5e_list if not _dentro_alcance(t, UR5E_MAX_REACH)]
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

    return (
        f"UR3e → {len(ur3e)} trazos, {puntos(ur3e)} puntos  |  "
        f"UR5e → {len(ur5e)} trazos, {puntos(ur5e)} puntos"
    )
