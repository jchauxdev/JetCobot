#!/usr/bin/env python3
# encoding: utf-8
"""
Interfaz de escritorio del JetCobot + posiciones guardadas por coordenadas.

Parte de jetcobot_gui.py (misma conexión, motores, articulaciones y gripper)
y añade un panel para crear botones de posición: se introducen X,Y,Z,R,P,Yaw,
un nombre, y al crear el botón, al pulsarlo el robot se mueve a esa coordenada
con mc.send_coords(). Las posiciones se guardan en posiciones_guardadas.json
en esta misma carpeta, así persisten entre ejecuciones.

Uso:
    python3 jetcobot_gui_posiciones.py

Requiere:
    pip install pymycobot
"""

import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from jetcobot_gui import JetcobotControlPanel

COORD_NAMES = ["X", "Y", "Z", "R", "P", "Yaw"]
POSITIONS_FILE = Path(__file__).parent / "posiciones_guardadas.json"


def load_positions():
    if POSITIONS_FILE.exists():
        try:
            with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_positions(positions):
    with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2, ensure_ascii=False)


class PosicionesPanel(JetcobotControlPanel):
    """JetcobotControlPanel + panel de posiciones guardadas por coordenadas."""

    def __init__(self, master, **kwargs):
        self.saved_positions = load_positions()
        self.position_rows = {}
        super().__init__(master, **kwargs)
        self._refresh_position_list()

    # ------------------------------------------------------------------
    def _build_ui(self):
        super()._build_ui()
        self._build_positions_panel()

    def _build_positions_panel(self):
        pad = {"padx": 6, "pady": 4}

        panel = ttk.LabelFrame(self, text="Posiciones guardadas (coordenadas)")
        panel.grid(row=5, column=0, columnspan=2, sticky="ew", **pad)

        add_frame = ttk.Frame(panel)
        add_frame.pack(fill="x", **pad)

        ttk.Label(add_frame, text="Nombre:").grid(row=0, column=0, **pad)
        self.pos_name_entry = ttk.Entry(add_frame, width=16)
        self.pos_name_entry.grid(row=0, column=1, **pad)

        ttk.Button(add_frame, text="Usar posición actual", command=self._on_use_current).grid(row=0, column=2, **pad)
        ttk.Button(add_frame, text="Crear botón", command=self._on_create_position).grid(row=0, column=3, **pad)

        self.pos_coord_entries = []
        for i, label in enumerate(COORD_NAMES):
            ttk.Label(add_frame, text=label).grid(row=1, column=2 * i, **pad)
            entry = ttk.Entry(add_frame, width=8)
            entry.grid(row=1, column=2 * i + 1, **pad)
            self.pos_coord_entries.append(entry)

        self.saved_list_frame = ttk.Frame(panel)
        self.saved_list_frame.pack(fill="x", **pad)

    # ------------------------------------------------------------------
    # Manejo de la cola: recibir coordenadas leídas para rellenar el formulario
    # ------------------------------------------------------------------
    def _on_extra_message(self, kind, payload):
        if kind == "fill_coord_entries":
            for entry, value in zip(self.pos_coord_entries, payload):
                entry.delete(0, "end")
                entry.insert(0, f"{value:.1f}")

    def _on_use_current(self):
        def do_read():
            coords = self.robot.get_coords()
            if coords:
                self.msg_queue.put(("fill_coord_entries", coords))
            else:
                self._log("No se pudo leer la posición actual.")

        self._run_async(do_read)

    # ------------------------------------------------------------------
    # Crear / eliminar / ejecutar posiciones guardadas
    # ------------------------------------------------------------------
    def _on_create_position(self):
        name = self.pos_name_entry.get().strip()
        if not name:
            self._log("Ponle un nombre a la posición antes de crear el botón.")
            return

        try:
            coords = [float(e.get()) for e in self.pos_coord_entries]
        except ValueError:
            self._log("Las 6 coordenadas (X,Y,Z,R,P,Yaw) deben ser números.")
            return

        is_new = name not in self.saved_positions
        self.saved_positions[name] = coords
        save_positions(self.saved_positions)
        self._log(f"Posición '{name}' guardada: {coords}")

        if is_new:
            self._add_position_row(name)
        else:
            self.position_rows[name]["coords_label"].configure(text=self._format_coords(coords))

    def _on_delete_position(self, name):
        self.saved_positions.pop(name, None)
        save_positions(self.saved_positions)
        row = self.position_rows.pop(name, None)
        if row is not None:
            row["frame"].destroy()
        self._log(f"Posición '{name}' eliminada.")

    def _on_go_to_position(self, name):
        coords = self.saved_positions.get(name)
        if coords is None:
            self._log(f"La posición '{name}' ya no existe.")
            return
        self._log(f"Moviendo a posición '{name}': {coords}")
        self._run_async(self.robot.send_coords, coords, self.speed_var.get())

    def _format_coords(self, coords):
        return ", ".join(f"{v:.1f}" for v in coords)

    def _add_position_row(self, name):
        pad = {"padx": 4, "pady": 2}
        row_frame = ttk.Frame(self.saved_list_frame)
        row_frame.pack(fill="x", **pad)

        go_btn = ttk.Button(row_frame, text=f"Ir a: {name}", width=20,
                             command=lambda n=name: self._on_go_to_position(n))
        go_btn.pack(side="left", **pad)

        coords_label = ttk.Label(row_frame, text=self._format_coords(self.saved_positions[name]), width=40)
        coords_label.pack(side="left", **pad)

        del_btn = ttk.Button(row_frame, text="Eliminar", width=8,
                              command=lambda n=name: self._on_delete_position(n))
        del_btn.pack(side="left", **pad)

        self.position_rows[name] = {"frame": row_frame, "coords_label": coords_label}

    def _refresh_position_list(self):
        for name in list(self.saved_positions.keys()):
            self._add_position_row(name)


class JetcobotGUIPosiciones(tk.Tk):
    """Ventana independiente que aloja el PosicionesPanel (uso standalone)."""

    def __init__(self):
        super().__init__()
        self.title("JetCobot - Control + posiciones guardadas")
        self.resizable(False, False)
        self.panel = PosicionesPanel(self)
        self.panel.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self.panel.shutdown()
        self.destroy()


if __name__ == "__main__":
    app = JetcobotGUIPosiciones()
    app.mainloop()
