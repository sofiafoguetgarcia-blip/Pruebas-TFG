"""
Sistema de detección de piezas cerámicas para cobot UR.

Pipeline configurable:
  - PIPELINE = "clasico"  → scripts/pipeline_clasico.py
  - PIPELINE = "fastsam"  → scripts/pipeline_fastsam.py

Flujo:
  1. Detectar piezas con el pipeline elegido.
  2. Detectar cruces de referencia de calibración.
  3. Convertir coordenadas píxeles → coordenadas robot (mm).
  4. Generar resultados/datos_robot.json con puntos para el robot.
"""

import json
import math
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
PIPELINE = "clasico"  # Cambiar a "fastsam" para usar FastSAM

BASE_DIR = Path(__file__).parent
IMAGEN_ENTRADA = BASE_DIR / "assets" / "imagenes" / "DSC07665.jpg"
DIR_RESULTADOS = BASE_DIR / "resultados"
JSON_ROBOT = DIR_RESULTADOS / "datos_robot.json"

# Referencias: píxeles en imagen  ↔  mm en sistema del robot
REF1_PX = (383.0, 495.0)
REF1_ROBOT = (263.93, -239.43)
REF2_PX = (2189.0, 2382.0)
REF2_ROBOT = (-363.60, -822.42)


# ---------------------------------------------------------------------------
# Importar pipeline elegido
# ---------------------------------------------------------------------------
if PIPELINE == "clasico":
    from scripts.pipeline_clasico import detectar_piezas, dibujar_anotaciones
    IMAGEN_ANOTADA = DIR_RESULTADOS / "imagen1_resultado.jpg"
    JSON_DETECCION = DIR_RESULTADOS / "deteccion.json"
elif PIPELINE == "fastsam":
    from scripts.pipeline_fastsam import detectar_piezas, dibujar_anotaciones
    IMAGEN_ANOTADA = DIR_RESULTADOS / "imagen1_resultado_fastsam.jpg"
    JSON_DETECCION = DIR_RESULTADOS / "deteccion_fastsam.json"
else:
    raise ValueError(f"PIPELINE desconocido: {PIPELINE}. Usar 'clasico' o 'fastsam'.")


# ---------------------------------------------------------------------------
# Calibración píxeles → robot
# ---------------------------------------------------------------------------

def calcular_calibracion(
    ref1_px: tuple[float, float],
    ref1_robot: tuple[float, float],
    ref2_px: tuple[float, float],
    ref2_robot: tuple[float, float],
) -> dict:
    """
    Calcula la transformación lineal píxeles → robot.

    Asume alineación de ejes (sin rotación). Devuelve escalas y offsets.
    """
    x1p, y1p = ref1_px
    x2p, y2p = ref2_px
    x1r, y1r = ref1_robot
    x2r, y2r = ref2_robot

    dx_p = x2p - x1p
    dy_p = y2p - y1p
    dx_r = x2r - x1r
    dy_r = y2r - y1r

    escala_x = dx_r / dx_p if dx_p != 0 else 0.0
    escala_y = dy_r / dy_p if dy_p != 0 else 0.0

    offset_x = x1r - escala_x * x1p
    offset_y = y1r - escala_y * y1p

    return {
        "escala_x": escala_x,
        "escala_y": escala_y,
        "offset_x": offset_x,
        "offset_y": offset_y,
    }


def pixel_a_robot(
    px: float,
    py: float,
    cal: dict,
) -> tuple[float, float]:
    """Convierte coordenadas píxeles a coordenadas robot (mm)."""
    rx = cal["escala_x"] * px + cal["offset_x"]
    ry = cal["escala_y"] * py + cal["offset_y"]
    return rx, ry


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)

    print(f"Pipeline seleccionado: {PIPELINE.upper()}")
    print(f"Imagen: {IMAGEN_ENTRADA}")

    # ── 1. Detectar piezas ────────────────────────────────────────────────
    piezas = detectar_piezas(IMAGEN_ENTRADA)
    print(f"\nPiezas detectadas: {len(piezas)}")
    print(f"{'N°':>3}  {'Centro (px)':^18}  {'Ancho':>7}  {'Alto':>7}  {'Ángulo':>9}")
    print("-" * 55)
    for p in piezas:
        print(
            f"{p['numero']:>3}  "
            f"({p['centro_x']:>5}, {p['centro_y']:>5})  "
            f"{p['ancho']:>7}px  "
            f"{p['alto']:>7}px  "
            f"{p['angulo_grados']:>8.2f}°"
        )

    # ── 2. Detectar referencias ───────────────────────────────────────────
    from scripts.deteccion_referencias import detectar_referencias, dibujar_referencias

    refs = detectar_referencias(IMAGEN_ENTRADA)
    ref1_px_detectado = refs["ref1"]
    ref2_px_detectado = refs["ref2"]

    print("\nReferencias detectadas:")
    print(f"  Ref 1 (img):  ({ref1_px_detectado[0]:.2f}, {ref1_px_detectado[1]:.2f})")
    print(f"  Ref 2 (img):  ({ref2_px_detectado[0]:.2f}, {ref2_px_detectado[1]:.2f})")

    # ── 3. Calibrar ───────────────────────────────────────────────────────
    cal = calcular_calibracion(
        ref1_px_detectado, REF1_ROBOT,
        ref2_px_detectado, REF2_ROBOT,
    )
    print("\nParámetros de calibración:")
    print(f"  escala_x = {cal['escala_x']:.6f} mm/px")
    print(f"  escala_y = {cal['escala_y']:.6f} mm/px")
    print(f"  offset_x = {cal['offset_x']:.2f} mm")
    print(f"  offset_y = {cal['offset_y']:.2f} mm")

    # ── 4. Convertir piezas a coordenadas robot ───────────────────────────
    piezas_robot = []
    for p in piezas:
        rx, ry = pixel_a_robot(p["centro_x"], p["centro_y"], cal)
        escala_media = (abs(cal["escala_x"]) + abs(cal["escala_y"])) / 2
        ancho_mm = p["ancho"] * escala_media
        alto_mm = p["alto"] * escala_media

        pr = {
            "numero": p["numero"],
            "robot_x": round(rx, 2),
            "robot_y": round(ry, 2),
            "ancho_mm": round(ancho_mm, 2),
            "alto_mm": round(alto_mm, 2),
            "angulo_grados": p["angulo_grados"],
        }
        piezas_robot.append(pr)

        # Añadir campos robot al diccionario original para dibujar anotaciones
        p["robot_x"] = pr["robot_x"]
        p["robot_y"] = pr["robot_y"]
        p["ancho_mm"] = pr["ancho_mm"]
        p["alto_mm"] = pr["alto_mm"]

    # ── 5. Guardar imágenes anotadas (cámara + robot) ─────────────────────
    img = cv2.imread(str(IMAGEN_ENTRADA))

    # Modo cámara (px)
    img_anotada = dibujar_anotaciones(img, piezas, modo="camara")
    dibujar_referencias(img_anotada, refs)
    cv2.imwrite(str(IMAGEN_ANOTADA), img_anotada)
    print(f"\nImagen anotada guardada: {IMAGEN_ANOTADA}")

    # Modo robot (mm)
    if PIPELINE == "clasico":
        IMAGEN_ANOTADA_ROBOT = DIR_RESULTADOS / "imagen1_resultado_robot.jpg"
    else:
        IMAGEN_ANOTADA_ROBOT = DIR_RESULTADOS / f"imagen1_resultado_{PIPELINE}_robot.jpg"
    img_anotada_robot = dibujar_anotaciones(img, piezas, modo="robot")
    dibujar_referencias(img_anotada_robot, refs)
    cv2.imwrite(str(IMAGEN_ANOTADA_ROBOT), img_anotada_robot)
    print(f"Imagen robot guardada:   {IMAGEN_ANOTADA_ROBOT}")

    # Guardar JSON de detección en px
    campos_deteccion = ["numero", "centro_x", "centro_y", "ancho", "alto", "angulo_grados"]
    with open(JSON_DETECCION, "w", encoding="utf-8") as f:
        json.dump(
            {
                "imagen": IMAGEN_ENTRADA.name,
                "total_piezas": len(piezas),
                "piezas": [{k: p[k] for k in campos_deteccion} for p in piezas],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"JSON detección guardado: {JSON_DETECCION}")

    # ── 5. Generar datos_robot.json ───────────────────────────────────────
    datos_salida = {
        "imagen": IMAGEN_ENTRADA.name,
        "pipeline": PIPELINE,
        "total_piezas": len(piezas_robot),
        "piezas": piezas_robot,
        "calibracion": {
            "ref1_px": {"x": round(ref1_px_detectado[0], 2), "y": round(ref1_px_detectado[1], 2)},
            "ref1_robot": {"x": REF1_ROBOT[0], "y": REF1_ROBOT[1]},
            "ref2_px": {"x": round(ref2_px_detectado[0], 2), "y": round(ref2_px_detectado[1], 2)},
            "ref2_robot": {"x": REF2_ROBOT[0], "y": REF2_ROBOT[1]},
            "escala_x_mm_px": round(cal["escala_x"], 6),
            "escala_y_mm_px": round(cal["escala_y"], 6),
            "offset_x_mm": round(cal["offset_x"], 2),
            "offset_y_mm": round(cal["offset_y"], 2),
        },
    }

    with open(JSON_ROBOT, "w", encoding="utf-8") as f:
        json.dump(datos_salida, f, indent=2, ensure_ascii=False)

    print(f"\nJSON robot guardado: {JSON_ROBOT}")
    print("\nPiezas en coordenadas robot:")
    print(f"{'N°':>3}  {'Robot X (mm)':>12}  {'Robot Y (mm)':>12}  {'Ancho':>8}  {'Alto':>8}  {'Ángulo':>9}")
    print("-" * 65)
    for p in piezas_robot:
        print(
            f"{p['numero']:>3}  "
            f"{p['robot_x']:>12.2f}  "
            f"{p['robot_y']:>12.2f}  "
            f"{p['ancho_mm']:>7.1f}mm  "
            f"{p['alto_mm']:>7.1f}mm  "
            f"{p['angulo_grados']:>8.2f}°"
        )


if __name__ == "__main__":
    main()
