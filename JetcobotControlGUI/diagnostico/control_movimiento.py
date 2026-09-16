#!/usr/bin/env python3
# encoding: utf-8
"""
Control y Movimiento - versión de diagnóstico (sin hilos, todo síncrono).

Aísla SOLO la función de conexión/motores/articulaciones/gripper/movimiento
cartesiano del JetCobot, sin cámara ni el resto de la app, para descartar
que "los comandos no se ejecutan" venga de otra parte (hilos, cola de
mensajes, otras pestañas compartiendo el mismo robot, etc).

Diferencias a propósito respecto al panel normal (panels/jetcobot_gui.py):
  - Cada botón llama a pymycobot DIRECTAMENTE y en el mismo hilo de la GUI
    (se congela un instante mientras responde — es la idea: si un comando
    se cuelga, se nota).
  - Antes y después de cada comando de movimiento, consulta y muestra
    is_paused() / is_moving(), para ver si el robot está detenido/pausado
    aunque el comando se haya "enviado bien".
  - El botón "Diagnóstico" vuelca de una vez is_power_on, is_paused,
    is_moving, is_all_servo_enable, get_error_information, get_angles y
    get_coords, tal cual los devuelve la librería.

Uso:
    python3 diagnostico/control_movimiento.py

Requiere:
    pip install pymycobot
"""

import time
import tkinter as tk
from tkinter import ttk

from pymycobot.mycobot280 import MyCobot280

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 1000000

JOINT_NAMES = ["J1", "J2", "J3", "J4", "J5", "J6"]
ANGLE_MIN = [-168, -135, -150, -145, -165, -180]
ANGLE_MAX = [168, 90, 150, 145, 165, 180]
HOME_ANGLES = [0, 0, 0, 0, 0, 45]

# Mismo orden/ids que pymycobot.genre.Coord: X,Y,Z,Rx,Ry,Rz
CART_AXIS_NAMES = ["X", "Y", "Z", "R", "P", "Yaw"]

GRIPPER_MIN = 0
GRIPPER_MAX = 100


class ControlMovimientoDebug(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JetCobot - Control y Movimiento (diagnóstico)")
        self.mc = None

        self.speed_var = tk.IntVar(value=50)
        self.step_var = tk.IntVar(value=5)
        self.cart_step_var = tk.IntVar(value=5)
        self.gripper_step_var = tk.IntVar(value=10)

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}

        conn_frame = ttk.LabelFrame(self, text="Conexión")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky="ew", **pad)

        ttk.Label(conn_frame, text="Puerto:").grid(row=0, column=0, **pad)
        self.port_entry = ttk.Entry(conn_frame, width=16)
        self.port_entry.insert(0, DEFAULT_PORT)
        self.port_entry.grid(row=0, column=1, **pad)

        ttk.Label(conn_frame, text="Baudrate:").grid(row=0, column=2, **pad)
        self.baud_entry = ttk.Entry(conn_frame, width=10)
        self.baud_entry.insert(0, str(DEFAULT_BAUD))
        self.baud_entry.grid(row=0, column=3, **pad)

        ttk.Button(conn_frame, text="Conectar", command=self._on_connect).grid(row=0, column=4, **pad)
        ttk.Button(conn_frame, text="Desconectar", command=self._on_disconnect).grid(row=0, column=5, **pad)
        self.status_label = ttk.Label(conn_frame, text="● Desconectado", foreground="red")
        self.status_label.grid(row=0, column=6, **pad)

        power_frame = ttk.LabelFrame(self, text="Motores")
        power_frame.grid(row=1, column=0, columnspan=2, sticky="ew", **pad)

        ttk.Button(power_frame, text="Power ON", command=self._on_power_on).grid(row=0, column=0, **pad)
        ttk.Button(power_frame, text="Power OFF", command=self._on_power_off).grid(row=0, column=1, **pad)
        ttk.Button(power_frame, text="Modo libre (soltar)", command=self._on_release).grid(row=0, column=2, **pad)
        ttk.Button(power_frame, text="Bloquear servos", command=self._on_focus).grid(row=0, column=3, **pad)
        ttk.Button(power_frame, text="Ir a Home", command=self._on_home).grid(row=0, column=4, **pad)

        tk.Button(
            power_frame, text="PARADA DE EMERGENCIA", command=self._on_stop,
            bg="#c0392b", fg="white", activebackground="#e74c3c", activeforeground="white",
        ).grid(row=0, column=5, **pad)
        tk.Button(
            power_frame, text="Reanudar", command=self._on_resume,
            bg="#27ae60", fg="white", activebackground="#2ecc71", activeforeground="white",
        ).grid(row=0, column=6, **pad)
        tk.Button(
            power_frame, text="Diagnóstico", command=self._on_diagnostico,
            bg="#2980b9", fg="white", activebackground="#3498db", activeforeground="white",
        ).grid(row=0, column=7, **pad)
        ttk.Button(power_frame, text="Limpiar errores", command=self._on_clear_errors).grid(row=0, column=8, **pad)
        tk.Button(
            power_frame, text="Fijar referencia = Base (0)", command=self._on_fijar_referencia_base,
            bg="#8e44ad", fg="white", activebackground="#9b59b6", activeforeground="white",
        ).grid(row=0, column=9, **pad)

        speed_frame = ttk.LabelFrame(self, text="Parámetros de movimiento")
        speed_frame.grid(row=2, column=0, columnspan=2, sticky="ew", **pad)

        ttk.Label(speed_frame, text="Velocidad").grid(row=0, column=0, **pad)
        ttk.Scale(speed_frame, from_=1, to=100, variable=self.speed_var, orient="horizontal", length=140).grid(row=0, column=1, **pad)
        ttk.Label(speed_frame, textvariable=self.speed_var, width=3).grid(row=0, column=2, **pad)

        ttk.Label(speed_frame, text="Paso articulación (°)").grid(row=0, column=3, **pad)
        ttk.Scale(speed_frame, from_=1, to=20, variable=self.step_var, orient="horizontal", length=120).grid(row=0, column=4, **pad)
        ttk.Label(speed_frame, textvariable=self.step_var, width=3).grid(row=0, column=5, **pad)

        ttk.Label(speed_frame, text="Paso cartesiano (mm/°)").grid(row=0, column=6, **pad)
        ttk.Scale(speed_frame, from_=1, to=20, variable=self.cart_step_var, orient="horizontal", length=120).grid(row=0, column=7, **pad)
        ttk.Label(speed_frame, textvariable=self.cart_step_var, width=3).grid(row=0, column=8, **pad)

        joints_frame = ttk.LabelFrame(self, text="Articulaciones")
        joints_frame.grid(row=3, column=0, sticky="nsew", **pad)
        for i, name in enumerate(JOINT_NAMES):
            ttk.Label(joints_frame, text=f"{name} [{ANGLE_MIN[i]}°,{ANGLE_MAX[i]}°]", width=16).grid(row=i, column=0, **pad)
            ttk.Button(joints_frame, text="-", width=3, command=lambda jid=i + 1: self._on_jog(jid, -1)).grid(row=i, column=1, **pad)
            ttk.Button(joints_frame, text="+", width=3, command=lambda jid=i + 1: self._on_jog(jid, 1)).grid(row=i, column=2, **pad)

        right_frame = ttk.Frame(self)
        right_frame.grid(row=3, column=1, sticky="nsew", **pad)

        cart_frame = ttk.LabelFrame(right_frame, text="Movimiento cartesiano (X,Y,Z,R,P,Yaw)")
        cart_frame.pack(fill="x", **pad)
        for i, name in enumerate(CART_AXIS_NAMES):
            axis_id = i + 1
            ttk.Label(cart_frame, text=name, width=4).grid(row=i // 3, column=(i % 3) * 3, **pad)
            ttk.Button(cart_frame, text="-", width=3, command=lambda a=axis_id: self._on_cart_jog(a, -1)).grid(
                row=i // 3, column=(i % 3) * 3 + 1, **pad
            )
            ttk.Button(cart_frame, text="+", width=3, command=lambda a=axis_id: self._on_cart_jog(a, 1)).grid(
                row=i // 3, column=(i % 3) * 3 + 2, **pad
            )

        gripper_frame = ttk.LabelFrame(right_frame, text="Gripper")
        gripper_frame.pack(fill="x", **pad)
        ttk.Button(gripper_frame, text="Abrir", command=lambda: self._on_gripper_set(GRIPPER_MAX)).grid(row=0, column=0, **pad)
        ttk.Button(gripper_frame, text="Cerrar", command=lambda: self._on_gripper_set(GRIPPER_MIN)).grid(row=0, column=1, **pad)
        ttk.Button(gripper_frame, text="-", width=3, command=lambda: self._on_gripper_step(-1)).grid(row=1, column=0, **pad)
        ttk.Button(gripper_frame, text="+", width=3, command=lambda: self._on_gripper_step(1)).grid(row=1, column=1, **pad)

        estado_frame = ttk.LabelFrame(right_frame, text="Estado actual")
        estado_frame.pack(fill="x", **pad)
        ttk.Button(estado_frame, text="Leer ángulos/coords ahora", command=self._on_leer_estado).pack(**pad)

        pruebas_frame = ttk.LabelFrame(right_frame, text="Pruebas de movimiento cartesiano")
        pruebas_frame.pack(fill="x", **pad)
        ttk.Button(
            pruebas_frame, text="Probar send_coords (X +5, absoluto)", command=self._on_probar_send_coords
        ).pack(fill="x", **pad)
        ttk.Button(
            pruebas_frame, text="Probar send_coord (solo eje X, id=1)", command=self._on_probar_send_coord_simple
        ).pack(fill="x", **pad)

        log_frame = ttk.LabelFrame(self, text="Registro (crudo, sin filtrar)")
        log_frame.grid(row=4, column=0, columnspan=2, sticky="ew", **pad)
        self.log_text = tk.Text(log_frame, height=16, width=110, state="disabled")
        self.log_text.pack(**pad)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {text}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.update_idletasks()

    def _estado_breve(self):
        if self.mc is None:
            return "sin conexión"
        try:
            return f"is_paused={self.mc.is_paused()!r} is_moving={self.mc.is_moving()!r}"
        except Exception as exc:
            return f"(error leyendo estado: {exc})"

    def _call(self, etiqueta, fn, *args):
        if self.mc is None:
            self._log(f"{etiqueta}: no conectado.")
            return None
        antes = self._estado_breve()
        try:
            resultado = fn(*args)
        except Exception as exc:
            self._log(f"{etiqueta} -> EXCEPCIÓN: {exc}  (antes: {antes})")
            return None
        despues = self._estado_breve()
        self._log(f"{etiqueta} -> devolvió {resultado!r}   [{antes}]  ->  [{despues}]")
        return resultado

    # ------------------------------------------------------------------
    # Conexión / motores
    # ------------------------------------------------------------------
    def _on_connect(self):
        port = self.port_entry.get().strip()
        try:
            baud = int(self.baud_entry.get().strip())
        except ValueError:
            self._log("Baudrate inválido.")
            return
        try:
            self.mc = MyCobot280(port, baud)
            angles = self.mc.get_angles()
            try:
                ref = self.mc.get_reference_frame()
            except Exception as exc:
                ref = f"error: {exc}"
            self._log(f"Conectado a {port}@{baud}. get_angles() inicial = {angles!r}")
            self._log(f"get_reference_frame() = {ref!r}  (0=base, 1=herramienta — debería ser 0)")
            self.status_label.configure(text="● Conectado", foreground="green")
        except Exception as exc:
            self.mc = None
            self._log(f"No se pudo conectar: {exc}")
            self.status_label.configure(text="● Desconectado", foreground="red")

    def _on_disconnect(self):
        if self.mc is not None:
            try:
                self.mc.close()
            except Exception:
                pass
        self.mc = None
        self._log("Desconectado.")
        self.status_label.configure(text="● Desconectado", foreground="red")

    def _on_power_on(self):
        self._call("Power ON", self.mc.power_on if self.mc else (lambda: None))

    def _on_power_off(self):
        self._call("Power OFF", self.mc.power_off if self.mc else (lambda: None))

    def _on_release(self):
        self._call("Modo libre", self.mc.release_all_servos if self.mc else (lambda: None))

    def _on_focus(self):
        self._call("Bloquear servos", self.mc.focus_all_servos if self.mc else (lambda: None))

    def _on_home(self):
        self._call("Ir a Home", self.mc.send_angles if self.mc else (lambda *a: None), HOME_ANGLES, self.speed_var.get())

    def _on_stop(self):
        self._call("PARADA DE EMERGENCIA", self.mc.stop if self.mc else (lambda: None))

    def _on_resume(self):
        self._call("Reanudar", self.mc.resume if self.mc else (lambda: None))

    def _on_clear_errors(self):
        self._call("Limpiar errores", self.mc.clear_error_information if self.mc else (lambda: None))

    def _on_fijar_referencia_base(self):
        self._call("set_reference_frame(0)", self.mc.set_reference_frame if self.mc else (lambda *a: None), 0)

    # ------------------------------------------------------------------
    # Articulaciones / cartesiano / gripper
    # ------------------------------------------------------------------
    def _on_jog(self, joint_id, direction):
        step = self.step_var.get() * direction
        self._call(f"jog_increment_angle(J{joint_id}, {step:+d})", self.mc.jog_increment_angle if self.mc else (lambda *a: None),
                   joint_id, step, self.speed_var.get())

    def _on_cart_jog(self, axis_id, direction):
        # jog_increment_coord y send_coord (un solo eje) no mueven el robot en
        # este firmware aunque no devuelven error (ver botones de prueba más
        # abajo) — por eso acá se arma el vector de 6 coordenadas completo y
        # se manda con send_coords, que es lo único que sí funciona.
        step = self.cart_step_var.get() * direction
        nombre = CART_AXIS_NAMES[axis_id - 1]
        if self.mc is None:
            self._log(f"jog cartesiano {nombre}: no conectado.")
            return
        coords = self._call("get_coords() (para el jog cartesiano)", self.mc.get_coords)
        if not isinstance(coords, (list, tuple)) or len(coords) != 6:
            self._log("No se pudo leer una coordenada válida, no se aplica el jog.")
            return
        objetivo = list(coords)
        objetivo[axis_id - 1] += step
        self._call(f"send_coords({objetivo}, {self.speed_var.get()})  [jog {nombre} {step:+d}]",
                   self.mc.send_coords, objetivo, self.speed_var.get())

    def _on_gripper_set(self, value):
        self._call(f"set_gripper_value({value})", self.mc.set_gripper_value if self.mc else (lambda *a: None),
                   value, self.speed_var.get())

    def _on_gripper_step(self, direction):
        step = self.gripper_step_var.get() * direction
        actual = self._call("get_gripper_value()", self.mc.get_gripper_value if self.mc else (lambda: None))
        if not isinstance(actual, (int, float)) or actual < 0:
            self._log("No se pudo leer el valor actual del gripper, no se aplica el paso.")
            return
        nuevo = max(GRIPPER_MIN, min(GRIPPER_MAX, actual + step))
        self._call(f"set_gripper_value({nuevo})", self.mc.set_gripper_value if self.mc else (lambda *a: None),
                   nuevo, self.speed_var.get())

    def _on_leer_estado(self):
        self._call("get_angles()", self.mc.get_angles if self.mc else (lambda: None))
        self._call("get_coords()", self.mc.get_coords if self.mc else (lambda: None))
        self._call("get_gripper_value()", self.mc.get_gripper_value if self.mc else (lambda: None))

    def _on_probar_send_coords(self):
        if self.mc is None:
            self._log("No conectado.")
            return
        coords = self._call("get_coords() (antes de la prueba)", self.mc.get_coords)
        if not isinstance(coords, (list, tuple)) or len(coords) != 6:
            self._log("No se pudo leer una coordenada válida, aborto la prueba.")
            return
        objetivo = list(coords)
        objetivo[0] += self.cart_step_var.get()
        self._call(f"send_coords({objetivo}, {self.speed_var.get()})", self.mc.send_coords, objetivo, self.speed_var.get())

    def _on_probar_send_coord_simple(self):
        if self.mc is None:
            self._log("No conectado.")
            return
        coords = self._call("get_coords() (antes de la prueba)", self.mc.get_coords)
        if not isinstance(coords, (list, tuple)) or len(coords) != 6:
            self._log("No se pudo leer una coordenada válida, aborto la prueba.")
            return
        objetivo_x = coords[0] + self.cart_step_var.get()
        self._call(f"send_coord(1, {objetivo_x}, {self.speed_var.get()})", self.mc.send_coord, 1, objetivo_x, self.speed_var.get())

    # ------------------------------------------------------------------
    def _on_diagnostico(self):
        if self.mc is None:
            self._log("No conectado.")
            return
        self._log("=== DIAGNÓSTICO ===")
        campos = [
            "is_power_on", "is_controller_connected", "is_paused", "is_moving",
            "is_all_servo_enable", "get_error_information", "get_angles", "get_coords",
            "get_reference_frame", "get_movement_type", "get_end_type",
        ]
        for nombre in campos:
            try:
                valor = getattr(self.mc, nombre)()
            except Exception as exc:
                valor = f"EXCEPCIÓN: {exc}"
            self._log(f"  {nombre}() = {valor!r}")
        self._log("===================")


if __name__ == "__main__":
    app = ControlMovimientoDebug()
    app.mainloop()
