# -*- coding: utf-8 -*-
"""
transform_ur5_to_ur3.py
=======================
Conversión auxiliar de una pose TCP del UR5e a la pose TCP equivalente del UR3e.

Idea:
    Si el punto del UR5e está bien medido en el espacio compartido, este módulo
    calcula dónde debería ir el UR3e para llegar al MISMO punto físico del papel.

IMPORTANTE:
    La conversión usa dos puntos de calibración que representan el mismo punto
    físico visto desde cada base:

        UR5E_REF_POSE  -> pose correcta del UR5e en el punto común
        UR3E_REF_POSE  -> pose equivalente del UR3e en ese mismo punto común

    Si el UR3e queda desplazado, NO cambies todo el programa: ajusta solamente
    UR3E_REF_POSE o los signos AXIS_SIGN_X / AXIS_SIGN_Y.
"""

from __future__ import annotations

from typing import Iterable, List

# -----------------------------------------------------------------------------
# PUNTO DE CALIBRACIÓN COMÚN
# -----------------------------------------------------------------------------
# Este punto del UR5e es el que tú dices que está correcto.
UR5E_REF_POSE = [0.68387, -0.03000, 0.00221, 2.481, -1.927, 0.0]

# Este debe ser el MISMO punto físico, pero medido con el UR3e.
# He dejado el valor que teníamos como origen bueno en pruebas anteriores.
UR3E_REF_POSE = [-0.52777, -0.01601, 0.00821, 1.346, 2.839, 0.0]

# -----------------------------------------------------------------------------
# RELACIÓN ENTRE EJES
# -----------------------------------------------------------------------------
# Como los robots están enfrentados, normalmente X va invertido.
# Si al mover +X en UR5e el UR3e también debe aumentar X, pon AXIS_SIGN_X = +1.
AXIS_SIGN_X = -1.0
AXIS_SIGN_Y = +1.0

# En Z normalmente NO interesa copiar la Z exacta del UR5e, porque cada robot tiene
# su propia altura/base/TCP. Por eso se mantiene la Z de referencia del UR3e.
COPY_Z_OFFSET = False


def convertir_pose_ur5_a_ur3(pose_ur5: Iterable[float]) -> List[float]:
    """
    Convierte una pose [x, y, z, rx, ry, rz] del UR5e a una pose equivalente del UR3e.

    Parameters
    ----------
    pose_ur5:
        Pose TCP del UR5e en metros/radianes.

    Returns
    -------
    list[float]
        Pose TCP equivalente para el UR3e.
    """
    p5 = list(pose_ur5) # Aseguramos que es una lista para poder indexar. También convertimos a float si viene en otro formato.
    if len(p5) != 6:    # La pose debe tener 6 valores: x, y, z, rx, ry, rz.
        raise ValueError("La pose del UR5e debe tener 6 valores: [x, y, z, rx, ry, rz]")

    dx5 = p5[0] - UR5E_REF_POSE[0]  # Diferencia en X entre la pose dada y la pose de referencia del UR5e.
    dy5 = p5[1] - UR5E_REF_POSE[1]  # Diferencia en Y entre la pose dada y la pose de referencia del UR5e.
    dz5 = p5[2] - UR5E_REF_POSE[2]  # Diferencia en Z entre la pose dada y la pose de referencia del UR5e.

    x3 = UR3E_REF_POSE[0] + AXIS_SIGN_X * dx5                          # Calculamos la X equivalente para el UR3e, aplicando el signo de inversión si es necesario. 
    y3 = UR3E_REF_POSE[1] + AXIS_SIGN_Y * dy5                          # Calculamos la Y equivalente para el UR3e, aplicando el signo de inversión si es necesario.
    z3 = UR3E_REF_POSE[2] + dz5 if COPY_Z_OFFSET else UR3E_REF_POSE[2] # Calculamos la Z equivalente para el UR3e.
    # Si COPY_Z_OFFSET es False, simplemente usamos la Z de referencia del UR3e, ignorando la Z del UR5e.

    # La orientación del UR3e se deja fija con la orientación calibrada del lápiz.
    rx3, ry3, rz3 = UR3E_REF_POSE[3], UR3E_REF_POSE[4], UR3E_REF_POSE[5] 

    return [x3, y3, z3, rx3, ry3, rz3]


def formatear_pose(pose: Iterable[float]) -> str:
    return "[" + ", ".join(f"{v:.5f}" for v in pose) + "]"  # Formatea la pose con 5 decimales para una visualización más clara.


if __name__ == "__main__":
    # Prueba rápida: al meter el punto correcto del UR5e, debe devolver el punto común del UR3e.
    pose_ur5 = UR5E_REF_POSE
    pose_ur3 = convertir_pose_ur5_a_ur3(pose_ur5)

    print("POSE UR5e entrada :", formatear_pose(pose_ur5))
    print("POSE UR3e calculada:", formatear_pose(pose_ur3))
    print("\nCopia esta pose en el origen del UR3e si al probar ves que coincide físicamente.")
