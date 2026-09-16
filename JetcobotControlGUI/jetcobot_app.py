#!/usr/bin/env python3
# encoding: utf-8
"""
Aplicación JetCobot organizada por pestañas.

  - "Control y Movimiento": todo lo de jetcobot_gui_posiciones.py
    (conexión, motores, articulaciones, gripper, posiciones guardadas).
  - "Detección de Color": detecta un color en la cámara (por preset o por
    rango HSV manual), mostrando el video en vivo con el resultado
    superpuesto.
  - "Calibración": perfiles de pieza (color + diámetro real + si debe tener
    hueco visible) y calibración de cámara (offset físico cámara→gripper y
    distancia focal), para calcular en vivo la distancia real a una pieza
    y cuánto le falta bajar al gripper para alcanzarla.

La cámara (/dev/video0 por defecto) se controla en una sola barra
compartida arriba de las pestañas, porque un dispositivo V4L2 no se puede
abrir dos veces a la vez.

Carpetas:
    panels/  paneles de la interfaz (control, posiciones, calibración)
    vision/  cámara compartida y funciones de visión por color/forma
    data/    perfiles, posiciones y calibraciones guardadas (JSON)

Uso:
    python3 jetcobot_app.py

Requiere:
    pip install pymycobot opencv-python pillow
"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import cv2
from PIL import Image, ImageTk

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "panels"))
sys.path.insert(0, str(_ROOT / "vision"))

from calibracion_panel import CalibracionPanel
from camera_stream import COLOR_PRESETS, DEFAULT_CAMERA, CameraStream
from jetcobot_gui_posiciones import PosicionesPanel


class ColorDetectionPanel(ttk.Frame):
    def __init__(self, master, camera, **kwargs):
        super().__init__(master, **kwargs)
        self.camera = camera
        self.active_ranges = None
        self.active_color_name = tk.StringVar(value="Ninguno")

        self.detect_var = tk.BooleanVar(value=True)
        self.show_mask_var = tk.BooleanVar(value=False)
        self.min_area_var = tk.IntVar(value=800)

        self.h_min, self.h_max = tk.IntVar(value=0), tk.IntVar(value=179)
        self.s_min, self.s_max = tk.IntVar(value=100), tk.IntVar(value=255)
        self.v_min, self.v_max = tk.IntVar(value=100), tk.IntVar(value=255)

        self.detection_var = tk.StringVar(value="Sin detección")

        self._build_ui()
        self._update_frame()

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

        preset_frame = ttk.LabelFrame(controls, text="Color a detectar (preset)")
        preset_frame.pack(fill="x", **pad)
        for i, name in enumerate(COLOR_PRESETS):
            ttk.Button(preset_frame, text=name, command=lambda n=name: self._on_preset(n)).grid(
                row=i // 3, column=i % 3, **pad
            )
        ttk.Label(preset_frame, text="Activo:").grid(row=2, column=0, **pad)
        ttk.Label(preset_frame, textvariable=self.active_color_name).grid(row=2, column=1, columnspan=2, sticky="w", **pad)

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

    # ------------------------------------------------------------------
    def _update_frame(self):
        frame = self.camera.get_frame() if self.camera.running else None
        if frame is not None:
            if self.detect_var.get() and self.active_ranges:
                display, info = self._detect_color(frame)
                self.detection_var.set(info)
            else:
                display = frame
                self.detection_var.set("Detección desactivada")
            self._render(display)
        else:
            self.video_label.configure(image="", text="Cámara apagada")
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
        pass


class JetcobotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JetCobot - Panel de control")
        self.geometry("1250x850")

        self.camera = CameraStream()
        self._build_camera_bar()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.control_panel = PosicionesPanel(notebook)
        self.color_panel = ColorDetectionPanel(notebook, self.camera)
        self.calib_panel = CalibracionPanel(notebook, self.camera, self.control_panel.robot)

        notebook.add(self.control_panel, text="Control y Movimiento")
        notebook.add(self.color_panel, text="Detección de Color")
        notebook.add(self.calib_panel, text="Calibración")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_camera_bar(self):
        pad = {"padx": 6, "pady": 4}
        bar = ttk.LabelFrame(self, text="Cámara (compartida entre pestañas)")
        bar.pack(fill="x", **pad)

        ttk.Label(bar, text="Dispositivo:").grid(row=0, column=0, **pad)
        self.device_entry = ttk.Entry(bar, width=14)
        self.device_entry.insert(0, DEFAULT_CAMERA)
        self.device_entry.grid(row=0, column=1, **pad)

        self.start_btn = ttk.Button(bar, text="Iniciar cámara", command=self._on_start_camera)
        self.start_btn.grid(row=0, column=2, **pad)
        self.stop_btn = ttk.Button(bar, text="Detener cámara", command=self._on_stop_camera, state="disabled")
        self.stop_btn.grid(row=0, column=3, **pad)

        self.camera_status_var = tk.StringVar(value="Cámara detenida.")
        ttk.Label(bar, textvariable=self.camera_status_var).grid(row=0, column=4, **pad)

    def _on_start_camera(self):
        device = self.device_entry.get().strip()
        try:
            self.camera.start(device)
        except Exception as exc:
            self.camera_status_var.set(f"Error: {exc}")
            return
        self.camera_status_var.set(f"Cámara activa: {device}")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

    def _on_stop_camera(self):
        self.camera.stop()
        self.camera_status_var.set("Cámara detenida.")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _on_close(self):
        self.control_panel.shutdown()
        self.color_panel.shutdown()
        self.calib_panel.shutdown()
        self.camera.stop()
        self.destroy()


if __name__ == "__main__":
    app = JetcobotApp()
    app.mainloop()
