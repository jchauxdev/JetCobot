#!/usr/bin/env python3
# encoding: utf-8
"""Cámara compartida (hilo de captura) y presets de color HSV.

Un solo dispositivo V4L2 (/dev/video0) no se puede abrir dos veces a la
vez, así que todas las pestañas de la app que necesitan video comparten
una única instancia de CameraStream en vez de abrir la cámara cada una
por su cuenta.
"""

import threading
import time

import cv2

DEFAULT_CAMERA = "/dev/video0"
FRAME_WIDTH, FRAME_HEIGHT = 640, 480

# Rangos HSV de referencia (OpenCV: H 0-179, S/V 0-255). El rojo se define
# con dos bandas porque el tono envuelve el 0/179. Negro y metálico dependen
# mucho de la iluminación real: úsalos como punto de partida y ajusta con
# "Mostrar máscara" hasta que solo quede la pieza.
COLOR_PRESETS = {
    "Rojo": [((0, 120, 70), (10, 255, 255)), ((170, 120, 70), (180, 255, 255))],
    "Negro": [((0, 0, 0), (180, 255, 55))],
    "Metálico": [((0, 0, 100), (180, 60, 230))],
    "Verde": [((36, 60, 60), (89, 255, 255))],
    "Azul": [((94, 80, 40), (126, 255, 255))],
    "Amarillo": [((20, 100, 100), (35, 255, 255))],
}


class CameraStream:
    """Lee frames de la cámara en un hilo aparte para no bloquear la GUI."""

    def __init__(self, device=DEFAULT_CAMERA):
        self.device = device
        self.cap = None
        self.lock = threading.Lock()
        self.latest_frame = None
        self._running = False
        self._thread = None

    @property
    def running(self):
        return self._running

    def start(self, device=None):
        if self._running:
            return
        if device:
            self.device = device
        self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            raise RuntimeError(f"No se pudo abrir {self.device}")
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            ok, frame = self.cap.read()
            if ok:
                with self.lock:
                    self.latest_frame = frame
            else:
                time.sleep(0.05)

    def get_frame(self):
        with self.lock:
            return None if self.latest_frame is None else self.latest_frame.copy()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        with self.lock:
            self.latest_frame = None
