# -*- coding: utf-8 -*-
"""
trajectory.py
=============
Este archivo convierte los bordes de una imagen en trayectorias 2D.

Entrada:
- una imagen binaria de bordes, generada en image_processing.py.

Salida:
- una lista de trayectorias.
- cada trayectoria es una lista de puntos (x, y) en metros.

Después, distributor.py reparte estas trayectorias entre UR3e y UR5e.
"""

import cv2                                                                          # Se usa para buscar contornos y simplificar curvas. 
import logging
import numpy as np                                                                  # Se usa para manejar arrays de puntos y formas de imagen. 
                                                                                      # Las imágenes de OpenCV son arrays de NumPy.
from typing import List, Tuple

from config_solucion import (
    MAX_ANCHO_M,          # Ancho máximo real del dibujo en metros.
    EPSILON_PX,           # Nivel de simplificación del contorno en píxeles.
    DECIMATE_STEP,        # Cada cuántos puntos se conserva uno.
    MIN_PUNTOS_CONTORNO,  # Mínimo de puntos para aceptar un trazo.
    MIN_LONGITUD_PX,      # Longitud mínima del contorno en píxeles.
    MAX_PUNTOS_TOTAL,     # Máximo total de puntos permitidos.
)

log = logging.getLogger(__name__)

Punto       = Tuple[float, float]                                                   # Un punto es una pareja (x, y) en metros.
Trayectoria = List[Punto]                                                           # Una trayectoria es una lista de puntos.


def extraer_trayectorias(
    edges: np.ndarray,
    img_shape: Tuple[int, int],
) -> List[Trayectoria]:
    """
    Convierte un mapa de bordes en trayectorias métricas centradas en (0,0).

    edges:
        imagen binaria con los bordes detectados.

    img_shape:
        tamaño de la imagen original.

    Devuelve:
        lista de trayectorias en metros.
    """
    img_h, img_w = img_shape[:2]                                                   # Extrae alto y ancho de la imagen.
                                                                                      # img_shape normalmente es:
                                                                                      # (alto, ancho, canales)
                                                                                      
    escala = MAX_ANCHO_M / float(img_w)                                            # Calcula la escala para convertir píxeles a metros.

    # Busca contornos en la imagen de bordes.
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)    # cv2.RETR_TREE:
                                                                                      # detecta contornos externos e internos.
                                                                                   # cv2.CHAIN_APPROX_NONE:
                                                                                      # conserva todos los puntos del contorno.
   
    if not contours:
        raise ValueError("No se detectaron contornos en la imagen.")

    log.info(f"Contornos crudos: {len(contours)}")
    
    contours = sorted(contours, key=lambda c: cv2.arcLength(c, False), reverse=True) # Ordena los contornos de mayor a menor longitud.
                                                                                        # Así se procesan primero los trazos principales
                                                                                        # y después los detalles pequeños.

    trayectorias: List[Trayectoria] = []                                             # Lista para guardar las trayectorias finales.               
    
    total_puntos = 0                                                                 # Contador total de puntos aceptados.
    
    descartados  = 0                                                                 # Contador de contornos descartados.

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)                                             # Calcula el rectángulo que encierra el contorno.
                                                                                        # x, y: esquina superior izquierda.
                                                                                        # w: ancho de la caja.
                                                                                        # h: alto de la caja.
                                                                                        
        if w >= img_w * 0.98 or h >= img_h * 0.98:                                   # Descarta contornos que ocupan casi toda la imagen.
                                                                                        # Esto suele ser el borde exterior de la imagen,
                                                                                        # no una línea real del dibujo.
            descartados += 1
            continue
        
        if cv2.arcLength(c, False) < MIN_LONGITUD_PX:                                # Descarta contornos muy cortos.              
            descartados += 1
            continue

        approx = cv2.approxPolyDP(c, EPSILON_PX, closed=False)                       # Simplifica el contorno.
                                                                                        # EPSILON_PX controla cuánto se simplifica:
                                                                                            # - valor bajo: más puntos, más detalle.
                                                                                            # - valor alto: menos puntos, menos detalle.
        
        pts    = approx.reshape(-1, 2)                                               # Convierte la estructura de OpenCV a una lista simple de puntos.
                                                                                        # OpenCV devuelve algo tipo:
                                                                                        # [[[x, y]], [[x, y]], ...]
                                                                                        # reshape(-1, 2) lo convierte en:
                                                                                        # [[x, y], [x, y], ...]
                                                                                        
        
        if DECIMATE_STEP > 1:   
             pts = pts[::DECIMATE_STEP]                                              # Ejemplo:
                                                                                        # DECIMATE_STEP = 3
                                                                                        # conserva punto 0, 3, 6, 9...
                                                                                        #
                                                                                        # Esto reduce mucho la cantidad de movimientos del robot.
           
            
        if len(pts) < MIN_PUNTOS_CONTORNO:                                          # Si después de simplificar quedan pocos puntos,
                                                                                        # el contorno no sirve como trayectoria.                                         
            descartados += 1
            continue
        
        
                                                                                     # Convierte los puntos de píxeles a metros.
                                                                                        # En imagen:
                                                                                        # - el origen está arriba a la izquierda.
                                                                                        # - Y crece hacia abajo.
                                                                                        #
                                                                                        # En el papel:
                                                                                        # - se usa el centro como origen (0,0).
                                                                                        # - Y se invierte para que crezca hacia arriba.
        trayectoria = [
            ((px - img_w / 2.0) * escala, -(py - img_h / 2.0) * escala)
            for px, py in pts
        ]
        trayectorias.append(trayectoria)
        total_puntos += len(trayectoria)

        if total_puntos >= MAX_PUNTOS_TOTAL:                                          # Si se supera el máximo de puntos permitido,
                                                                                         # se corta el procesamiento.
                                                                                         #
                                                                                         # Esto evita generar scripts enormes y movimientos excesivos.
            log.warning(f"Límite {MAX_PUNTOS_TOTAL} puntos alcanzado.")
            break

    if not trayectorias:
        raise ValueError("No hay trayectorias válidas tras el filtrado.")

    log.info(
        f"Trayectorias: {len(trayectorias)} válidas | "
        f"{total_puntos} puntos | {descartados} descartados"
    )
    return trayectorias
