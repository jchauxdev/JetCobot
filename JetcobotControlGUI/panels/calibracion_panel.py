#!/usr/bin/env python3
# encoding: utf-8
"""
Pestaña de Calibración: perfiles de pieza (color + diámetro real + si debe
tener hueco visible) y calibración de cámara (offset físico cámara→gripper
y distancia focal en píxeles), para poder calcular en tiempo real la
distancia real a una pieza y cuánto le falta bajar al gripper para
alcanzarla, sin importar si la altura de la pieza varía.

Los datos se guardan en data/perfiles_piezas.json y
data/calibracion_camara.json (relativo a la raíz de JetcobotControlGUI).
"""

import json
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vision"))

from jetcobot_gui import ScrollableFrame
from camera_stream import COLOR_PRESETS, FRAME_HEIGHT, FRAME_WIDTH
from pieza_vision import (
    ajustar_circulo,
    ajustar_focal_por_regresion,
    analizar_mascara,
    construir_mascara,
    distancia_mm,
    offset_xy_mm,
)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PERFILES_FILE = _DATA_DIR / "perfiles_piezas.json"
CALIBRACION_FILE = _DATA_DIR / "calibracion_camara.json"

DEFAULT_CALIBRACION = {"focal_px": None, "offset_mm": {"dx": 0.0, "dy": 0.0, "dz": 36.0}}


def load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class CalibracionPanel(ttk.Frame):
    def __init__(self, master, camera, robot, **kwargs):
        super().__init__(master, **kwargs)
        self.camera = camera
        self.robot = robot
        self.msg_queue = queue.Queue()

        self._dz_medicion = None
        self._dz_touch_z = None
        self.calib_speed_var = tk.IntVar(value=30)

        self.perfiles = load_json(PERFILES_FILE, {})
        self.calibracion = load_json(CALIBRACION_FILE, DEFAULT_CALIBRACION)
        self._current_hsv_bands = COLOR_PRESETS["Rojo"]
        self._selected_profile = None

        self.h_min, self.h_max = tk.IntVar(value=0), tk.IntVar(value=179)
        self.s_min, self.s_max = tk.IntVar(value=100), tk.IntVar(value=255)
        self.v_min, self.v_max = tk.IntVar(value=100), tk.IntVar(value=255)

        self.diametro_var = tk.StringVar(value="30")
        self.requiere_hueco_var = tk.BooleanVar(value=True)
        self.min_area_var = tk.IntVar(value=500)
        self.bandas_activas_var = tk.StringVar(value="Rojo (preset)")

        self.dx_var = tk.StringVar(value=str(self.calibracion["offset_mm"]["dx"]))
        self.dy_var = tk.StringVar(value=str(self.calibracion["offset_mm"]["dy"]))
        self.dz_var = tk.StringVar(value=str(self.calibracion["offset_mm"]["dz"]))

        self.distancia_real_var = tk.StringVar(value="200")
        self.focal_label_var = tk.StringVar(value=self._focal_text())

        self.detectar_var = tk.BooleanVar(value=True)
        self.resultado_var = tk.StringVar(value="Selecciona un perfil guardado para probar.")

        self._scroll = ScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True)
        self.content = self._scroll.interior

        self._build_ui()
        self._refresh_profile_list()
        self._update_frame()
        self.after(100, self._process_queue)

    def _focal_text(self):
        focal = self.calibracion.get("focal_px")
        return f"{focal:.1f} px" if focal else "Sin calibrar"

    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}

        video_frame = ttk.LabelFrame(self.content, text="Cámara")
        video_frame.grid(row=0, column=0, rowspan=4, sticky="nsew", **pad)
        self.video_label = tk.Label(video_frame, text="Cámara apagada", background="black", foreground="white")
        self.video_label.pack(padx=4, pady=4)

        result_frame = ttk.LabelFrame(video_frame, text="Resultado de la prueba")
        result_frame.pack(fill="x", padx=4, pady=4)
        ttk.Checkbutton(result_frame, text="Detectar en vivo (perfil seleccionado)", variable=self.detectar_var).pack(
            anchor="w", **pad
        )
        ttk.Label(result_frame, textvariable=self.resultado_var, width=48, wraplength=380).pack(**pad)

        offset_frame = ttk.LabelFrame(self.content, text="Offset físico cámara → gripper (mm, medido con calibre)")
        offset_frame.grid(row=0, column=1, sticky="ew", **pad)
        ttk.Label(offset_frame, text="dx").grid(row=0, column=0, **pad)
        ttk.Entry(offset_frame, textvariable=self.dx_var, width=8).grid(row=0, column=1, **pad)
        ttk.Label(offset_frame, text="dy").grid(row=0, column=2, **pad)
        ttk.Entry(offset_frame, textvariable=self.dy_var, width=8).grid(row=0, column=3, **pad)
        ttk.Label(offset_frame, text="dz (profundidad)").grid(row=0, column=4, **pad)
        ttk.Entry(offset_frame, textvariable=self.dz_var, width=8).grid(row=0, column=5, **pad)
        ttk.Button(offset_frame, text="Guardar offset", command=self._on_guardar_offset).grid(row=0, column=6, **pad)

        focal_frame = ttk.LabelFrame(self.content, text="Distancia focal (usa el perfil seleccionado en la lista de abajo)")
        focal_frame.grid(row=1, column=1, sticky="ew", **pad)
        ttk.Label(focal_frame, text="Distancia real medida cámara-pieza (mm):").grid(row=0, column=0, **pad)
        ttk.Entry(focal_frame, textvariable=self.distancia_real_var, width=8).grid(row=0, column=1, **pad)
        ttk.Button(focal_frame, text="Capturar y calcular focal (manual)", command=self._on_capturar_focal).grid(
            row=0, column=2, **pad
        )
        ttk.Label(focal_frame, text="Focal actual:").grid(row=1, column=0, **pad)
        ttk.Label(focal_frame, textvariable=self.focal_label_var).grid(row=1, column=1, columnspan=2, sticky="w", **pad)

        auto_frame = ttk.LabelFrame(
            self.content, text="Calibración guiada automática (mueve el brazo — usa el perfil seleccionado abajo)"
        )
        auto_frame.grid(row=2, column=1, sticky="ew", **pad)

        ttk.Label(auto_frame, text="Velocidad calibración:").grid(row=0, column=0, **pad)
        ttk.Scale(auto_frame, from_=10, to=60, variable=self.calib_speed_var, orient="horizontal", length=100).grid(
            row=0, column=1, **pad
        )
        ttk.Label(auto_frame, textvariable=self.calib_speed_var, width=3).grid(row=0, column=2, **pad)

        ttk.Button(
            auto_frame, text="1. Auto-calibrar foco (sube/baja solo)", command=self._on_auto_focal
        ).grid(row=1, column=0, columnspan=3, sticky="ew", **pad)

        ttk.Label(
            auto_frame,
            text="2. Offset dz: coloca la pieza en la pose de observación y mide, luego baja\n"
                 "el gripper (pestaña Control) hasta tocarla y registra el toque.",
            justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        ttk.Button(auto_frame, text="2a. Medir aquí", command=self._on_medir_aqui).grid(row=3, column=0, **pad)
        ttk.Button(auto_frame, text="2b. Aquí toca la pieza", command=self._on_toca_pieza).grid(row=3, column=1, **pad)
        ttk.Button(auto_frame, text="2c. Calcular dz", command=self._on_calcular_dz).grid(row=3, column=2, **pad)

        ttk.Button(
            auto_frame, text="3. Auto-calibrar offset lateral (gira la muñeca solo)", command=self._on_auto_lateral
        ).grid(row=4, column=0, columnspan=3, sticky="ew", **pad)

        self.calib_log = tk.Text(auto_frame, height=6, width=48, state="disabled")
        self.calib_log.grid(row=5, column=0, columnspan=3, sticky="ew", **pad)

        profile_frame = ttk.LabelFrame(self.content, text="Perfiles de pieza")
        profile_frame.grid(row=3, column=1, sticky="nsew", **pad)

        list_col = ttk.Frame(profile_frame)
        list_col.grid(row=0, column=0, rowspan=8, sticky="ns", **pad)
        self.profiles_listbox = tk.Listbox(list_col, height=10, width=20, exportselection=False)
        self.profiles_listbox.pack()
        self.profiles_listbox.bind("<<ListboxSelect>>", self._on_select_profile)
        ttk.Button(list_col, text="Eliminar perfil", command=self._on_eliminar_perfil).pack(fill="x", pady=(4, 0))

        form_col = ttk.Frame(profile_frame)
        form_col.grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(form_col, text="Nombre:").grid(row=0, column=0, **pad)
        self.name_entry = ttk.Entry(form_col, width=18)
        self.name_entry.grid(row=0, column=1, columnspan=3, **pad)

        preset_row = ttk.Frame(form_col)
        preset_row.grid(row=1, column=0, columnspan=4, sticky="w", **pad)
        ttk.Label(preset_row, text="Color:").pack(side="left", padx=(0, 4))
        for name in COLOR_PRESETS:
            ttk.Button(preset_row, text=name, command=lambda n=name: self._on_preset(n)).pack(side="left", padx=2)

        self._add_hsv_row(form_col, "H", self.h_min, self.h_max, 179, 2)
        self._add_hsv_row(form_col, "S", self.s_min, self.s_max, 255, 3)
        self._add_hsv_row(form_col, "V", self.v_min, self.v_max, 255, 4)
        ttk.Button(form_col, text="Usar rango manual (sliders)", command=self._on_usar_manual).grid(
            row=5, column=0, columnspan=4, **pad
        )
        ttk.Label(form_col, textvariable=self.bandas_activas_var).grid(row=6, column=0, columnspan=4, sticky="w", **pad)

        ttk.Label(form_col, text="Diámetro real (mm):").grid(row=7, column=0, **pad)
        ttk.Entry(form_col, textvariable=self.diametro_var, width=8).grid(row=7, column=1, **pad)
        ttk.Checkbutton(form_col, text="Requiere hueco visible (posición correcta)", variable=self.requiere_hueco_var).grid(
            row=7, column=2, columnspan=2, **pad
        )

        ttk.Label(form_col, text="Área mínima (px²):").grid(row=8, column=0, **pad)
        ttk.Scale(form_col, from_=100, to=5000, variable=self.min_area_var, orient="horizontal", length=140).grid(
            row=8, column=1, columnspan=2, **pad
        )
        ttk.Button(form_col, text="Guardar perfil", command=self._on_guardar_perfil).grid(row=8, column=3, **pad)

    def _add_hsv_row(self, parent, label, var_min, var_max, max_value, row):
        pad = {"padx": 4, "pady": 2}
        ttk.Label(parent, text=f"{label} min").grid(row=row, column=0, **pad)
        ttk.Scale(parent, from_=0, to=max_value, variable=var_min, orient="horizontal", length=90).grid(row=row, column=1, **pad)
        ttk.Label(parent, text=f"{label} max").grid(row=row, column=2, **pad)
        ttk.Scale(parent, from_=0, to=max_value, variable=var_max, orient="horizontal", length=90).grid(row=row, column=3, **pad)

    # ------------------------------------------------------------------
    # Perfiles: preset / manual / guardar / eliminar / seleccionar
    # ------------------------------------------------------------------
    def _on_preset(self, name):
        self._current_hsv_bands = COLOR_PRESETS[name]
        self.bandas_activas_var.set(f"{name} (preset, {len(self._current_hsv_bands)} banda(s))")

    def _on_usar_manual(self):
        self._current_hsv_bands = [(
            (self.h_min.get(), self.s_min.get(), self.v_min.get()),
            (self.h_max.get(), self.s_max.get(), self.v_max.get()),
        )]
        self.bandas_activas_var.set("Rango manual (1 banda)")

    def _on_guardar_perfil(self):
        nombre = self.name_entry.get().strip()
        if not nombre:
            self.resultado_var.set("Ponle un nombre al perfil antes de guardar.")
            return
        try:
            diametro = float(self.diametro_var.get())
        except ValueError:
            self.resultado_var.set("El diámetro real debe ser un número (mm).")
            return

        self.perfiles[nombre] = {
            "hsv": self._current_hsv_bands,
            "diametro_mm": diametro,
            "requiere_hueco": self.requiere_hueco_var.get(),
            "min_area": self.min_area_var.get(),
        }
        save_json(PERFILES_FILE, self.perfiles)
        self.resultado_var.set(f"Perfil '{nombre}' guardado.")
        self._refresh_profile_list(select=nombre)

    def _on_eliminar_perfil(self):
        if self._selected_profile is None:
            return
        self.perfiles.pop(self._selected_profile, None)
        save_json(PERFILES_FILE, self.perfiles)
        self._selected_profile = None
        self.resultado_var.set("Perfil eliminado.")
        self._refresh_profile_list()

    def _refresh_profile_list(self, select=None):
        self.profiles_listbox.delete(0, "end")
        for nombre in sorted(self.perfiles):
            self.profiles_listbox.insert("end", nombre)
        if select and select in self.perfiles:
            idx = sorted(self.perfiles).index(select)
            self.profiles_listbox.selection_set(idx)
            self._selected_profile = select

    def _on_select_profile(self, _event):
        selection = self.profiles_listbox.curselection()
        if not selection:
            return
        nombre = self.profiles_listbox.get(selection[0])
        self._selected_profile = nombre
        perfil = self.perfiles[nombre]

        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, nombre)
        self._current_hsv_bands = perfil["hsv"]
        self.bandas_activas_var.set(f"{len(perfil['hsv'])} banda(s) cargada(s) de '{nombre}'")
        if len(perfil["hsv"]) == 1:
            (h0, s0, v0), (h1, s1, v1) = perfil["hsv"][0]
            self.h_min.set(h0); self.s_min.set(s0); self.v_min.set(v0)
            self.h_max.set(h1); self.s_max.set(s1); self.v_max.set(v1)
        self.diametro_var.set(str(perfil["diametro_mm"]))
        self.requiere_hueco_var.set(perfil["requiere_hueco"])
        self.min_area_var.set(perfil.get("min_area", 500))

    # ------------------------------------------------------------------
    # Calibración de cámara
    # ------------------------------------------------------------------
    def _on_guardar_offset(self):
        try:
            self.calibracion["offset_mm"] = {
                "dx": float(self.dx_var.get()),
                "dy": float(self.dy_var.get()),
                "dz": float(self.dz_var.get()),
            }
        except ValueError:
            self.resultado_var.set("El offset dx/dy/dz debe ser numérico (mm).")
            return
        save_json(CALIBRACION_FILE, self.calibracion)
        self.resultado_var.set("Offset cámara→gripper guardado.")

    # ------------------------------------------------------------------
    # Cola de mensajes (para actualizar la GUI desde los hilos de calibración)
    # ------------------------------------------------------------------
    def _log(self, text):
        self.msg_queue.put(("log", text))

    def _process_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "log":
                    self.calib_log.configure(state="normal")
                    self.calib_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {payload}\n")
                    self.calib_log.see("end")
                    self.calib_log.configure(state="disabled")
                elif kind == "focal_label":
                    self.focal_label_var.set(self._focal_text())
                elif kind == "offset_vars":
                    dx, dy, dz = payload
                    self.dx_var.set(f"{dx:.1f}")
                    self.dy_var.set(f"{dy:.1f}")
                    self.dz_var.set(f"{dz:.1f}")
        except queue.Empty:
            pass
        self.after(100, self._process_queue)

    def _perfil_activo_valido(self):
        if self._selected_profile is None or self._selected_profile not in self.perfiles:
            self._log("Selecciona (o guarda) un perfil en la lista antes de calibrar.")
            return None
        if self.robot is None or not self.robot.connected:
            self._log("Conecta el robot primero (pestaña Control y Movimiento).")
            return None
        return self.perfiles[self._selected_profile]

    # ------------------------------------------------------------------
    # 1. Auto-calibración de foco: sube y baja sobre la pieza de referencia
    # ------------------------------------------------------------------
    def _on_auto_focal(self):
        perfil = self._perfil_activo_valido()
        if perfil is None:
            return
        threading.Thread(target=self._auto_focal_routine, args=(perfil,), daemon=True).start()

    def _auto_focal_routine(self, perfil):
        speed = self.calib_speed_var.get()
        self._log(f"Auto-calibración de foco iniciada con '{self._selected_profile}'...")
        try:
            base_coords = self.robot.get_coords()
        except Exception as exc:
            self._log(f"Error leyendo posición: {exc}")
            return
        if base_coords is None:
            self._log("El robot no respondió con una posición válida. Intenta de nuevo en unos segundos.")
            return

        muestras = []
        for dz in (-15, -7, 0, 8, 16):
            objetivo = list(base_coords)
            objetivo[2] = base_coords[2] + dz
            try:
                self.robot.send_coords(objetivo, speed)
            except Exception as exc:
                self._log(f"Error moviendo (delta Z={dz}): {exc}")
                continue
            time.sleep(1.3)
            try:
                actual = self.robot.get_coords()
                delta_real = actual[2] - base_coords[2] if actual else dz
            except Exception:
                delta_real = dz
            frame = self.camera.get_frame()
            if frame is None:
                self._log(f"Z={delta_real:+.1f}mm: sin imagen de cámara, se omite.")
                continue
            mask = construir_mascara(frame, perfil["hsv"])
            resultado = analizar_mascara(mask, perfil.get("min_area", 500))
            if resultado is None:
                self._log(f"Z={delta_real:+.1f}mm: pieza no detectada, se omite.")
                continue
            muestras.append((delta_real, resultado["diametro_px"]))
            self._log(f"Z={delta_real:+.1f}mm -> diámetro detectado {resultado['diametro_px']:.1f}px")

        try:
            self.robot.send_coords(list(base_coords), speed)
        except Exception:
            pass

        focal = ajustar_focal_por_regresion(muestras, perfil["diametro_mm"])
        if focal is None:
            self._log("No se pudo calcular la focal (muy pocas muestras válidas). Ajusta el color/luz e intenta de nuevo.")
            return
        self.calibracion["focal_px"] = focal
        save_json(CALIBRACION_FILE, self.calibracion)
        self._log(f"Focal calculada automáticamente: {focal:.1f} px (con {len(muestras)} muestras). Guardada.")
        self.msg_queue.put(("focal_label", None))

    # ------------------------------------------------------------------
    # 2. Offset dz: medir a distancia + tocar físicamente una vez
    # ------------------------------------------------------------------
    def _on_medir_aqui(self):
        perfil = self._perfil_activo_valido()
        if perfil is None:
            return
        if not self.calibracion.get("focal_px"):
            self._log("Calibra la focal primero (paso 1).")
            return
        frame = self.camera.get_frame()
        if frame is None:
            self._log("No hay imagen de cámara.")
            return
        mask = construir_mascara(frame, perfil["hsv"])
        resultado = analizar_mascara(mask, perfil.get("min_area", 500))
        if resultado is None:
            self._log("No se detectó la pieza para medir.")
            return
        dist = distancia_mm(perfil["diametro_mm"], resultado["diametro_px"], self.calibracion["focal_px"])
        try:
            coords = self.robot.get_coords()
        except Exception as exc:
            self._log(f"Error leyendo posición: {exc}")
            return
        if coords is None:
            self._log("El robot no respondió con una posición válida. Intenta de nuevo.")
            return
        g_z = coords[2]
        self._dz_medicion = {"distancia_mm": dist, "g_z_obs": g_z}
        self._log(f"Medición tomada: distancia cámara-pieza={dist:.1f}mm, Z del gripper={g_z:.1f}mm")

    def _on_toca_pieza(self):
        if self.robot is None or not self.robot.connected:
            self._log("Conecta el robot primero.")
            return
        try:
            coords = self.robot.get_coords()
        except Exception as exc:
            self._log(f"Error leyendo posición: {exc}")
            return
        if coords is None:
            self._log("El robot no respondió con una posición válida. Intenta de nuevo.")
            return
        g_z = coords[2]
        self._dz_touch_z = g_z
        self._log(f"Toque registrado: Z={g_z:.1f}mm")

    def _on_calcular_dz(self):
        if self._dz_medicion is None or self._dz_touch_z is None:
            self._log("Faltan datos: primero '2a. Medir aquí' y luego '2b. Aquí toca la pieza'.")
            return
        dist = self._dz_medicion["distancia_mm"]
        g_z_obs = self._dz_medicion["g_z_obs"]
        dz = dist - (g_z_obs - self._dz_touch_z)
        self.calibracion["offset_mm"]["dz"] = dz
        save_json(CALIBRACION_FILE, self.calibracion)
        self._log(f"dz calculado automáticamente: {dz:.1f} mm. Guardado.")
        self.msg_queue.put(("offset_vars", (
            self.calibracion["offset_mm"].get("dx", 0.0),
            self.calibracion["offset_mm"].get("dy", 0.0),
            dz,
        )))
        self._dz_medicion = None
        self._dz_touch_z = None

    # ------------------------------------------------------------------
    # 3. Auto-calibración de offset lateral: gira la muñeca (J6)
    # ------------------------------------------------------------------
    def _on_auto_lateral(self):
        perfil = self._perfil_activo_valido()
        if perfil is None:
            return
        if not self.calibracion.get("focal_px"):
            self._log("Calibra la focal primero (paso 1).")
            return
        threading.Thread(target=self._auto_lateral_routine, args=(perfil,), daemon=True).start()

    def _auto_lateral_routine(self, perfil):
        speed = self.calib_speed_var.get()
        self._log("Auto-calibración de offset lateral iniciada (girando la muñeca)...")
        try:
            base_angles = self.robot.get_angles()
        except Exception as exc:
            self._log(f"Error leyendo ángulos: {exc}")
            return
        if base_angles is None:
            self._log("El robot no respondió con ángulos válidos. Intenta de nuevo en unos segundos.")
            return
        base_j6 = base_angles[5]

        puntos = []
        for delta in (-24, -12, 0, 12, 24):
            objetivo_j6 = max(-175.0, min(175.0, base_j6 + delta))
            angulos = list(base_angles)
            angulos[5] = objetivo_j6
            try:
                self.robot.send_angles(angulos, speed)
            except Exception as exc:
                self._log(f"Error girando (J6={objetivo_j6:.1f}): {exc}")
                continue
            time.sleep(1.3)
            frame = self.camera.get_frame()
            if frame is None:
                self._log(f"J6={objetivo_j6:.1f}°: sin imagen, se omite.")
                continue
            mask = construir_mascara(frame, perfil["hsv"])
            resultado = analizar_mascara(mask, perfil.get("min_area", 500))
            if resultado is None:
                self._log(f"J6={objetivo_j6:.1f}°: pieza no detectada, se omite.")
                continue
            puntos.append(resultado["centro_px"])
            self._log(f"J6={objetivo_j6:.1f}° -> centro detectado {resultado['centro_px']}")

        try:
            self.robot.send_angles(list(base_angles), speed)
        except Exception:
            pass

        circulo = ajustar_circulo(puntos)
        if circulo is None:
            self._log("No se pudo ajustar el círculo (muy pocas muestras válidas).")
            return
        cx, cy, radio = circulo

        time.sleep(1.0)
        frame = self.camera.get_frame()
        dist_mm = None
        if frame is not None:
            mask = construir_mascara(frame, perfil["hsv"])
            resultado = analizar_mascara(mask, perfil.get("min_area", 500))
            if resultado is not None:
                dist_mm = distancia_mm(perfil["diametro_mm"], resultado["diametro_px"], self.calibracion["focal_px"])
        if dist_mm is None:
            self._log("No se pudo medir la distancia actual para convertir el offset de px a mm.")
            return

        dx_mm, dy_mm = offset_xy_mm(cx, cy, FRAME_WIDTH, FRAME_HEIGHT, dist_mm, self.calibracion["focal_px"])
        self.calibracion["offset_mm"]["dx"] = dx_mm
        self.calibracion["offset_mm"]["dy"] = dy_mm
        save_json(CALIBRACION_FILE, self.calibracion)
        self._log(
            f"Offset lateral calculado: dx={dx_mm:.1f}mm, dy={dy_mm:.1f}mm "
            f"(centro de giro en px: {cx:.0f},{cy:.0f}, radio {radio:.1f}px). Guardado."
        )
        self.msg_queue.put(("offset_vars", (
            dx_mm, dy_mm, self.calibracion["offset_mm"].get("dz", 0.0),
        )))

    def _on_capturar_focal(self):
        if self._selected_profile is None:
            self.resultado_var.set("Selecciona (o guarda primero) un perfil de la lista para calibrar la focal.")
            return
        perfil = self.perfiles[self._selected_profile]
        frame = self.camera.get_frame()
        if frame is None:
            self.resultado_var.set("No hay imagen de cámara (¿está iniciada?).")
            return
        try:
            distancia_real = float(self.distancia_real_var.get())
        except ValueError:
            self.resultado_var.set("La distancia real medida debe ser un número (mm).")
            return

        mask = construir_mascara(frame, perfil["hsv"])
        resultado = analizar_mascara(mask, perfil.get("min_area", 500))
        if resultado is None:
            self.resultado_var.set(f"No se detectó la pieza '{self._selected_profile}' en la imagen actual.")
            return

        focal_px = distancia_real * resultado["diametro_px"] / perfil["diametro_mm"]
        self.calibracion["focal_px"] = focal_px
        save_json(CALIBRACION_FILE, self.calibracion)
        self.focal_label_var.set(self._focal_text())
        self.resultado_var.set(
            f"Focal calculada: {focal_px:.1f} px (diámetro detectado: {resultado['diametro_px']:.0f} px "
            f"a {distancia_real:.0f} mm real)."
        )

    # ------------------------------------------------------------------
    # Video en vivo + prueba de perfil
    # ------------------------------------------------------------------
    def _update_frame(self):
        frame = self.camera.get_frame() if self.camera.running else None
        if frame is not None:
            display = frame
            if self.detectar_var.get() and self._selected_profile is not None:
                display = self._probar_perfil(frame, self.perfiles[self._selected_profile])
            self._render(display)
        else:
            self.video_label.configure(image="", text="Cámara apagada")
        self.after(30, self._update_frame)

    def _probar_perfil(self, frame, perfil):
        mask = construir_mascara(frame, perfil["hsv"])
        resultado = analizar_mascara(mask, perfil.get("min_area", 500))
        display = frame.copy()
        if resultado is None:
            self.resultado_var.set("Sin detección para el perfil seleccionado.")
            return display

        cx, cy = resultado["centro_px"]
        radius = int(resultado["diametro_px"] / 2)
        color_borde = (0, 255, 0) if resultado["hueco"] else (0, 0, 255)
        cv2.circle(display, (cx, cy), radius, color_borde, 2)
        cv2.circle(display, (cx, cy), 4, (255, 0, 0), -1)
        if resultado["hueco_contorno"] is not None:
            cv2.drawContours(display, [resultado["hueco_contorno"]], -1, (0, 255, 255), 2)

        hueco_txt = "Con hueco (correcta)" if resultado["hueco"] else "Sin hueco (incorrecta)"
        if perfil["requiere_hueco"] and not resultado["hueco"]:
            estado = "RECHAZAR: se requiere hueco visible"
        else:
            estado = "OK para agarrar"

        focal = self.calibracion.get("focal_px")
        extra = ""
        if focal:
            dist = distancia_mm(perfil["diametro_mm"], resultado["diametro_px"], focal)
            if dist is not None:
                dx_mm, dy_mm = offset_xy_mm(cx, cy, FRAME_WIDTH, FRAME_HEIGHT, dist, focal)
                offset = self.calibracion["offset_mm"]
                falta_bajar = dist - offset.get("dz", 0.0)
                extra = (
                    f"\nDistancia cámara-pieza: {dist:.1f} mm"
                    f"\nDesplazamiento lateral real: dx={dx_mm:.1f} mm, dy={dy_mm:.1f} mm"
                    f"\nLe falta bajar al gripper: {falta_bajar:.1f} mm"
                )

        self.resultado_var.set(
            f"{self._selected_profile}: {hueco_txt}\nDiámetro: {resultado['diametro_px']:.0f} px   "
            f"Área: {int(resultado['area'])} px²\n{estado}{extra}"
        )
        return display

    def _render(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        photo = ImageTk.PhotoImage(image=Image.fromarray(rgb))
        self.video_label.configure(image=photo, text="")
        self.video_label.image = photo

    def shutdown(self):
        pass
