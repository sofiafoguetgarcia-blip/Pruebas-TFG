# -*- coding: utf-8 -*-
"""
transform_ur5_to_ur3.py
=======================
Módulo auxiliar de transformación entre referencias UR3e y UR5e.

Ahora NO obliga a usar siempre el UR5e como referencia. Desde main.py puedes elegir:

    --base-origen ur3e   -> el origen bueno/manual es el del UR3e y se calcula el UR5e
    --base-origen ur5e   -> el origen bueno/manual es el del UR5e y se calcula el UR3e

La idea es que el dibujo sigue estando expresado como puntos (x, y) alrededor de un
origen común del papel, pero tú decides qué robot manda en la calibración.

IMPORTANTE:
    UR3E_REF_POSE y UR5E_REF_POSE deben ser el MISMO punto físico del papel,
    medido desde la base de cada robot.
"""

from __future__ import annotations
from typing import Iterable, List, Tuple

# -----------------------------------------------------------------------------
# PUNTO DE CALIBRACIÓN COMÚN
# -----------------------------------------------------------------------------
# Mismo punto físico visto desde UR5e
UR5E_REF_POSE = [0.68387, -0.03000, 0.00221, 2.481, -1.927, 0.0]

# Mismo punto físico visto desde UR3e
# Ajusta esta pose si el UR3e no cae exactamente en el origen del papel.
UR3E_REF_POSE = [-0.52777, -0.01601, 0.00821, 1.346, 2.839, 0.0]

# -----------------------------------------------------------------------------
# RELACIÓN ENTRE EJES
# -----------------------------------------------------------------------------
# Como los robots están enfrentados, normalmente X va invertido.
AXIS_SIGN_X = -1.0
AXIS_SIGN_Y = +1.0

# En Z no copiamos normalmente el offset entre robots porque cada TCP/herramienta
# tiene su propia altura. Para el dibujo, cada robot detecta la mesa por fuerza.
COPY_Z_OFFSET = False


def _validar_pose(pose: Iterable[float], nombre: str) -> List[float]:
    p = [float(v) for v in pose]
    if len(p) != 6:
        raise ValueError(f"{nombre} debe tener 6 valores: [x, y, z, rx, ry, rz]")
    return p


def convertir_pose(pose: Iterable[float], desde: str, hacia: str) -> List[float]:
    """
    Convierte una pose TCP de un robot al otro usando el punto común calibrado.

    Parameters
    ----------
    pose:
        Pose [x, y, z, rx, ry, rz] en el robot de origen.
    desde:
        'ur3e' o 'ur5e'.
    hacia:
        'ur3e' o 'ur5e'.
    """
    desde = desde.lower().strip()
    hacia = hacia.lower().strip()
    if desde not in ("ur3e", "ur5e") or hacia not in ("ur3e", "ur5e"):
        raise ValueError("desde/hacia deben ser 'ur3e' o 'ur5e'")

    p = _validar_pose(pose, f"pose {desde}")
    if desde == hacia:
        return p

    if desde == "ur5e" and hacia == "ur3e":
        ref_from = UR5E_REF_POSE
        ref_to = UR3E_REF_POSE
        sx, sy = AXIS_SIGN_X, AXIS_SIGN_Y
    elif desde == "ur3e" and hacia == "ur5e":
        ref_from = UR3E_REF_POSE
        ref_to = UR5E_REF_POSE
        # Inversa de la transformación. Como los signos son +/-1, la inversa es igual.
        sx, sy = AXIS_SIGN_X, AXIS_SIGN_Y

    dx = p[0] - ref_from[0]
    dy = p[1] - ref_from[1]
    dz = p[2] - ref_from[2]

    x = ref_to[0] + sx * dx
    y = ref_to[1] + sy * dy
    z = ref_to[2] + dz if COPY_Z_OFFSET else ref_to[2]

    # La orientación se toma de la referencia del robot destino.
    rx, ry, rz = ref_to[3], ref_to[4], ref_to[5]
    return [x, y, z, rx, ry, rz]


def obtener_origenes(base_origen: str = "ur3e") -> Tuple[List[float], List[float]]:
    """
    Devuelve (origen_ur3e, origen_ur5e) según el robot elegido como base.

    base_origen='ur3e': usa UR3E_REF_POSE como origen real y calcula UR5e.
    base_origen='ur5e': usa UR5E_REF_POSE como origen real y calcula UR3e.
    """
    base = base_origen.lower().strip()
    if base == "ur3e":
        origen_ur3e = list(UR3E_REF_POSE)
        origen_ur5e = convertir_pose(UR3E_REF_POSE, desde="ur3e", hacia="ur5e")
    elif base == "ur5e":
        origen_ur5e = list(UR5E_REF_POSE)
        origen_ur3e = convertir_pose(UR5E_REF_POSE, desde="ur5e", hacia="ur3e")
    else:
        raise ValueError("base_origen debe ser 'ur3e' o 'ur5e'")
    return origen_ur3e, origen_ur5e


# Compatibilidad con versiones anteriores del proyecto.
def convertir_pose_ur5_a_ur3(pose_ur5: Iterable[float]) -> List[float]:
    return convertir_pose(pose_ur5, desde="ur5e", hacia="ur3e")


def convertir_pose_ur3_a_ur5(pose_ur3: Iterable[float]) -> List[float]:
    return convertir_pose(pose_ur3, desde="ur3e", hacia="ur5e")


def formatear_pose(pose: Iterable[float]) -> str:
    return "[" + ", ".join(f"{float(v):.5f}" for v in pose) + "]"


if __name__ == "__main__":
    for base in ("ur3e", "ur5e"):
        o3, o5 = obtener_origenes(base)
        print(f"\nBASE: {base}")
        print("ORIGEN UR3e:", formatear_pose(o3))
        print("ORIGEN UR5e:", formatear_pose(o5))
