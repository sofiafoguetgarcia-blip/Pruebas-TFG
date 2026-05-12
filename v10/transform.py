# -*- coding: utf-8 -*-
"""
transform.py
============
Transformaciones básicas entre UR5e y UR3e para la demo actual.

IMPORTANTE:
Los robots están en mesas distintas y enfrentados.
Por eso el mismo punto físico NO tiene las mismas coordenadas en ambos robots.

La zona compartida se define con dos poses:
- DROP_ZONE_UR5E: mismo punto físico visto desde UR5e.
- DROP_ZONE_UR3E: mismo punto físico visto desde UR3e.
"""

from __future__ import annotations
from typing import Iterable, List, Tuple

from config import DROP_ZONE_UR5E, DROP_ZONE_UR3E


# Según la foto:
# UR5e está a la izquierda.
# UR3e está a la derecha.
# Están enfrentados hacia la zona central.
#
# Lo más normal es invertir el eje X o Y según cómo hayas definido las bases.
# Para tu caso inicial dejamos:
AXIS_SIGN_X = 1.0
AXIS_SIGN_Y = -1.0

# La Z NO se transforma porque cada robot detecta la mesa con fuerza.
COPY_Z_OFFSET = False


def _validar_pose(pose: Iterable[float], nombre: str) -> List[float]:
    p = [float(v) for v in pose]
    if len(p) != 6:
        raise ValueError(f"{nombre} debe tener 6 valores: [x, y, z, rx, ry, rz]")
    return p


def formatear_pose(pose: Iterable[float]) -> str:
    return "[" + ", ".join(f"{float(v):.5f}" for v in pose) + "]"


def obtener_drop_zones() -> Tuple[List[float], List[float]]:
    """
    Devuelve:
        drop_zone_ur3e, drop_zone_ur5e
    """
    return list(DROP_ZONE_UR3E), list(DROP_ZONE_UR5E)


def convertir_pose(pose: Iterable[float], desde: str, hacia: str) -> List[float]:
    """
    Convierte una pose aproximada entre robots usando la zona compartida
    como punto de referencia común.

    OJO:
    Esto sirve para desplazamientos relativos simples.
    Para precisión real se necesita calibración con varios puntos.
    """
    desde = desde.lower().strip()
    hacia = hacia.lower().strip()

    if desde not in ("ur3e", "ur5e"):
        raise ValueError("desde debe ser 'ur3e' o 'ur5e'")
    if hacia not in ("ur3e", "ur5e"):
        raise ValueError("hacia debe ser 'ur3e' o 'ur5e'")

    p = _validar_pose(pose, f"pose_{desde}")

    if desde == hacia:
        return p

    if desde == "ur5e" and hacia == "ur3e":
        ref_from = DROP_ZONE_UR5E
        ref_to = DROP_ZONE_UR3E
    else:
        ref_from = DROP_ZONE_UR3E
        ref_to = DROP_ZONE_UR5E

    dx = p[0] - ref_from[0]
    dy = p[1] - ref_from[1]
    dz = p[2] - ref_from[2]

    x = ref_to[0] + AXIS_SIGN_X * dx
    y = ref_to[1] + AXIS_SIGN_Y * dy

    if COPY_Z_OFFSET:
        z = ref_to[2] + dz
    else:
        z = ref_to[2]

    rx = ref_to[3]
    ry = ref_to[4]
    rz = ref_to[5]

    return [x, y, z, rx, ry, rz]


def pose_pieza_en_ur3e(pose_pieza_ur5e: Iterable[float]) -> List[float]:
    return convertir_pose(pose_pieza_ur5e, desde="ur5e", hacia="ur3e")


def pose_pieza_en_ur5e(pose_pieza_ur3e: Iterable[float]) -> List[float]:
    return convertir_pose(pose_pieza_ur3e, desde="ur3e", hacia="ur5e")


if __name__ == "__main__":
    dz3, dz5 = obtener_drop_zones()

    print("DROP_ZONE UR3e:", formatear_pose(dz3))
    print("DROP_ZONE UR5e:", formatear_pose(dz5))

    ejemplo_ur5 = [
        DROP_ZONE_UR5E[0] + 0.05,
        DROP_ZONE_UR5E[1] + 0.02,
        DROP_ZONE_UR5E[2],
        DROP_ZONE_UR5E[3],
        DROP_ZONE_UR5E[4],
        DROP_ZONE_UR5E[5],
    ]

    print("Ejemplo UR5e:", formatear_pose(ejemplo_ur5))
    print("Convertido a UR3e:", formatear_pose(pose_pieza_en_ur3e(ejemplo_ur5)))