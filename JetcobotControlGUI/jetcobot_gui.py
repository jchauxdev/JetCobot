#!/usr/bin/env python3
# encoding: utf-8
"""
Interfaz de escritorio basica para el control del JetCobot (MyCobot280).

Uso:
    python3 jetcobot_gui.py

Requiere:
    pip install pymycobot
"""

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

from pymycobot.mycobot280 import MyCobot280

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 1000000

JOINT_NAMES = ["J1", "J2", "J3", "J4", "J5", "J6"]
ANGLE_MIN = [-168, -135, -150, -145, -165, -180]
ANGLE_MAX = [168, 90, 150, 145, 165, 180]
HOME_ANGLES = [0, 0, 0, 0, 0, -45]

GRIPPER_MIN = 0
GRIPPER_MAX = 100

POLL_INTERVAL = 0.7  # segundos entre lecturas de estado del robot


class RobotController:
    """Envuelve MyCobot280 y serializa el acceso al puerto serie con un lock."""

    def __init__(self):
        self.mc = None
        self.lock = threading.Lock()

    @property
    def connected(self):
        return self.mc is not None

    def connect(self, port, baud):
        with self.lock:
            mc = MyCobot280(port, baud)
            # Fuerza una lectura para confirmar que el robot responde de verdad.
            mc.get_angles()
            self.mc = mc

    def disconnect(self):
        with self.lock:
            if self.mc is not None:
                try:
                    self.mc.close()
                except Exception:
                    pass
                self.mc = None

    def _call(self, fn, *args, **kwargs):
        if self.mc is None:
            raise RuntimeError("El robot no está conectado.")
        with self.lock:
            return fn(*args, **kwargs)

    def get_angles(self):
        return self._call(self.mc.get_angles)

    def get_coords(self):
        return self._call(self.mc.get_coords)

    def get_gripper_value(self):
        return self._call(self.mc.get_gripper_value)

    def jog_joint(self, joint_id, step_deg, speed):
        self._call(self.mc.jog_increment_angle, joint_id, step_deg, speed)

    def send_angles(self, angles, speed):
        self._call(self.mc.send_angles, angles, speed)

    def set_gripper(self, value, speed):
        value = max(GRIPPER_MIN, min(GRIPPER_MAX, value))
        self._call(self.mc.set_gripper_value, value, speed)

    def power_on(self):
        self._call(self.mc.power_on)

    def power_off(self):
        self._call(self.mc.power_off)

    def release_servos(self):
        self._call(self.mc.release_all_servos)

    def focus_servos(self):
        self._call(self.mc.focus_all_servos)

    def stop(self):
        self._call(self.mc.stop)


class JetcobotGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JetCobot - Control básico")
        self.resizable(False, False)

        self.robot = RobotController()
        self.msg_queue = queue.Queue()
        self.auto_update = tk.BooleanVar(value=True)
        self._poll_thread = None
        self._poll_stop = threading.Event()

        self.speed_var = tk.IntVar(value=50)
        self.step_var = tk.IntVar(value=5)
        self.gripper_step_var = tk.IntVar(value=10)

        self.angle_labels = []
        self.gripper_label_var = tk.StringVar(value="--")
        self.coords_label_var = tk.StringVar(value="--")

        self._build_ui()
        self._set_controls_enabled(False)
        self.after(100, self._process_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Construccion de la interfaz
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

        self.connect_btn = ttk.Button(conn_frame, text="Conectar", command=self._on_connect)
        self.connect_btn.grid(row=0, column=4, **pad)
        self.disconnect_btn = ttk.Button(conn_frame, text="Desconectar", command=self._on_disconnect)
        self.disconnect_btn.grid(row=0, column=5, **pad)

        self.status_label = ttk.Label(conn_frame, text="● Desconectado", foreground="red")
        self.status_label.grid(row=0, column=6, **pad)

        power_frame = ttk.LabelFrame(self, text="Motores")
        power_frame.grid(row=1, column=0, columnspan=2, sticky="ew", **pad)

        self.power_on_btn = ttk.Button(power_frame, text="Power ON", command=self._on_power_on)
        self.power_on_btn.grid(row=0, column=0, **pad)
        self.power_off_btn = ttk.Button(power_frame, text="Power OFF", command=self._on_power_off)
        self.power_off_btn.grid(row=0, column=1, **pad)
        self.release_btn = ttk.Button(power_frame, text="Modo libre (soltar)", command=self._on_release)
        self.release_btn.grid(row=0, column=2, **pad)
        self.focus_btn = ttk.Button(power_frame, text="Bloquear servos", command=self._on_focus)
        self.focus_btn.grid(row=0, column=3, **pad)
        self.home_btn = ttk.Button(power_frame, text="Ir a Home", command=self._on_home)
        self.home_btn.grid(row=0, column=4, **pad)

        self.stop_btn = tk.Button(
            power_frame, text="PARADA DE EMERGENCIA", command=self._on_stop,
            bg="#c0392b", fg="white", activebackground="#e74c3c", activeforeground="white",
        )
        self.stop_btn.grid(row=0, column=5, **pad)

        speed_frame = ttk.LabelFrame(self, text="Parámetros de movimiento")
        speed_frame.grid(row=2, column=0, columnspan=2, sticky="ew", **pad)

        ttk.Label(speed_frame, text="Velocidad").grid(row=0, column=0, **pad)
        ttk.Scale(speed_frame, from_=1, to=100, variable=self.speed_var, orient="horizontal", length=160).grid(row=0, column=1, **pad)
        ttk.Label(speed_frame, textvariable=self.speed_var).grid(row=0, column=2, **pad)

        ttk.Label(speed_frame, text="Paso articulación (°)").grid(row=0, column=3, **pad)
        ttk.Scale(speed_frame, from_=1, to=20, variable=self.step_var, orient="horizontal", length=160).grid(row=0, column=4, **pad)
        ttk.Label(speed_frame, textvariable=self.step_var).grid(row=0, column=5, **pad)

        ttk.Checkbutton(speed_frame, text="Auto-actualizar estado", variable=self.auto_update).grid(row=0, column=6, **pad)

        joints_frame = ttk.LabelFrame(self, text="Articulaciones")
        joints_frame.grid(row=3, column=0, sticky="nsew", **pad)

        for i, name in enumerate(JOINT_NAMES):
            ttk.Label(joints_frame, text=f"{name} [{ANGLE_MIN[i]}° , {ANGLE_MAX[i]}°]", width=18).grid(row=i, column=0, **pad)
            minus_btn = ttk.Button(joints_frame, text="-", width=3, command=lambda jid=i + 1: self._on_jog(jid, -1))
            minus_btn.grid(row=i, column=1, **pad)
            plus_btn = ttk.Button(joints_frame, text="+", width=3, command=lambda jid=i + 1: self._on_jog(jid, 1))
            plus_btn.grid(row=i, column=2, **pad)
            value_var = tk.StringVar(value="--")
            ttk.Label(joints_frame, textvariable=value_var, width=8).grid(row=i, column=3, **pad)
            self.angle_labels.append(value_var)

        side_frame = ttk.Frame(self)
        side_frame.grid(row=3, column=1, sticky="nsew", **pad)

        gripper_frame = ttk.LabelFrame(side_frame, text="Gripper")
        gripper_frame.pack(fill="x", **pad)

        ttk.Button(gripper_frame, text="Abrir", command=lambda: self._on_gripper_set(GRIPPER_MAX)).grid(row=0, column=0, **pad)
        ttk.Button(gripper_frame, text="Cerrar", command=lambda: self._on_gripper_set(GRIPPER_MIN)).grid(row=0, column=1, **pad)
        ttk.Button(gripper_frame, text="-", width=3, command=lambda: self._on_gripper_step(-1)).grid(row=1, column=0, **pad)
        ttk.Button(gripper_frame, text="+", width=3, command=lambda: self._on_gripper_step(1)).grid(row=1, column=1, **pad)
        ttk.Label(gripper_frame, text="Paso gripper").grid(row=2, column=0, **pad)
        ttk.Scale(gripper_frame, from_=1, to=30, variable=self.gripper_step_var, orient="horizontal", length=100).grid(row=2, column=1, **pad)
        ttk.Label(gripper_frame, text="Valor:").grid(row=3, column=0, **pad)
        ttk.Label(gripper_frame, textvariable=self.gripper_label_var).grid(row=3, column=1, **pad)

        coords_frame = ttk.LabelFrame(side_frame, text="Coordenadas [X,Y,Z,R,P,Y]")
        coords_frame.pack(fill="x", **pad)
        ttk.Label(coords_frame, textvariable=self.coords_label_var, width=32).pack(**pad)
        ttk.Button(coords_frame, text="Leer estado ahora", command=self._on_read_now).pack(**pad)

        log_frame = ttk.LabelFrame(self, text="Registro")
        log_frame.grid(row=4, column=0, columnspan=2, sticky="ew", **pad)
        self.log_text = tk.Text(log_frame, height=8, width=90, state="disabled")
        self.log_text.pack(**pad)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _log(self, text):
        self.msg_queue.put(("log", text))

    def _run_async(self, fn, *args):
        threading.Thread(target=self._safe_call, args=(fn,) + args, daemon=True).start()

    def _safe_call(self, fn, *args):
        try:
            fn(*args)
        except Exception as exc:
            self._log(f"ERROR: {exc}")

    def _set_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for widget in (self.power_on_btn, self.power_off_btn, self.release_btn,
                       self.focus_btn, self.home_btn, self.stop_btn):
            widget.configure(state=state)
        self.connect_btn.configure(state="disabled" if enabled else "normal")
        self.disconnect_btn.configure(state="normal" if enabled else "disabled")

    def _process_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "log":
                    self.log_text.configure(state="normal")
                    self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {payload}\n")
                    self.log_text.see("end")
                    self.log_text.configure(state="disabled")
                elif kind == "status":
                    connected = payload
                    self.status_label.configure(
                        text="● Conectado" if connected else "● Desconectado",
                        foreground="green" if connected else "red",
                    )
                    self._set_controls_enabled(connected)
                elif kind == "angles":
                    for var, value in zip(self.angle_labels, payload):
                        var.set(f"{value:.1f}°")
                elif kind == "coords":
                    self.coords_label_var.set(", ".join(f"{v:.1f}" for v in payload))
                elif kind == "gripper":
                    self.gripper_label_var.set(str(payload))
        except queue.Empty:
            pass
        self.after(100, self._process_queue)

    # ------------------------------------------------------------------
    # Conexión
    # ------------------------------------------------------------------
    def _on_connect(self):
        port = self.port_entry.get().strip()
        try:
            baud = int(self.baud_entry.get().strip())
        except ValueError:
            self._log("Baudrate inválido.")
            return

        def do_connect():
            try:
                self.robot.connect(port, baud)
                self._log(f"Conectado a {port} @ {baud}")
                self.msg_queue.put(("status", True))
                self._start_polling()
            except Exception as exc:
                self._log(f"No se pudo conectar: {exc}")
                self.msg_queue.put(("status", False))

        threading.Thread(target=do_connect, daemon=True).start()

    def _on_disconnect(self):
        self._stop_polling()
        self.robot.disconnect()
        self._log("Desconectado.")
        self.msg_queue.put(("status", False))

    def _on_close(self):
        self._stop_polling()
        self.robot.disconnect()
        self.destroy()

    # ------------------------------------------------------------------
    # Motores
    # ------------------------------------------------------------------
    def _on_power_on(self):
        self._log("Power ON")
        self._run_async(self.robot.power_on)

    def _on_power_off(self):
        self._log("Power OFF")
        self._run_async(self.robot.power_off)

    def _on_release(self):
        self._log("Liberando servos (modo libre)")
        self._run_async(self.robot.release_servos)

    def _on_focus(self):
        self._log("Bloqueando servos")
        self._run_async(self.robot.focus_servos)

    def _on_home(self):
        self._log("Moviendo a posición Home")
        self._run_async(self.robot.send_angles, HOME_ANGLES, self.speed_var.get())

    def _on_stop(self):
        self._log("PARADA DE EMERGENCIA")
        self._run_async(self.robot.stop)

    # ------------------------------------------------------------------
    # Articulaciones y gripper
    # ------------------------------------------------------------------
    def _on_jog(self, joint_id, direction):
        step = self.step_var.get() * direction
        self._run_async(self.robot.jog_joint, joint_id, step, self.speed_var.get())

    def _on_gripper_set(self, value):
        self._run_async(self.robot.set_gripper, value, self.speed_var.get())

    def _on_gripper_step(self, direction):
        step = self.gripper_step_var.get() * direction

        def do_step():
            current = self.robot.get_gripper_value()
            if isinstance(current, (list, tuple)):
                current = current[0]
            self.robot.set_gripper(current + step, self.speed_var.get())

        self._run_async(do_step)

    def _on_read_now(self):
        self._run_async(self._read_state)

    # ------------------------------------------------------------------
    # Lectura periódica de estado
    # ------------------------------------------------------------------
    def _read_state(self):
        angles = self.robot.get_angles()
        if angles:
            self.msg_queue.put(("angles", angles))
        coords = self.robot.get_coords()
        if coords:
            self.msg_queue.put(("coords", coords))
        gripper = self.robot.get_gripper_value()
        if isinstance(gripper, (list, tuple)):
            gripper = gripper[0]
        if gripper is not None:
            self.msg_queue.put(("gripper", gripper))

    def _start_polling(self):
        self._poll_stop.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _stop_polling(self):
        self._poll_stop.set()

    def _poll_loop(self):
        while not self._poll_stop.is_set():
            if self.auto_update.get() and self.robot.connected:
                try:
                    self._read_state()
                except Exception as exc:
                    self._log(f"Error leyendo estado: {exc}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    app = JetcobotGUI()
    app.mainloop()
