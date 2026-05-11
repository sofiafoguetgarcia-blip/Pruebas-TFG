# -*- coding: utf-8 -*-
"""Convierte bordes de una imagen en trayectorias 2D métricas para el UR3e."""

from typing import List, Tuple
import logging
import cv2
import numpy as np

from config import EPSILON_PX, DECIMATE_STEP, MIN_PUNTOS_CONTORNO, MIN_LONGITUD_PX, MAX_PUNTOS_TOTAL

log = logging.getLogger(__name__)
Punto = Tuple[float, float]
Trayectoria = List[Punto]


def extraer_trayectorias(edges: np.ndarray, img_shape: Tuple[int, int], ancho_dibujo_m: float) -> List[Trayectoria]:
    """
    Devuelve trayectorias centradas en (0,0), escaladas a ancho_dibujo_m.
    Así el dibujo se adapta al tamaño de la baldosa detectada.
    """
    img_h, img_w = img_shape[:2]
    
    #oso
        #escala = ancho_dibujo_m * 2.0 / float(img_w)
        
    #flor
    escala = ancho_dibujo_m / float(img_w)

    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError("No se detectaron contornos en la imagen de dibujo.")

    contours = sorted(contours, key=lambda c: cv2.arcLength(c, False), reverse=True)
    trayectorias: List[Trayectoria] = []
    total_puntos = 0
    descartados = 0

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w >= img_w * 0.98 or h >= img_h * 0.98:
            descartados += 1
            continue
        if cv2.arcLength(c, False) < MIN_LONGITUD_PX:
            descartados += 1
            continue

        approx = cv2.approxPolyDP(c, EPSILON_PX, closed=False)
        pts = approx.reshape(-1, 2)
        if DECIMATE_STEP > 1:
            pts = pts[::DECIMATE_STEP]
        if len(pts) < MIN_PUNTOS_CONTORNO:
            descartados += 1
            continue

        trayectoria = [
            ((px - img_w / 2.0) * escala, -(py - img_h / 2.0) * escala)
            for px, py in pts
        ]
        trayectorias.append(trayectoria)
        total_puntos += len(trayectoria)

        if total_puntos >= MAX_PUNTOS_TOTAL:
            log.warning(f"Límite de {MAX_PUNTOS_TOTAL} puntos alcanzado.")
            break

    if not trayectorias:
        raise ValueError("No hay trayectorias válidas tras el filtrado.")

    log.info(
        f"Trayectorias válidas: {len(trayectorias)} | puntos={total_puntos} | "
        f"descartados={descartados} | ancho dibujo={ancho_dibujo_m*1000:.1f} mm"
    )
    return trayectorias
