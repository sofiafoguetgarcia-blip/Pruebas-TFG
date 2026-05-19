# -*- coding: utf-8 -*-
"""
drawing_scale.py
================
Calcula el tamaño del dibujo que hará el UR3e en función de las medidas
REALES de cada baldosa, leídas directamente del JSON.

Criterio:
- El dibujo se inscribe sobre el lado menor de la baldosa.
- Se aplica un margen configurable (MARGEN_BALDOSA) para no llegar al borde.
- El resultado se clampa entre MIN_DRAWING_WIDTH_M y MAX_DRAWING_WIDTH_M
  para proteger al robot en casos extremos.

Uso:
    from drawing_scale import calcular_ancho_dibujo_por_baldosa
    ancho_m = calcular_ancho_dibujo_por_baldosa(ancho_mm=140.98, alto_mm=141.96)
"""

import logging
from config import (
    DRAWING_SCALE_ON_TILE,
    MAX_DRAWING_WIDTH_M,
    MIN_DRAWING_WIDTH_M,
)

log = logging.getLogger(__name__)

# Fracción del lado menor que se usa como área de dibujo.
# 0.55 → el dibujo ocupa el 55 % del lado menor de la baldosa.
# Este parámetro ya existe en config.py como DRAWING_SCALE_ON_TILE.
# Se puede sobreescribir aquí si quieres un valor distinto para este módulo.
_ESCALA = DRAWING_SCALE_ON_TILE


def calcular_ancho_dibujo_por_baldosa(
    ancho_mm: float,
    alto_mm: float,
    escala: float | None = None,
) -> float:
    """
    Devuelve el ancho del dibujo en metros, escalado al lado menor de la baldosa.

    Args:
        ancho_mm:  Anchura de la baldosa en milímetros (campo 'ancho_mm' del JSON).
        alto_mm:   Altura de la baldosa en milímetros (campo 'alto_mm' del JSON).
        escala:    Fracción del lado menor que ocupa el dibujo.
                   Si es None, se usa DRAWING_SCALE_ON_TILE de config.py.

    Returns:
        Ancho del dibujo en metros, ya clampado a [MIN_DRAWING_WIDTH_M, MAX_DRAWING_WIDTH_M].
    """
    if escala is None:
        escala = _ESCALA

    lado_menor_mm = min(ancho_mm, alto_mm)
    lado_menor_m = lado_menor_mm / 1000.0

    ancho_raw_m = lado_menor_m * escala
    ancho_final_m = max(MIN_DRAWING_WIDTH_M, min(MAX_DRAWING_WIDTH_M, ancho_raw_m))

    log.info(
        f"Escala dibujo | baldosa: {ancho_mm:.1f}x{alto_mm:.1f} mm "
        f"| lado menor: {lado_menor_mm:.1f} mm "
        f"| escala: {escala:.2f} "
        f"| ancho dibujo calculado: {ancho_raw_m*1000:.1f} mm "
        f"| ancho dibujo final: {ancho_final_m*1000:.1f} mm"
    )

    if ancho_raw_m != ancho_final_m:
        log.warning(
            f"El ancho calculado ({ancho_raw_m*1000:.1f} mm) quedó fuera de los límites "
            f"[{MIN_DRAWING_WIDTH_M*1000:.0f}, {MAX_DRAWING_WIDTH_M*1000:.0f}] mm "
            f"y se ajustó a {ancho_final_m*1000:.1f} mm."
        )

    return ancho_final_m


def resumen_escala(piezas: list[dict]) -> str:
    """
    Genera un resumen legible del tamaño de dibujo que se asignará a cada pieza.
    Útil para revisar en consola antes de enviar nada al robot.

    Args:
        piezas: Lista de dicts con los campos del JSON ('numero', 'ancho_mm', 'alto_mm').

    Returns:
        String multilínea con la tabla de piezas y sus anchos de dibujo.
    """
    lineas = [
        "",
        "=" * 65,
        f"  {'Pieza':>5}  {'Baldosa (mm)':^18}  {'Lado menor':>10}  {'Dibujo (mm)':>11}",
        "-" * 65,
    ]
    for p in piezas:
        num = p.get("numero", "?")
        a = float(p.get("ancho_mm", 0))
        h = float(p.get("alto_mm", 0))
        lado = min(a, h)
        dibujo_m = calcular_ancho_dibujo_por_baldosa(a, h)
        lineas.append(
            f"  {num:>5}  {a:>7.1f} x {h:<7.1f}  {lado:>10.1f}  {dibujo_m*1000:>11.1f}"
        )
    lineas += ["=" * 65, ""]
    return "\n".join(lineas)
