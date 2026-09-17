#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
  Cliente OPC UA - Simulador del robot JetCobot  <->  PLC S7-1500
  Estación MPS Processing
-------------------------------------------------------------------------------
  - Interfaz gráfica (Tkinter) para probar el handshake con el PLC.
  - Campo para la dirección del servidor OPC UA + botón Conectar/Desconectar.
  - Dos interruptores que el robot ESCRIBE:   Robot_Listo, Pieza_Recogida
  - Tres pilotos que el PLC ENVÍA (se leen):   Estacion_Lista, Pieza_Lista,
                                               Orient_Salida
  - Terminal de log con el estado en tiempo real.

  Requisitos en la Jetson (Python 3.8):
      sudo apt install python3-tk
      pip3 install asyncua
===============================================================================
"""

import queue
import threading
import time
import tkinter as tk
from tkinter import scrolledtext

from asyncua.sync import Client
from asyncua import ua

# -----------------------------------------------------------------------------
# CONFIGURACIÓN POR DEFECTO  (ajústala a tu instalación)
# -----------------------------------------------------------------------------
DEFAULT_URL = "opc.tcp://192.168.20.20:4840"   # IP real del PLC
DEFAULT_NS  = 3                              # índice de namespace (confírmalo en UaExpert)
DEFAULT_USER = "robot"                       # usuario creado en el servidor OPC UA
DEFAULT_PASS = "Julian&Kate120909"                       # contraseña de ese usuario
POLL_MS = 200                                # cada cuánto se leen las variables del PLC

# Nombres de las variables dentro del DB_Robot
DB = "DB_Robot"
VARS = {
    # Robot -> PLC  (las escribe el robot / esta app)
    "Robot_Listo":     "escribir",
    "Pieza_Recogida":  "escribir",
    # PLC -> Robot  (las lee el robot / esta app)
    "Estacion_Lista":  "leer",
    "Pieza_Lista":     "leer",
    "Orient_Salida":   "leer",
}


def node_id(ns, var):
    """Construye el NodeId estilo S7-1500:  ns=3;s="DB_Robot"."Variable" """
    return 'ns={};s="{}"."{}"'.format(ns, DB, var)


# =============================================================================
#  HILO DE COMUNICACIÓN OPC UA
#  Todo el trabajo con el cliente vive en un hilo aparte para no congelar la GUI.
# =============================================================================
class OpcWorker(threading.Thread):
    def __init__(self, cmd_q, status_q):
        super().__init__(daemon=True)
        self.cmd_q = cmd_q          # comandos que llegan de la GUI
        self.status_q = status_q    # estado/log que se envía a la GUI
        self.client = None
        self.nodes = {}
        self.connected = False
        self.running = True
        # valores que el robot quiere escribir
        self.write_vals = {"Robot_Listo": False, "Pieza_Recogida": False}

    def log(self, msg):
        self.status_q.put(("log", msg))

    def set_conn(self, state):
        self.connected = state
        self.status_q.put(("conn", state))

    # --------------------------------------------------------------
    def run(self):
        while self.running:
            try:
                cmd = self.cmd_q.get(timeout=0.05)
            except queue.Empty:
                cmd = None

            if cmd is not None:
                kind = cmd[0]
                if kind == "connect":
                    self._connect(cmd[1], cmd[2], cmd[3], cmd[4])
                elif kind == "disconnect":
                    self._disconnect()
                elif kind == "write":
                    self.write_vals[cmd[1]] = cmd[2]
                elif kind == "quit":
                    self._disconnect()
                    self.running = False
                    break

            if self.connected:
                self._cycle()

    # --------------------------------------------------------------
    def _connect(self, url, ns, user, pwd):
        try:
            self.log("Conectando a %s ..." % url)
            self.client = Client(url)
            if user:
                self.client.set_user(user)
                self.client.set_password(pwd)
            self.client.connect()
            # crear referencias a los nodos
            self.nodes = {v: self.client.get_node(node_id(ns, v)) for v in VARS}
            # dejar las salidas del robot en un estado inicial conocido
            self.write_vals = {"Robot_Listo": False, "Pieza_Recogida": False}
            self._write_bool("Robot_Listo", False)
            self._write_bool("Pieza_Recogida", False)
            self.set_conn(True)
            self.log("Conectado. Namespace=%s" % ns)
        except Exception as e:
            self.log("ERROR al conectar: %s" % e)
            self.set_conn(False)
            try:
                if self.client:
                    self.client.disconnect()
            except Exception:
                pass
            self.client = None

    def _disconnect(self):
        if self.client:
            try:
                self.client.disconnect()
                self.log("Desconectado.")
            except Exception as e:
                self.log("Aviso al desconectar: %s" % e)
        self.client = None
        self.nodes = {}
        self.set_conn(False)

    # --------------------------------------------------------------
    def _write_bool(self, var, value):
        node = self.nodes[var]
        node.write_value(ua.DataValue(ua.Variant(bool(value), ua.VariantType.Boolean)))

    def _cycle(self):
        try:
            # 1) escribir lo que el robot manda (solo si cambió, para no saturar)
            for var in ("Robot_Listo", "Pieza_Recogida"):
                self._write_bool(var, self.write_vals[var])

            # 2) leer lo que el PLC envía
            reads = {}
            for var in ("Estacion_Lista", "Pieza_Lista", "Orient_Salida"):
                reads[var] = bool(self.nodes[var].read_value())
            self.status_q.put(("read", reads))

        except Exception as e:
            self.log("ERROR de comunicación: %s" % e)
            self._disconnect()


# =============================================================================
#  INTERFAZ GRÁFICA
# =============================================================================
class App:
    BG = "#1e1e2e"
    FG = "#e0e0e0"
    ACCENT = "#4c7dff"

    def __init__(self, root):
        self.root = root
        self.cmd_q = queue.Queue()
        self.status_q = queue.Queue()
        self.worker = OpcWorker(self.cmd_q, self.status_q)
        self.worker.start()

        root.title("Robot JetCobot - Cliente OPC UA (Simulador)")
        root.configure(bg=self.BG)
        root.geometry("620x640")

        self._build_conn_frame()
        self._build_switches_frame()
        self._build_leds_frame()
        self._build_log_frame()

        self.connected = False
        self._set_controls_state(False)
        self.root.after(100, self._poll_status)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- Conexión ----------
    def _build_conn_frame(self):
        f = tk.LabelFrame(self.root, text=" Conexión OPC UA ", bg=self.BG,
                          fg=self.ACCENT, font=("Arial", 10, "bold"), padx=8, pady=8)
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

        self.btn_conn = tk.Button(f, text="Conectar", width=14, command=self._toggle_conn,
                                  bg=self.ACCENT, fg="white", font=("Arial", 10, "bold"))
        self.btn_conn.grid(row=2, column=0, columnspan=2, pady=6, sticky="w")

        self.lbl_state = tk.Label(f, text="DESCONECTADO", bg=self.BG, fg="#ff6b6b",
                                  font=("Arial", 10, "bold"))
        self.lbl_state.grid(row=0, column=4, padx=10)

    # ---------- Interruptores (Robot -> PLC) ----------
    def _build_switches_frame(self):
        f = tk.LabelFrame(self.root, text=" El robot ESCRIBE (Robot -> PLC) ", bg=self.BG,
                          fg=self.ACCENT, font=("Arial", 10, "bold"), padx=8, pady=8)
        f.pack(fill="x", padx=10, pady=4)

        self.sw_robot = tk.BooleanVar(value=False)
        self.sw_recog = tk.BooleanVar(value=False)

        tk.Checkbutton(f, text="Robot_Listo", variable=self.sw_robot,
                       command=lambda: self._on_switch("Robot_Listo", self.sw_robot),
                       bg=self.BG, fg=self.FG, selectcolor="#333", activebackground=self.BG,
                       activeforeground=self.FG, font=("Arial", 11)).grid(row=0, column=0, padx=20, pady=4, sticky="w")

        tk.Checkbutton(f, text="Pieza_Recogida", variable=self.sw_recog,
                       command=lambda: self._on_switch("Pieza_Recogida", self.sw_recog),
                       bg=self.BG, fg=self.FG, selectcolor="#333", activebackground=self.BG,
                       activeforeground=self.FG, font=("Arial", 11)).grid(row=0, column=1, padx=20, pady=4, sticky="w")

    # ---------- Pilotos (PLC -> Robot) ----------
    def _build_leds_frame(self):
        f = tk.LabelFrame(self.root, text=" El PLC ENVÍA (PLC -> Robot) ", bg=self.BG,
                          fg=self.ACCENT, font=("Arial", 10, "bold"), padx=8, pady=8)
        f.pack(fill="x", padx=10, pady=4)

        self.leds = {}
        specs = [
            ("Estacion_Lista", "Estación lista\n(pide permiso)"),
            ("Pieza_Lista",    "Pieza en salida\n(recoger)"),
            ("Orient_Salida",  "Orientación\n(ON=mala)"),
        ]
        for i, (var, txt) in enumerate(specs):
            col = tk.Frame(f, bg=self.BG)
            col.grid(row=0, column=i, padx=22, pady=4)
            cv = tk.Canvas(col, width=54, height=54, bg=self.BG, highlightthickness=0)
            cv.pack()
            circ = cv.create_oval(6, 6, 48, 48, fill="#444", outline="#888", width=2)
            tk.Label(col, text=txt, bg=self.BG, fg=self.FG, font=("Arial", 9),
                     justify="center").pack()
            self.leds[var] = (cv, circ)

    # ---------- Terminal / Log ----------
    def _build_log_frame(self):
        f = tk.LabelFrame(self.root, text=" Registro / Estado ", bg=self.BG,
                          fg=self.ACCENT, font=("Arial", 10, "bold"), padx=6, pady=6)
        f.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.log = scrolledtext.ScrolledText(f, bg="#0c0c14", fg="#9dff9d",
                                             font=("Consolas", 9), height=12, state="disabled")
        self.log.pack(fill="both", expand=True)

    # =========================================================
    #  Acciones
    # =========================================================
    def _toggle_conn(self):
        if not self.connected:
            ns = int(self.ns_var.get().strip() or DEFAULT_NS)
            self.cmd_q.put(("connect", self.url_var.get().strip(), ns,
                            self.user_var.get().strip(), self.pass_var.get()))
        else:
            self.cmd_q.put(("disconnect",))

    def _on_switch(self, var, boolvar):
        val = bool(boolvar.get())
        self.cmd_q.put(("write", var, val))
        self._append("[TX] %s = %s" % (var, "TRUE" if val else "FALSE"))

    def _set_controls_state(self, connected):
        self.connected = connected
        if connected:
            self.btn_conn.config(text="Desconectar", bg="#ff6b6b")
            self.lbl_state.config(text="CONECTADO", fg="#4cd964")
        else:
            self.btn_conn.config(text="Conectar", bg=self.ACCENT)
            self.lbl_state.config(text="DESCONECTADO", fg="#ff6b6b")
            for var, (cv, circ) in self.leds.items():
                cv.itemconfig(circ, fill="#444")

    def _set_led(self, var, on):
        cv, circ = self.leds[var]
        if var == "Orient_Salida":
            color = "#ff6b6b" if on else "#4cd964"   # ON = mala (rojo)
        else:
            color = "#4cd964" if on else "#444"       # ON = verde
        cv.itemconfig(circ, fill=color)

    def _append(self, text):
        ts = time.strftime("%H:%M:%S")
        self.log.config(state="normal")
        self.log.insert("end", "%s  %s\n" % (ts, text))
        self.log.see("end")
        self.log.config(state="disabled")

    # =========================================================
    #  Bucle de refresco desde el hilo OPC
    # =========================================================
    def _poll_status(self):
        last_reads = None
        try:
            while True:
                kind, payload = self.status_q.get_nowait()
                if kind == "log":
                    self._append(payload)
                elif kind == "conn":
                    self._set_controls_state(payload)
                elif kind == "read":
                    for var, val in payload.items():
                        self._set_led(var, val)
                    last_reads = payload
        except queue.Empty:
            pass

        if last_reads is not None:
            self._last_reads = getattr(self, "_last_reads", {})
            for var, val in last_reads.items():
                if self._last_reads.get(var) != val:
                    self._append("[RX] %s = %s" % (var, "TRUE" if val else "FALSE"))
            self._last_reads = last_reads

        self.root.after(POLL_MS, self._poll_status)

    def _on_close(self):
        self.cmd_q.put(("quit",))
        self.root.after(200, self.root.destroy)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
