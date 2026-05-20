"""
Pipeline FastSAM de detección de piezas cerámicas rectangulares.

Utiliza el modelo FastSAM de Ultralytics para segmentar instancias,
filtra por área, extrae propiedades geométricas con minAreaRect y
ordena las piezas en lectura.
"""

import json
import math
from pathlib import Path

import cv2
import numpy as np

from ultralytics import FastSAM


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
IMAGEN_ENTRADA = BASE_DIR / "assets" / "imagenes" / "DSC07665.jpg"
DIR_RESULTADOS = BASE_DIR / "resultados"
IMAGEN_SALIDA = DIR_RESULTADOS / "imagen1_resultado_fastsam.jpg"
JSON_SALIDA = DIR_RESULTADOS / "deteccion_fastsam.json"
MODELO_FASTSAM = BASE_DIR / "modelos" / "FastSAM-s.pt"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _normalizar_rect(w_rect: float, h_rect: float, angle: float) -> tuple[float, float, float]:
    """Normaliza ángulo a (-45, 45] y ancho/alto a corto/largo."""
    if angle < -45.0:
        angle += 90.0
        w_rect, h_rect = h_rect, w_rect
    ancho = min(w_rect, h_rect)
    alto = max(w_rect, h_rect)
    return ancho, alto, angle


def _escalar_contorno(cnt: np.ndarray, fx: float, fy: float) -> np.ndarray:
    """Escala un contorno de la resolución de máscara a la imagen original."""
    cnt_s = cnt.astype(np.float32)
    cnt_s[:, 0, 0] *= fx
    cnt_s[:, 0, 1] *= fy
    return cnt_s.astype(np.int32)


# ---------------------------------------------------------------------------
# Detección
# ---------------------------------------------------------------------------

def detectar_piezas(ruta_imagen: Path, modelo_path: Path = MODELO_FASTSAM) -> list[dict]:
    """
    Detecta piezas cerámicas rectangulares usando FastSAM.

    Retorna lista ordenada (izquierda→derecha, arriba→abajo) con:
        numero, centro_x, centro_y, ancho, alto, angulo_grados
    """
    img = cv2.imread(str(ruta_imagen))
    if img is None:
        raise FileNotFoundError(f"No se pudo cargar la imagen: {ruta_imagen}")

    h_orig, w_orig = img.shape[:2]

    model = FastSAM(str(modelo_path))
    # Usar tamaño original (ajustado a múltiplo de 32 por el modelo)
    results = model(str(ruta_imagen), device="cpu", verbose=False, imgsz=max(h_orig, w_orig))
    r = results[0]

    if r.masks is None:
        return []

    masks = r.masks.data.cpu().numpy()
    h_mask, w_mask = masks.shape[1:3]
    fx = w_orig / w_mask
    fy = h_orig / h_mask

    candidatos = []
    for idx, mask in enumerate(masks):
        if mask.sum() < 5_000:  # descartar ruido
            continue

        mask_uint8 = (mask > 0.5).astype(np.uint8) * 255
        cnts, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        cnt = max(cnts, key=cv2.contourArea)
        cnt = _escalar_contorno(cnt, fx, fy)

        area = cv2.contourArea(cnt)
        if area < 50_000 or area > 2_500_000:
            continue

        rect = cv2.minAreaRect(cnt)
        (cx, cy), (wr, hr), ang = rect
        area_bbox = max(wr * hr, 1.0)
        if area / area_bbox < 0.50:
            continue

        ancho, alto, angulo = _normalizar_rect(wr, hr, ang)

        candidatos.append({
            "centro_x": round(cx),
            "centro_y": round(cy),
            "ancho": round(ancho),
            "alto": round(alto),
            "angulo_grados": round(angulo, 2),
            "area": area,
            "_rect": rect,
            "_contour": cnt,
        })

    # Ordenar en lectura
    tolerancia_fila = h_orig * 0.12
    candidatos.sort(key=lambda p: (
        round(p["centro_y"] / tolerancia_fila),
        p["centro_x"]
    ))

    for i, pieza in enumerate(candidatos, start=1):
        pieza["numero"] = i

    return candidatos


# ---------------------------------------------------------------------------
# Anotación visual
# ---------------------------------------------------------------------------

def _punto_en_eje(cx: float, cy: float, angulo_rad: float,
                  longitud: float, eje: str) -> tuple[int, int]:
    if eje == "ancho":
        dx = math.cos(angulo_rad) * longitud / 2
        dy = math.sin(angulo_rad) * longitud / 2
    else:
        dx = math.cos(angulo_rad + math.pi / 2) * longitud / 2
        dy = math.sin(angulo_rad + math.pi / 2) * longitud / 2
    return (round(cx + dx), round(cy + dy))


def _texto_con_sombra(img: np.ndarray, texto: str, pos: tuple[int, int],
                      escala: float, color: tuple, grosor: int) -> None:
    fuente = cv2.FONT_HERSHEY_SIMPLEX
    off = max(1, round(grosor * 0.8))
    cv2.putText(img, texto, (pos[0] + off, pos[1] + off),
                fuente, escala, (0, 0, 0), grosor + 1, cv2.LINE_AA)
    cv2.putText(img, texto, pos, fuente, escala, color, grosor, cv2.LINE_AA)


def dibujar_anotaciones(img_original: np.ndarray, piezas: list[dict],
                        modo: str = "camara") -> np.ndarray:
    """
    Dibuja sobre una copia de la imagen las anotaciones de cada pieza.

    modo="camara"  → textos en píxeles (centro_x, centro_y, ancho, alto).
    modo="robot"   → textos en mm      (robot_x, robot_y, ancho_mm, alto_mm).
    """
    img = img_original.copy()
    h_img, w_img = img.shape[:2]
    escala_fuente = max(0.8, w_img / 2500)
    grosor = max(2, round(w_img / 1000))

    es_robot = (modo == "robot")

    for pieza in piezas:
        cx = pieza["centro_x"]
        cy = pieza["centro_y"]
        rect = pieza["_rect"]
        angulo = pieza["angulo_grados"]
        numero = pieza["numero"]

        if es_robot:
            cx_texto = pieza.get("robot_x", cx)
            cy_texto = pieza.get("robot_y", cy)
            ancho_texto = pieza.get("ancho_mm", pieza["ancho"])
            alto_texto = pieza.get("alto_mm", pieza["alto"])
            unidad = "mm"
        else:
            cx_texto = cx
            cy_texto = cy
            ancho_texto = pieza["ancho"]
            alto_texto = pieza["alto"]
            unidad = "px"

        ancho = pieza["ancho"]
        alto = pieza["alto"]
        ang_rad = math.radians(angulo)

        box = np.int32(cv2.boxPoints(rect))
        cv2.drawContours(img, [box], 0, (0, 220, 0), grosor + 1)

        r = max(8, round(w_img / 300))
        cv2.circle(img, (cx, cy), r, (0, 0, 220), -1)
        cv2.circle(img, (cx, cy), r + 2, (255, 255, 255), 2)
        off_txt = round(r * 1.8)
        _texto_con_sombra(img, f"({cx_texto:.1f}, {cy_texto:.1f})",
                          (cx + off_txt, cy - off_txt),
                          escala_fuente * 0.85, (255, 255, 255), grosor)

        pto_sup = box[box[:, 1].argmin()]
        pos_num = (pto_sup[0] - round(escala_fuente * 25),
                   pto_sup[1] - round(escala_fuente * 15))
        _texto_con_sombra(img, str(numero), pos_num,
                          escala_fuente * 1.6, (0, 220, 255), grosor + 1)

        p1 = _punto_en_eje(cx, cy, ang_rad, alto, "alto")
        p2 = _punto_en_eje(cx, cy, ang_rad, -alto, "alto")
        cv2.line(img, p1, p2, (0, 140, 255), grosor)
        mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
        _texto_con_sombra(img, f"H:{alto_texto:.1f}{unidad}",
                          (mid[0] + 5, mid[1] - 5),
                          escala_fuente * 0.8, (0, 140, 255), grosor)

        p3 = _punto_en_eje(cx, cy, ang_rad, ancho, "ancho")
        p4 = _punto_en_eje(cx, cy, ang_rad, -ancho, "ancho")
        cv2.line(img, p3, p4, (255, 200, 0), grosor)
        mid2 = ((p3[0] + p4[0]) // 2, (p3[1] + p4[1]) // 2)
        _texto_con_sombra(img, f"W:{ancho_texto:.1f}{unidad}",
                          (mid2[0] + 5, mid2[1] + 5),
                          escala_fuente * 0.8, (255, 200, 0), grosor)

        _texto_con_sombra(img, f"{angulo:.1f}\u00b0",
                          (cx + off_txt, cy + off_txt + round(escala_fuente * 22)),
                          escala_fuente * 0.75, (200, 200, 255), grosor)

    return img


# ---------------------------------------------------------------------------
# Serialización JSON
# ---------------------------------------------------------------------------

def guardar_json(piezas: list[dict], ruta_imagen: Path, ruta_salida: Path) -> None:
    campos = ["numero", "centro_x", "centro_y", "ancho", "alto", "angulo_grados"]
    datos = {
        "imagen": ruta_imagen.name,
        "total_piezas": len(piezas),
        "piezas": [{k: p[k] for k in campos} for p in piezas],
    }
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main interno
# ---------------------------------------------------------------------------

def main() -> None:
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)

    print(f"Procesando: {IMAGEN_ENTRADA}")
    piezas = detectar_piezas(IMAGEN_ENTRADA)

    print(f"\nPiezas detectadas: {len(piezas)}\n")
    print(f"{'N°':>3}  {'Centro':^18}  {'Ancho':>7}  {'Alto':>7}  {'Ángulo':>9}")
    print("-" * 55)
    for p in piezas:
        print(
            f"{p['numero']:>3}  "
            f"({p['centro_x']:>5}, {p['centro_y']:>5})  "
            f"{p['ancho']:>7}px  "
            f"{p['alto']:>7}px  "
            f"{p['angulo_grados']:>8.2f}°"
        )

    img = cv2.imread(str(IMAGEN_ENTRADA))
    img_anotada = dibujar_anotaciones(img, piezas)

    cv2.imwrite(str(IMAGEN_SALIDA), img_anotada)
    print(f"\nImagen guardada: {IMAGEN_SALIDA}")

    guardar_json(piezas, IMAGEN_ENTRADA, JSON_SALIDA)
    print(f"JSON guardado:   {JSON_SALIDA}")


if __name__ == "__main__":
    main()
