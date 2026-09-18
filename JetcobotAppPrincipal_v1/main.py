#!/usr/bin/env python3
# encoding: utf-8
"""
JetCobot - Aplicación principal v1

Integra en una sola interfaz:
  - La conexión y el movimiento del robot (robot_control.py, mismo
    RobotController que CHAUX/JetcobotControlGUI/panels/jetcobot_gui.py).
  - La comunicación OPC UA con el PLC (opc_client.py, mismo OpcWorker que
    CHAUX/JetcobotOPCUA/robot_opcua_tester.py).
  - La secuencia automática de la estación (secuencia.py).

No tiene botones de movimiento por articulación ni cartesiano: los
movimientos de trabajo (PosEncimaPieza, PosRecogerPieza, DejarPiezaDesecho)
los dispara únicamente la secuencia automática, usando las coordenadas
guardadas en data/posiciones_guardadas.json (copia propia de este proyecto).

Requisitos en la Jetson (Python 3.8):
    sudo apt install python3-tk
    pip3 install pymycobot asyncua
"""

import json
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext

from opc_client import (
    DEFAULT_NS,
    DEFAULT_PASS,
    DEFAULT_URL,
    DEFAULT_USER,
    OpcWorker,
)
from robot_control import (
    DEFAULT_BAUD,
    DEFAULT_PORT,
    HOME_ANGLES,
    RobotController,
    wait_until_stopped,
)
from secuencia import SequenceController

POSITIONS_FILE = Path(__file__).resolve().parent / "data" / "posiciones_guardadas.json"
POSICIONES_REQUERIDAS = ("PosEncimaPieza", "PosRecogerPieza", "DejarPiezaDesecho")

VEL_HOME_MANUAL = 50
POLL_MS = 200


def load_positions():
    if not POSITIONS_FILE.exists():
        return {}
    try:
        with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class App(tk.Tk):
    BG = "#1e1e2e"
    FG = "#e0e0e0"
    ACCENT = "#4c7dff"

    def __init__(self):
        super().__init__()
        self.title("JetCobot - Aplicación Principal v1")
        self.configure(bg=self.BG)
        self.geometry("760x820")

        # -------- estado compartido con la secuencia automática --------
        self.robot = RobotController()
        self.positions = load_positions()
        self.opcua_state = {"Estacion_Lista": False, "Pieza_Lista": False, "Orient_Salida": False}
        self.robot_connected = False
        self.opcua_connected = False
        self.homed = False

        self.msg_queue = queue.Queue()
        self.opc_cmd_q = queue.Queue()
        self.opc_status_q = queue.Queue()
        self.opc_worker = OpcWorker(self.opc_cmd_q, self.opc_status_q)
        self.opc_worker.start()

        self.sequence = SequenceController(self)

        self._build_ui()
        self._set_manual_controls_enabled(False)
        self._set_busy_controls_enabled(False)

        self._verificar_posiciones()
        self.sequence.start()

        self.after(100, self._poll_opcua)
        self.after(100, self._poll_msg_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ==================================================================
    # Construcción de la interfaz
    # ==================================================================
    def _build_ui(self):
        self._build_opcua_frame()
        self._build_robot_frame()
        self._build_estado_frame()
        self._build_leds_frame()
        self._build_log_frame()

    def _build_opcua_frame(self):
        f = tk.LabelFrame(self, text=" Conexión OPC UA ", bg=self.BG, fg=self.ACCENT,
                           font=("Arial", 10, "bold"), padx=8, pady=8)
        f.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(f, text="Servidor:", bg=self.BG, fg=self.FG).grid(row=0, column=0, sticky="e")
        self.url_var = tk.StringVar(value=DEFAULT_URL)
        tk.Entry(f, textvariable=self.url_var, width=34).grid(row=0, column=1, columnspan=3, sticky="w", padx=4)

        tk.Label(f, text="NS:", bg=self.BG, fg=self.FG).grid(row=1, column=0, sticky="e")
        self.ns_var = tk.StringVar(value=str(DEFAULT_NS))
        tk.Entry(f, textvariable=self.ns_var, width=5).grid(row=1, column=1, sticky="w", padx=4)

        tk.Label(f, text="Usuario:", bg=self.BG, fg=self.FG).grid(row=1, column=2, sticky="e")
        self.user_var = tk.StringVar(value=DEFAULT_USER)
        tk.Entry(f, textvariable=self.user_var, width=12).grid(row=1, column=3, sticky="w", padx=4)

        tk.Label(f, text="Clave:", bg=self.BG, fg=self.FG).grid(row=2, column=2, sticky="e")
        self.pass_var = tk.StringVar(value=DEFAULT_PASS)
        tk.Entry(f, textvariable=self.pass_var, width=12, show="*").grid(row=2, column=3, sticky="w", padx=4)

        self.btn_opcua = tk.Button(f, text="Conectar", width=14, command=self._toggle_opcua,
                                    bg=self.ACCENT, fg="white", font=("Arial", 10, "bold"))
        self.btn_opcua.grid(row=2, column=0, columnspan=2, pady=6, sticky="w")

        self.lbl_opcua = tk.Label(f, text="OPC UA: DESCONECTADO", bg=self.BG, fg="#ff6b6b",
                                   font=("Arial", 10, "bold"))
        self.lbl_opcua.grid(row=0, column=4, padx=10)

    def _build_robot_frame(self):
        f = tk.LabelFrame(self, text=" Conexión y control del robot ", bg=self.BG, fg=self.ACCENT,
                           font=("Arial", 10, "bold"), padx=8, pady=8)
        f.pack(fill="x", padx=10, pady=4)

        tk.Label(f, text="Puerto:", bg=self.BG, fg=self.FG).grid(row=0, column=0, sticky="e")
        self.port_var = tk.StringVar(value=DEFAULT_PORT)
        tk.Entry(f, textvariable=self.port_var, width=16).grid(row=0, column=1, sticky="w", padx=4)

        tk.Label(f, text="Baudrate:", bg=self.BG, fg=self.FG).grid(row=0, column=2, sticky="e")
        self.baud_var = tk.StringVar(value=str(DEFAULT_BAUD))
        tk.Entry(f, textvariable=self.baud_var, width=10).grid(row=0, column=3, sticky="w", padx=4)

        self.btn_robot = tk.Button(f, text="Conectar", width=14, command=self._toggle_robot,
                                    bg=self.ACCENT, fg="white", font=("Arial", 10, "bold"))
        self.btn_robot.grid(row=0, column=4, padx=6)

        self.lbl_robot = tk.Label(f, text="ROBOT: DESCONECTADO", bg=self.BG, fg="#ff6b6b",
                                   font=("Arial", 10, "bold"))
        self.lbl_robot.grid(row=0, column=5, padx=10)

        botones = tk.Frame(f, bg=self.BG)
        botones.grid(row=1, column=0, columnspan=6, pady=(8, 0), sticky="w")

        self.btn_power_on = tk.Button(botones, text="Activar servos", width=14, command=self._on_power_on)
        self.btn_power_on.grid(row=0, column=0, padx=4)
        self.btn_power_off = tk.Button(botones, text="Desactivar servos", width=14, command=self._on_power_off)
        self.btn_power_off.grid(row=0, column=1, padx=4)
        self.btn_focus = tk.Button(botones, text="Bloquear", width=10, command=self._on_focus)
        self.btn_focus.grid(row=0, column=2, padx=4)
        self.btn_release = tk.Button(botones, text="Liberar", width=10, command=self._on_release)
        self.btn_release.grid(row=0, column=3, padx=4)
        self.btn_home = tk.Button(botones, text="Ir a HOME", width=10, command=self._on_home,
                                   bg="#3a9d5d", fg="white")
        self.btn_home.grid(row=0, column=4, padx=4)

    def _build_estado_frame(self):
        f = tk.LabelFrame(self, text=" Estado de la secuencia ", bg=self.BG, fg=self.ACCENT,
                           font=("Arial", 10, "bold"), padx=8, pady=8)
        f.pack(fill="x", padx=10, pady=4)

        self.estado_var = tk.StringVar(value="Conecte el robot y el OPC UA, luego coloque el robot en HOME.")
        tk.Label(f, textvariable=self.estado_var, bg=self.BG, fg="#ffd166",
                 font=("Arial", 10, "bold"), wraplength=700, justify="left").pack(fill="x")

    def _build_leds_frame(self):
        f = tk.LabelFrame(self, text=" Pilotos ", bg=self.BG, fg=self.ACCENT,
                           font=("Arial", 10, "bold"), padx=8, pady=8)
        f.pack(fill="x", padx=10, pady=4)

        self.leds = {}
        specs = [
            ("Robot_Listo", "Robot_Listo\n(robot -> PLC)"),
            ("Pieza_Recogida", "Pieza_Recogida\n(robot -> PLC)"),
            ("Estacion_Lista", "Estacion_Lista\n(PLC -> robot)"),
            ("Pieza_Lista", "Pieza_Lista\n(PLC -> robot)"),
            ("Orient_Salida", "Orient_Salida\n(PLC -> robot)"),
        ]
        for i, (var, txt) in enumerate(specs):
            col = tk.Frame(f, bg=self.BG)
            col.grid(row=0, column=i, padx=16, pady=4)
            cv = tk.Canvas(col, width=48, height=48, bg=self.BG, highlightthickness=0)
            cv.pack()
            circ = cv.create_oval(5, 5, 43, 43, fill="#444", outline="#888", width=2)
            tk.Label(col, text=txt, bg=self.BG, fg=self.FG, font=("Arial", 9), justify="center").pack()
            self.leds[var] = (cv, circ)

    def _build_log_frame(self):
        f = tk.LabelFrame(self, text=" Registro / Secuencia de operaciones ", bg=self.BG, fg=self.ACCENT,
                           font=("Arial", 10, "bold"), padx=6, pady=6)
        f.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.log_widget = scrolledtext.ScrolledText(f, bg="#0c0c14", fg="#9dff9d",
                                                     font=("Consolas", 9), height=14, state="disabled")
        self.log_widget.pack(fill="both", expand=True)

    # ==================================================================
    # Conexión OPC UA
    # ==================================================================
    def _toggle_opcua(self):
        if not self.opcua_connected:
            try:
                ns = int(self.ns_var.get().strip() or DEFAULT_NS)
            except ValueError:
                self._log("NS inválido.")
                return
            self.opc_cmd_q.put(("connect", self.url_var.get().strip(), ns,
                                 self.user_var.get().strip(), self.pass_var.get()))
        else:
            self.opc_cmd_q.put(("disconnect",))

    # ==================================================================
    # Conexión y control del robot
    # ==================================================================
    def _toggle_robot(self):
        if not self.robot_connected:
            port = self.port_var.get().strip()
            try:
                baud = int(self.baud_var.get().strip())
            except ValueError:
                self._log("Baudrate inválido.")
                return
            threading.Thread(target=self._hacer_conectar_robot, args=(port, baud), daemon=True).start()
        else:
            self.robot.disconnect()
            self.robot_connected = False
            self.homed = False
            self.sequence.forzar_espera_home()
            self.msg_queue.put(("conn_robot", False))
            self._log("Robot desconectado.")

    def _hacer_conectar_robot(self, port, baud):
        try:
            self.robot.connect(port, baud)
            self.homed = False
            self.sequence.forzar_espera_home()
            self.msg_queue.put(("conn_robot", True))
            self._log(f"Robot conectado en {port} @ {baud}.")
            self.set_estado("Robot conectado. Coloque el robot en HOME para iniciar el ciclo.")
        except Exception as exc:
            self._log(f"No se pudo conectar el robot: {exc}")
            self.msg_queue.put(("conn_robot", False))

    def _on_power_on(self):
        self._log("Activando servos (Power ON).")
        self._run_async(self.robot.power_on)

    def _on_power_off(self):
        self._log("Desactivando servos (Power OFF).")
        self.homed = False
        self.sequence.forzar_espera_home()
        self.set_estado("Servos desactivados. Coloque el robot en HOME antes de reanudar.")
        self._run_async(self.robot.power_off)

    def _on_focus(self):
        self._log("Bloqueando servos.")
        self._run_async(self.robot.focus_servos)

    def _on_release(self):
        self._log("Liberando servos (modo libre). El brazo puede moverse a mano.")
        self.homed = False
        self.sequence.forzar_espera_home()
        self.set_estado("Servos liberados. Coloque el robot en HOME antes de reanudar.")
        self._run_async(self.robot.release_servos)

    def _on_home(self):
        if not self.robot_connected:
            self._log("Conecte el robot antes de ir a HOME.")
            return
        self._log("Enviando robot a HOME...")
        self.msg_queue.put(("busy", True))
        threading.Thread(target=self._hacer_home, daemon=True).start()

    def _hacer_home(self):
        try:
            self.robot.send_angles(HOME_ANGLES, VEL_HOME_MANUAL)
            if wait_until_stopped(self.robot):
                self.homed = True
                self._log("Robot en HOME.")
                self.set_estado("Robot en HOME. Esperando Estacion_Lista para iniciar el ciclo.")
            else:
                self._log("Tiempo agotado esperando a que el robot llegue a HOME.")
        except Exception as exc:
            self._log(f"ERROR yendo a HOME: {exc}")
        finally:
            self.msg_queue.put(("busy", False))

    def _run_async(self, fn, *args):
        def hacerlo():
            try:
                fn(*args)
            except Exception as exc:
                self._log(f"ERROR: {exc}")
        threading.Thread(target=hacerlo, daemon=True).start()

    # ==================================================================
    # Interfaz usada por SequenceController (se llama desde su propio hilo)
    # ==================================================================
    def log(self, msg):
        self._log(msg)

    def opcua_write(self, var, value):
        value = bool(value)
        self.opc_cmd_q.put(("write", var, value))
        self.msg_queue.put(("tx", (var, value)))

    def set_busy(self, busy):
        self.msg_queue.put(("busy", busy))

    def set_estado(self, texto):
        self.msg_queue.put(("estado", texto))

    # ==================================================================
    # Posiciones guardadas
    # ==================================================================
    def _verificar_posiciones(self):
        faltantes = [n for n in POSICIONES_REQUERIDAS if n not in self.positions]
        if faltantes:
            self._log(f"AVISO: faltan posiciones guardadas en {POSITIONS_FILE.name}: {', '.join(faltantes)}")
        else:
            self._log(f"Posiciones cargadas desde {POSITIONS_FILE}.")

    # ==================================================================
    # Helpers de UI
    # ==================================================================
    def _log(self, text):
        self.msg_queue.put(("log", text))

    def _append_log(self, text):
        ts = time.strftime("%H:%M:%S")
        self.log_widget.config(state="normal")
        self.log_widget.insert("end", "%s  %s\n" % (ts, text))
        self.log_widget.see("end")
        self.log_widget.config(state="disabled")

    def _set_manual_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for btn in (self.btn_power_on, self.btn_power_off, self.btn_focus, self.btn_release, self.btn_home):
            btn.configure(state=state)

    def _set_busy_controls_enabled(self, enabled):
        """Deshabilita los controles manuales del robot mientras hay un
        movimiento en curso (manual a HOME o ciclo automático), para no
        mandar dos comandos de movimiento a la vez."""
        if not self.robot_connected:
            return  # ya están deshabilitados por _set_manual_controls_enabled(False)
        state = "normal" if enabled else "disabled"
        for btn in (self.btn_power_on, self.btn_power_off, self.btn_focus, self.btn_release, self.btn_home):
            btn.configure(state=state)

    def _set_led(self, var, on):
        cv, circ = self.leds[var]
        if var == "Orient_Salida":
            color = "#ff6b6b" if on else "#444"   # solo se enciende (rojo) si la orientación es mala
        else:
            color = "#4cd964" if on else "#444"
        cv.itemconfig(circ, fill=color)

    # ==================================================================
    # Colas de mensajes (todo lo que toca widgets pasa por acá, en el hilo de Tk)
    # ==================================================================
    def _poll_opcua(self):
        last_reads = None
        try:
            while True:
                kind, payload = self.opc_status_q.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "conn":
                    self.opcua_connected = payload
                    if payload:
                        self.lbl_opcua.config(text="OPC UA: CONECTADO", fg="#4cd964")
                        self.btn_opcua.config(text="Desconectar", bg="#ff6b6b")
                    else:
                        self.lbl_opcua.config(text="OPC UA: DESCONECTADO", fg="#ff6b6b")
                        self.btn_opcua.config(text="Conectar", bg=self.ACCENT)
                        for var in ("Estacion_Lista", "Pieza_Lista", "Orient_Salida"):
                            self.opcua_state[var] = False
                            self._set_led(var, False)
                elif kind == "read":
                    for var, val in payload.items():
                        self.opcua_state[var] = val
                        self._set_led(var, val)
                    last_reads = payload
        except queue.Empty:
            pass

        if last_reads is not None:
            self._last_reads = getattr(self, "_last_reads", {})
            for var, val in last_reads.items():
                if self._last_reads.get(var) != val:
                    self._append_log("[RX] %s = %s" % (var, "TRUE" if val else "FALSE"))
            self._last_reads = last_reads

        self.after(POLL_MS, self._poll_opcua)

    def _poll_msg_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "conn_robot":
                    self.robot_connected = payload
                    if payload:
                        self.lbl_robot.config(text="ROBOT: CONECTADO", fg="#4cd964")
                        self.btn_robot.config(text="Desconectar", bg="#ff6b6b")
                        self._set_manual_controls_enabled(True)
                    else:
                        self.lbl_robot.config(text="ROBOT: DESCONECTADO", fg="#ff6b6b")
                        self.btn_robot.config(text="Conectar", bg=self.ACCENT)
                        self._set_manual_controls_enabled(False)
                        for var in ("Robot_Listo", "Pieza_Recogida"):
                            self._set_led(var, False)
                elif kind == "tx":
                    var, val = payload
                    self._set_led(var, val)
                    self._append_log("[TX] %s = %s" % (var, "TRUE" if val else "FALSE"))
                elif kind == "busy":
                    self._set_busy_controls_enabled(not payload)
                elif kind == "estado":
                    self.estado_var.set(payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_msg_queue)

    # ==================================================================
    def _on_close(self):
        self.sequence.stop()
        self.opc_cmd_q.put(("quit",))
        self.robot.disconnect()
        self.after(200, self.destroy)


if __name__ == "__main__":
    app = App()
    app.mainloop()
