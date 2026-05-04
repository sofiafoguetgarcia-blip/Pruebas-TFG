# -*- coding: utf-8 -*-
"""
image_processing.py
===================
Preprocesado de imagen y detección de bordes (Canny + gradiente morfológico).
Idéntico al proyecto single-robot — no depende de cuántos robots haya.
"""

import cv2
import numpy as np
import logging
import os

from config_solucion import (
    CANNY_FINO_LOW, CANNY_FINO_HIGH,
    CANNY_GRUESO_LOW, CANNY_GRUESO_HIGH,
)

log = logging.getLogger(__name__)


def cargar_imagen(path: str) -> np.ndarray:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No existe la imagen: {path}")
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"OpenCV no pudo leer la imagen: {path}")
    log.info(f"Imagen cargada: {path}  ({img.shape[1]}x{img.shape[0]} px)")
    return img


def preprocesar_imagen(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    edges_fino   = cv2.Canny(blur, CANNY_FINO_LOW,   CANNY_FINO_HIGH)
    edges_grueso = cv2.Canny(blur, CANNY_GRUESO_LOW,  CANNY_GRUESO_HIGH)

    kernel = np.ones((3, 3), np.uint8)
    grad   = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)
    _, edges_grad = cv2.threshold(grad, 15, 255, cv2.THRESH_BINARY)

    edges = cv2.bitwise_or(edges_fino,  edges_grueso)
    edges = cv2.bitwise_or(edges,       edges_grad)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)

    log.debug("Preprocesado completado.")
    return edges


def guardar_debug(edges: np.ndarray, path: str = "debug_edges.png") -> None:
    cv2.imwrite(path, edges)
    log.info(f"Imagen de bordes guardada en: {path}")
