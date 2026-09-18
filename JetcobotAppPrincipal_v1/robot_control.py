#!/usr/bin/env python3
# encoding: utf-8
"""
Control del brazo JetCobot (MyCobot280) para la aplicación principal.

Mismo envoltorio (RobotController) que CHAUX/JetcobotControlGUI/panels/jetcobot_gui.py,
serializando el acceso al puerto serie con un lock, más las consultas de
"movimiento en curso" (is_moving / is_gripper_moving) que necesita la
secuencia automática para saber cuándo el robot llegó a una posición.
"""

import threading
import time

from pymycobot.mycobot280 import MyCobot280

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 1000000

HOME_ANGLES = [0, 0, 0, 0, 0, 45]

GRIPPER_MIN = 0
GRIPPER_MAX = 100


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
            # Fuerza el sistema de referencia a "base" (0), igual que en
            # jetcobot_gui.py: si quedara en "herramienta" (1) los envíos de
            # coordenadas guardadas no llegarían a donde se espera.
            try:
                mc.set_reference_frame(0)
            except Exception:
                pass
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

    def _call_lista(self, fn, largo_esperado, reintentos=5):
        """Como _call, pero valida que la respuesta sea la lista esperada.

        pymycobot a veces responde -1 en vez de la lista pedida cuando el bus
        serie está ocupado; -1 es "verdadero" en Python así que hay que
        revisar el tipo explícitamente. Devuelve None si tras reintentar no
        se obtiene una lista válida.
        """
        for _ in range(reintentos):
            resultado = self._call(fn)
            if isinstance(resultado, (list, tuple)) and len(resultado) == largo_esperado:
                return list(resultado)
            time.sleep(0.3)
        return None

    def get_angles(self):
        return self._call_lista(self.mc.get_angles, 6)

    def get_coords(self):
        return self._call_lista(self.mc.get_coords, 6)

    def get_gripper_value(self):
        resultado = self._call(self.mc.get_gripper_value)
        if isinstance(resultado, (int, float)) and resultado >= 0:
            return resultado
        return None

    def send_angles(self, angles, speed):
        self._call(self.mc.send_angles, angles, speed)

    def send_coords(self, coords, speed):
        self._call(self.mc.send_coords, coords, speed)

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

    def resume(self):
        self._call(self.mc.resume)

    def is_moving(self):
        return bool(self._call(self.mc.is_moving))

    def is_gripper_moving(self):
        return bool(self._call(self.mc.is_gripper_moving))

    def get_reference_frame(self):
        """0 = base (esperado), 1 = herramienta. None si no se pudo leer."""
        resultado = self._call(self.mc.get_reference_frame)
        return resultado if resultado in (0, 1) else None

    def set_reference_frame_base(self):
        self._call(self.mc.set_reference_frame, 0)


def wait_until_stopped(robot, timeout=30.0, poll=0.3, arranque=0.5):
    """Bloquea hasta que el brazo termine de moverse (o venza el timeout).

    `arranque` da tiempo a que el robot empiece a moverse antes de la
    primera consulta: is_moving() puede devolver False durante los primeros
    milisegundos, justo antes de que el firmware registre el movimiento.
    """
    time.sleep(arranque)
    limite = time.time() + timeout
    while time.time() < limite:
        if not robot.is_moving():
            return True
        time.sleep(poll)
    return False


def wait_until_gripper_stopped(robot, timeout=10.0, poll=0.2, arranque=0.3):
    time.sleep(arranque)
    limite = time.time() + timeout
    while time.time() < limite:
        if not robot.is_gripper_moving():
            return True
        time.sleep(poll)
    return False
