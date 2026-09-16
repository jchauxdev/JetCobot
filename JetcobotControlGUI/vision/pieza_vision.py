#!/usr/bin/env python3
# encoding: utf-8
"""
Funciones de visión reutilizables: segmentar por color, encontrar la pieza
principal y detectar si tiene un hueco visible (posición correcta), y la
geometría de cámara estenopeica para pasar de píxeles a milímetros reales.
"""

import cv2
import numpy as np


def construir_mascara(frame_bgr, rangos_hsv):
    """Aplica uno o más rangos HSV (para colores que envuelven el tono) y limpia ruido."""
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask = None
    for lo, hi in rangos_hsv:
        banda = cv2.inRange(hsv, lo, hi)
        mask = banda if mask is None else cv2.bitwise_or(mask, banda)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)
    return mask


def analizar_mascara(mask, min_area=500, min_hole_ratio=0.03):
    """Encuentra el contorno externo más grande de la máscara y busca un hueco dentro.

    Devuelve None si no hay ningún contorno que supere min_area. Si lo hay,
    devuelve un dict con el contorno, su área y diámetro aproximado (círculo
    envolvente), su centro en píxeles, y si tiene o no un hueco (hijo en la
    jerarquía de contornos) de al menos min_hole_ratio de su propia área.
    """
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if not contours or hierarchy is None:
        return None
    hierarchy = hierarchy[0]

    externos = [(i, c) for i, c in enumerate(contours) if hierarchy[i][3] == -1]
    if not externos:
        return None
    idx, outer = max(externos, key=lambda t: cv2.contourArea(t[1]))
    area = cv2.contourArea(outer)
    if area < min_area:
        return None

    (cx, cy), radius = cv2.minEnclosingCircle(outer)

    hueco = False
    hueco_contorno = None
    child_idx = hierarchy[idx][2]
    while child_idx != -1:
        child = contours[child_idx]
        if cv2.contourArea(child) >= area * min_hole_ratio:
            hueco = True
            hueco_contorno = child
            break
        child_idx = hierarchy[child_idx][0]

    return {
        "contorno": outer,
        "area": area,
        "centro_px": (int(cx), int(cy)),
        "diametro_px": radius * 2,
        "hueco": hueco,
        "hueco_contorno": hueco_contorno,
    }


def distancia_mm(diametro_real_mm, diametro_px, focal_px):
    """Distancia cámara-objeto por tamaño aparente (modelo de cámara estenopeica)."""
    if not diametro_px or diametro_px <= 0 or not focal_px:
        return None
    return (diametro_real_mm * focal_px) / diametro_px


def offset_xy_mm(cx_px, cy_px, frame_w, frame_h, distancia_objeto_mm, focal_px):
    """Desplazamiento lateral real (mm) del centro detectado respecto al centro de la imagen."""
    if not distancia_objeto_mm or not focal_px:
        return None, None
    dx_px = cx_px - frame_w / 2
    dy_px = cy_px - frame_h / 2
    dx_mm = dx_px * distancia_objeto_mm / focal_px
    dy_mm = dy_px * distancia_objeto_mm / focal_px
    return dx_mm, dy_mm


def ajustar_focal_por_regresion(muestras, diametro_real_mm):
    """Ajusta la focal (px) a partir de muestras (delta_z_mm, diametro_px) tomadas
    moviendo la cámara a varias alturas conocidas sobre la misma pieza.

    Usa que 1/diametro_px es lineal en delta_z (modelo de cámara estenopeica),
    así que la pendiente del ajuste lineal da la focal directamente sin
    necesitar la distancia absoluta a la pieza. Devuelve None si hay muy
    pocas muestras o el ajuste no es válido.
    """
    if len(muestras) < 3:
        return None
    deltas = np.array([m[0] for m in muestras], dtype=float)
    inv_px = np.array([1.0 / m[1] for m in muestras if m[1] > 0], dtype=float)
    if len(inv_px) < 3:
        return None
    pendiente, _intercepto = np.polyfit(deltas, inv_px, 1)
    if pendiente <= 0:
        return None
    return 1.0 / (diametro_real_mm * pendiente)


def ajustar_circulo(puntos):
    """Ajuste algebraico de círculo (método de Kasa) a una lista de puntos (x,y).

    Se usa para hallar por dónde "pasa" el eje de giro de la muñeca en la
    imagen: si la cámara gira rígidamente con la muñeca, un punto fijo del
    mundo traza un círculo en la imagen cuyo centro es la proyección de ese
    eje. Devuelve (cx, cy, radio) o None si hay muy pocos puntos.
    """
    if len(puntos) < 3:
        return None
    xs = np.array([p[0] for p in puntos], dtype=float)
    ys = np.array([p[1] for p in puntos], dtype=float)
    A = np.column_stack([xs, ys, np.ones(len(xs))])
    b = xs**2 + ys**2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    radio_cuadrado = sol[2] + cx**2 + cy**2
    if radio_cuadrado <= 0:
        return None
    return cx, cy, radio_cuadrado**0.5
