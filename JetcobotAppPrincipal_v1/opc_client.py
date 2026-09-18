#!/usr/bin/env python3
# encoding: utf-8
"""
Cliente OPC UA robot <-> PLC S7-1500 (estación MPS Processing).

Mismo esquema que CHAUX/JetcobotOPCUA/robot_opcua_tester.py: hilo aparte para
no congelar la GUI, dos variables que el robot ESCRIBE (Robot_Listo,
Pieza_Recogida) y tres que el PLC ENVÍA y el robot LEE (Estacion_Lista,
Pieza_Lista, Orient_Salida).

Requisitos en la Jetson (Python 3.8):
    sudo apt install python3-tk
    pip3 install asyncua
"""

import queue
import threading

from asyncua.sync import Client
from asyncua import ua

DEFAULT_URL = "opc.tcp://192.168.20.20:4840"   # IP real del PLC
DEFAULT_NS = 3                                 # índice de namespace (confírmalo en UaExpert)
DEFAULT_USER = "robot"                         # usuario creado en el servidor OPC UA
DEFAULT_PASS = "Julian&Kate120909"             # contraseña de ese usuario

DB = "DB_Robot"
VARS = {
    # Robot -> PLC  (las escribe el robot / esta app)
    "Robot_Listo": "escribir",
    "Pieza_Recogida": "escribir",
    # PLC -> Robot  (las lee el robot / esta app)
    "Estacion_Lista": "leer",
    "Pieza_Lista": "leer",
    "Orient_Salida": "leer",
}


def node_id(ns, var):
    """Construye el NodeId estilo S7-1500:  ns=3;s="DB_Robot"."Variable" """
    return 'ns={};s="{}"."{}"'.format(ns, DB, var)


class OpcWorker(threading.Thread):
    """Todo el trabajo con el cliente OPC UA vive en este hilo, aparte de la GUI."""

    def __init__(self, cmd_q, status_q):
        super().__init__(daemon=True)
        self.cmd_q = cmd_q          # comandos que llegan de la GUI/secuencia
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
            # 1) escribir lo que el robot manda (siempre, para no depender de detectar cambios)
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
