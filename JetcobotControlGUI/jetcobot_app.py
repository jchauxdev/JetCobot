#!/usr/bin/env python3
# encoding: utf-8
"""
Aplicación JetCobot organizada por pestañas.

  - "Control y Movimiento": todo lo de jetcobot_gui_posiciones.py
    (conexión, motores, articulaciones, gripper, posiciones guardadas).
  - "Detección de Color": abre la cámara del robot (/dev/video0 por
    defecto) y detecta un color (por preset o por rango HSV manual),
    mostrando el video en vivo con el resultado superpuesto.

Uso:
    python3 jetcobot_app.py

Requiere:
    pip install pymycobot opencv-python pillow
"""

import threading
import time
import tkinter as tk
from tkinter import ttk

import cv2
from PIL import Image, ImageTk

from jetcobot_gui_posiciones import PosicionesPanel

DEFAULT_CAMERA = "/dev/video0"
FRAME_WIDTH, FRAME_HEIGHT = 640, 480

# Rangos HSV de referencia (OpenCV: H 0-179, S/V 0-255). El rojo se define
# con dos bandas porque el tono envuelve el 0/179.
COLOR_PRESETS = {
    "Rojo": [((0, 120, 70), (10, 255, 255)), ((170, 120, 70), (180, 255, 255))],
    "Verde": [((36, 60, 60), (89, 255, 255))],
    "Azul": [((94, 80, 40), (126, 255, 255))],
    "Amarillo": [((20, 100, 100), (35, 255, 255))],
}


class CameraStream:
    """Lee frames de la cámara en un hilo aparte para no bloquear la GUI."""

    def __init__(self, device):
        self.device = device
        self.cap = None
        self.lock = threading.Lock()
        self.latest_frame = None
        self._running = False
        self._thread = None

    def start(self):
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


class ColorDetectionPanel(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.stream = None
        self.active_ranges = None
        self.active_color_name = tk.StringVar(value="Ninguno")

        self.detect_var = tk.BooleanVar(value=True)
        self.show_mask_var = tk.BooleanVar(value=False)
        self.min_area_var = tk.IntVar(value=800)

        self.h_min, self.h_max = tk.IntVar(value=0), tk.IntVar(value=179)
        self.s_min, self.s_max = tk.IntVar(value=100), tk.IntVar(value=255)
        self.v_min, self.v_max = tk.IntVar(value=100), tk.IntVar(value=255)

        self.status_var = tk.StringVar(value="Cámara detenida.")
        self.detection_var = tk.StringVar(value="Sin detección")

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}

        video_frame = ttk.LabelFrame(self, text="Cámara")
        video_frame.grid(row=0, column=0, sticky="nsew", **pad)
        self.video_label = tk.Label(
            video_frame, text="Cámara apagada",
            background="black", foreground="white",
        )
        self.video_label.pack(padx=4, pady=4)

        controls = ttk.Frame(self)
        controls.grid(row=0, column=1, sticky="n", **pad)

        cam_frame = ttk.LabelFrame(controls, text="Conexión de cámara")
        cam_frame.pack(fill="x", **pad)
        ttk.Label(cam_frame, text="Dispositivo:").grid(row=0, column=0, **pad)
        self.device_entry = ttk.Entry(cam_frame, width=14)
        self.device_entry.insert(0, DEFAULT_CAMERA)
        self.device_entry.grid(row=0, column=1, **pad)
        self.start_btn = ttk.Button(cam_frame, text="Iniciar", command=self._on_start_camera)
        self.start_btn.grid(row=0, column=2, **pad)
        self.stop_btn = ttk.Button(cam_frame, text="Detener", command=self._on_stop_camera, state="disabled")
        self.stop_btn.grid(row=0, column=3, **pad)
        ttk.Label(cam_frame, textvariable=self.status_var).grid(row=1, column=0, columnspan=4, sticky="w", **pad)

        preset_frame = ttk.LabelFrame(controls, text="Color a detectar (preset)")
        preset_frame.pack(fill="x", **pad)
        for i, name in enumerate(COLOR_PRESETS):
            ttk.Button(preset_frame, text=name, command=lambda n=name: self._on_preset(n)).grid(row=0, column=i, **pad)
        ttk.Label(preset_frame, text="Activo:").grid(row=1, column=0, **pad)
        ttk.Label(preset_frame, textvariable=self.active_color_name).grid(row=1, column=1, columnspan=3, sticky="w", **pad)

        manual_frame = ttk.LabelFrame(controls, text="Rango HSV manual")
        manual_frame.pack(fill="x", **pad)
        self._add_hsv_row(manual_frame, "H", self.h_min, self.h_max, 179, 0)
        self._add_hsv_row(manual_frame, "S", self.s_min, self.s_max, 255, 1)
        self._add_hsv_row(manual_frame, "V", self.v_min, self.v_max, 255, 2)
        ttk.Button(manual_frame, text="Aplicar rango manual", command=self._on_apply_manual).grid(
            row=3, column=0, columnspan=6, **pad
        )

        opts_frame = ttk.LabelFrame(controls, text="Opciones de detección")
        opts_frame.pack(fill="x", **pad)
        ttk.Checkbutton(opts_frame, text="Detectar color", variable=self.detect_var).grid(row=0, column=0, **pad)
        ttk.Checkbutton(opts_frame, text="Mostrar máscara", variable=self.show_mask_var).grid(row=0, column=1, **pad)
        ttk.Label(opts_frame, text="Área mínima (px²)").grid(row=1, column=0, **pad)
        ttk.Scale(opts_frame, from_=100, to=5000, variable=self.min_area_var, orient="horizontal", length=140).grid(
            row=1, column=1, **pad
        )

        info_frame = ttk.LabelFrame(controls, text="Resultado")
        info_frame.pack(fill="x", **pad)
        ttk.Label(info_frame, textvariable=self.detection_var, width=34).pack(**pad)

    def _add_hsv_row(self, parent, label, var_min, var_max, max_value, row):
        pad = {"padx": 4, "pady": 2}
        ttk.Label(parent, text=f"{label} min").grid(row=row, column=0, **pad)
        ttk.Scale(parent, from_=0, to=max_value, variable=var_min, orient="horizontal", length=110).grid(row=row, column=1, **pad)
        ttk.Label(parent, textvariable=var_min, width=4).grid(row=row, column=2, **pad)
        ttk.Label(parent, text=f"{label} max").grid(row=row, column=3, **pad)
        ttk.Scale(parent, from_=0, to=max_value, variable=var_max, orient="horizontal", length=110).grid(row=row, column=4, **pad)
        ttk.Label(parent, textvariable=var_max, width=4).grid(row=row, column=5, **pad)

    # ------------------------------------------------------------------
    def _on_preset(self, name):
        self.active_ranges = COLOR_PRESETS[name]
        self.active_color_name.set(name)

    def _on_apply_manual(self):
        self.active_ranges = [(
            (self.h_min.get(), self.s_min.get(), self.v_min.get()),
            (self.h_max.get(), self.s_max.get(), self.v_max.get()),
        )]
        self.active_color_name.set("Manual")

    def _on_start_camera(self):
        device = self.device_entry.get().strip()
        try:
            stream = CameraStream(device)
            stream.start()
        except Exception as exc:
            self.status_var.set(f"Error: {exc}")
            return
        self.stream = stream
        self.status_var.set(f"Cámara activa: {device}")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._update_frame()

    def _on_stop_camera(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream = None
        self.video_label.configure(image="", text="Cámara apagada")
        self.status_var.set("Cámara detenida.")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    # ------------------------------------------------------------------
    def _update_frame(self):
        if self.stream is None:
            return
        frame = self.stream.get_frame()
        if frame is not None:
            if self.detect_var.get() and self.active_ranges:
                display, info = self._detect_color(frame)
                self.detection_var.set(info)
            else:
                display = frame
                self.detection_var.set("Detección desactivada")
            self._render(display)
        self.after(30, self._update_frame)

    def _detect_color(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = None
        for lo, hi in self.active_ranges:
            band = cv2.inRange(hsv, lo, hi)
            mask = band if mask is None else cv2.bitwise_or(mask, band)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        display = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR) if self.show_mask_var.get() else frame.copy()

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        info = "Sin detección"
        if contours:
            c = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(c)
            if area >= self.min_area_var.get():
                x, y, w, h = cv2.boundingRect(c)
                cx, cy = x + w // 2, y + h // 2
                cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(display, (cx, cy), 5, (0, 0, 255), -1)
                info = f"Centro: ({cx}, {cy})   Área: {int(area)} px²"
        return display, info

    def _render(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        photo = ImageTk.PhotoImage(image=Image.fromarray(rgb))
        self.video_label.configure(image=photo, text="")
        self.video_label.image = photo  # evita que el garbage collector la borre

    # ------------------------------------------------------------------
    def shutdown(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream = None


class JetcobotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JetCobot - Panel de control")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.control_panel = PosicionesPanel(notebook)
        self.color_panel = ColorDetectionPanel(notebook)

        notebook.add(self.control_panel, text="Control y Movimiento")
        notebook.add(self.color_panel, text="Detección de Color")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self.control_panel.shutdown()
        self.color_panel.shutdown()
        self.destroy()


if __name__ == "__main__":
    app = JetcobotApp()
    app.mainloop()
