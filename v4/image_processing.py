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
    if not os.path.isfile(path): # Comprueba existe el archivo antes de intentar cargarlo.
        raise FileNotFoundError(f"No existe la imagen: {path}")
    img = cv2.imread(path) # Carga la imagen en formato BGR (OpenCV estándar). No es RGB.
    if img is None:
        raise ValueError(f"OpenCV no pudo leer la imagen: {path}")
    log.info(f"Imagen cargada: {path}  ({img.shape[1]}x{img.shape[0]} px)") # Ancho x Alto en píxeles. 
                                        # img.shape es (alto, ancho, canales).
    return img

'''   Detecta bordes usando Canny con dos umbrales (fino y grueso) y un gradiente morfológico.
    Devuelve una imagen binaria con los bordes detectados.
    El resultado se guarda en debug_edges.png para que puedas ver qué bordes se han detectado.'''
def preprocesar_imagen(img: np.ndarray) -> np.ndarray: 
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) # Convierte a escala de grises. Porq Canny funciona mejor en imágenes monocromáticas.
    blur = cv2.GaussianBlur(gray, (3, 3), 0) # Aplica un desenfoque gaussiano para reducir ruido. El kernel de 3x3 es un buen compromiso entre suavizado y detalle.

    edges_fino   = cv2.Canny(blur, CANNY_FINO_LOW,   CANNY_FINO_HIGH) # Detecta bordes finos con umbrales bajos.
    edges_grueso = cv2.Canny(blur, CANNY_GRUESO_LOW,  CANNY_GRUESO_HIGH) # Detecta bordes gruesos con umbrales altos.

    kernel = np.ones((3, 3), np.uint8) # Kernel para operaciones morfológicas. Un bloque de 3x3 píxeles.
    grad   = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel) # Calcula el gradiente morfológico, que resalta los bordes como la diferencia entre dilatación y erosión. 
    # Útil para detectar bordes que Canny podría perder.
    
    _, edges_grad = cv2.threshold(grad, 15, 255, cv2.THRESH_BINARY) # Convierte el gradiente a una imagen binaria. El umbral de 15 es un valor que resalta los bordes sin incluir demasiado ruido.

    edges = cv2.bitwise_or(edges_fino,  edges_grueso) # Combina los bordes finos y gruesos usando una operación OR bit a bit. Así se conservan ambos tipos de bordes.
    edges = cv2.bitwise_or(edges,       edges_grad) # Combina el resultado anterior con el gradiente morfológico para incluir bordes adicionales que Canny podría haber pasado por alto.
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1) # Aplica una operación de cierre (dilatación seguida de erosión) para cerrar pequeños huecos en los bordes y conectar segmentos cercanos. 
    # Ayuda a formar contornos más continuos.

    log.debug("Preprocesado completado.") 
    return edges

''' Guarda la imagen de bordes detectados en un archivo para depuración. Útil para verificar que los parámetros de Canny y el gradiente están funcionando como esperas.'''
def guardar_debug(edges: np.ndarray, path: str = "debug_edges.png") -> None:
    cv2.imwrite(path, edges)
    log.info(f"Imagen de bordes guardada en: {path}")
