# -*- coding: utf-8 -*-
"""
image_processing.py
===================
Preprocesa la imagen del dibujo que luego ejecutara el UR3e.

El objetivo es extraer los bordes de la imagen de forma robusta.
Se usan dos pasadas de Canny con umbrales distintos (uno mas fino y
otro mas grueso) y ademas el gradiente morfologico. Los tres resultados
se combinan para no perder detalles ni lineas finas.

Al final se guarda una imagen de debug para poder ver que bordes
se han detectado antes de mandar nada al robot.
"""

import os
import logging
import cv2
import numpy as np

from config import CANNY_FINO_LOW, CANNY_FINO_HIGH, CANNY_GRUESO_LOW, CANNY_GRUESO_HIGH

log = logging.getLogger(__name__)


def cargar_imagen(path: str) -> np.ndarray:
    """
    Carga la imagen del dibujo desde disco.
    Si el archivo no existe o no se puede leer, lanza un error claro
    en lugar de fallar de forma misteriosa mas adelante.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No existe la imagen de dibujo: {path}")
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"OpenCV no pudo leer la imagen: {path}")
    log.info(f"Imagen de dibujo cargada: {path} ({img.shape[1]}x{img.shape[0]} px)")
    return img


def preprocesar_imagen(img: np.ndarray) -> np.ndarray:
    """
    Extrae los bordes de la imagen usando tres metodos distintos y combinandolos.

    Proceso paso a paso:
    1. Convertir a escala de grises.
    2. Suavizar con Gaussian Blur para reducir el ruido.
    3. Canny con umbrales finos (detecta bordes debiles).
    4. Canny con umbrales gruesos (detecta solo los bordes fuertes).
    5. Gradiente morfologico (detecta cambios bruscos de intensidad).
    6. Combinar los tres con OR para quedarnos con todos los bordes.
    7. Un cierre morfologico final para cerrar pequeños huecos en las lineas.
    """
    # Paso 1 y 2: gris y suavizado
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    # Paso 3 y 4: dos pasadas de Canny con distintos umbrales
    edges_fino = cv2.Canny(blur, CANNY_FINO_LOW, CANNY_FINO_HIGH)
    edges_grueso = cv2.Canny(blur, CANNY_GRUESO_LOW, CANNY_GRUESO_HIGH)

    # Paso 5: gradiente morfologico (diferencia entre dilatacion y erosion)
    kernel = np.ones((3, 3), np.uint8)
    grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)
    _, edges_grad = cv2.threshold(grad, 15, 255, cv2.THRESH_BINARY)

    # Paso 6: combinamos los tres resultados
    edges = cv2.bitwise_or(edges_fino, edges_grueso)
    edges = cv2.bitwise_or(edges, edges_grad)

    # Paso 7: cierre morfologico para unir bordes que quedaron cortados
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)

    return edges


def guardar_debug(edges: np.ndarray, path: str = "debug_edges.png") -> None:
    """
    Guarda la imagen de bordes en disco para poder revisarla visualmente.
    Util para comprobar que se han detectado bien los contornos del dibujo.
    """
    cv2.imwrite(path, edges)
    log.info(f"Imagen de bordes guardada: {path}")
