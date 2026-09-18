#!/usr/bin/env python3
# encoding: utf-8
"""
Secuencia automática de la aplicación principal: coordina los movimientos del
JetCobot (robot_control.py) con el handshake OPC UA (opc_client.py) según el
ciclo de la estación MPS Processing.

Ciclo (una vez el robot está en HOME y las dos conexiones activas):
  1. Espera Estacion_Lista = TRUE.
  2. Va a PosEncimaPieza y abre el gripper (velocidad 50).
  3. Al llegar, avisa Robot_Listo = TRUE.
  4. Espera Pieza_Lista = TRUE (mientras tanto se muestra Orient_Salida en el piloto).
  5. Va a PosRecogerPieza (velocidad 12), cierra el gripper, vuelve a
     PosEncimaPieza (velocidad 12) y avisa Robot_Listo = FALSE.
  6. Va a HOME (velocidad 50) y avisa Pieza_Recogida = TRUE.
  7. Pasa por PosSeguraDejar (velocidad 50) y va a DejarPiezaDesecho
     (velocidad 50), abre el gripper y avisa Pieza_Recogida = FALSE.
  8. Vuelve a HOME (velocidad 50) y queda a la espera de Estacion_Lista.

Cualquier error o pérdida de conexión durante el ciclo obliga a volver a
pasar por HOME antes de reintentar (no se asume dónde quedó el brazo).
"""

import threading
import time

from robot_control import (
    GRIPPER_MAX,
    GRIPPER_MIN,
    HOME_ANGLES,
    wait_until_gripper_stopped,
    wait_until_stopped,
)

VEL_ESPERA = 50
VEL_RECOGIDA = 12
VEL_DESECHO = 50
VEL_HOME = 50

POS_ENCIMA = "PosEncimaPieza"
POS_RECOGER = "PosRecogerPieza"
POS_SEGURA_DEJAR = "PosSeguraDejar"
POS_DESECHO = "DejarPiezaDesecho"

ESPERANDO_HOME = "esperando_home"
ESPERANDO_ESTACION = "esperando_estacion"
EJECUTANDO = "ejecutando"


class SequenceController(threading.Thread):
    """Hilo dedicado a la secuencia automática. Usa la instancia `app`
    (ver main.py) para leer/escribir estado y no bloquear jamás el hilo de Tk."""

    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        self.running = True
        self.state = ESPERANDO_HOME
        self._prev_estacion = False
        self._prev_pieza = False

    def stop(self):
        self.running = False

    def forzar_espera_home(self):
        """El robot dejó de estar en una posición conocida (se desconectó,
        hubo un error, o el operador acaba de conectar): hay que rehacer HOME
        antes de dejar que el ciclo automático vuelva a moverlo."""
        self.state = ESPERANDO_HOME
        self._prev_estacion = False
        self._prev_pieza = False

    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            time.sleep(0.15)

            if not (self.app.robot_connected and self.app.opcua_connected):
                continue

            if self.state == ESPERANDO_HOME:
                if self.app.homed:
                    self.state = ESPERANDO_ESTACION
                    self.app.set_estado("Esperando Estacion_Lista para iniciar el ciclo.")
                    self.app.log("Robot en HOME. Esperando Estacion_Lista para iniciar el ciclo.")
                continue

            if self.state == ESPERANDO_ESTACION:
                estacion = bool(self.app.opcua_state.get("Estacion_Lista", False))
                if estacion and not self._prev_estacion:
                    self._prev_estacion = estacion
                    self._ejecutar_ciclo()
                else:
                    self._prev_estacion = estacion
                continue

    # ------------------------------------------------------------------
    def _ejecutar_ciclo(self):
        app = self.app
        self.state = EJECUTANDO
        app.set_busy(True)
        try:
            app.log("Estacion_Lista=TRUE. Yendo a PosEncimaPieza y abriendo gripper...")
            app.set_estado("Ejecutando ciclo: yendo a PosEncimaPieza...")
            self._mover_a(POS_ENCIMA, VEL_ESPERA)
            self._gripper(GRIPPER_MAX, VEL_ESPERA)

            app.log("En posición. Robot_Listo=TRUE")
            app.opcua_write("Robot_Listo", True)

            app.set_estado("Esperando Pieza_Lista (ver Orient_Salida)...")
            if not self._esperar_pieza_lista():
                return

            app.log("Pieza_Lista=TRUE. Yendo a recoger la pieza...")
            app.set_estado("Ejecutando ciclo: recogiendo pieza...")
            self._mover_a(POS_RECOGER, VEL_RECOGIDA)
            self._gripper(GRIPPER_MIN, VEL_RECOGIDA)
            self._mover_a(POS_ENCIMA, VEL_RECOGIDA)

            app.log("Robot_Listo=FALSE")
            app.opcua_write("Robot_Listo", False)

            app.set_estado("Ejecutando ciclo: volviendo a HOME...")
            self._mover_home(VEL_HOME)

            app.log("Pieza_Recogida=TRUE")
            app.opcua_write("Pieza_Recogida", True)

            app.set_estado("Ejecutando ciclo: pasando por posición segura...")
            self._mover_a(POS_SEGURA_DEJAR, VEL_DESECHO)

            app.set_estado("Ejecutando ciclo: dejando pieza en desecho...")
            self._mover_a(POS_DESECHO, VEL_DESECHO)
            self._gripper(GRIPPER_MAX, VEL_DESECHO)

            app.log("Pieza_Recogida=FALSE")
            app.opcua_write("Pieza_Recogida", False)

            app.set_estado("Ejecutando ciclo: volviendo a HOME...")
            self._mover_home(VEL_HOME)

            app.log("Ciclo completo. Esperando Estacion_Lista para reiniciar.")
            app.set_estado("Ciclo completo. Esperando Estacion_Lista para reiniciar.")
            self.state = ESPERANDO_ESTACION
            self._prev_estacion = bool(app.opcua_state.get("Estacion_Lista", False))

        except Exception as exc:
            app.log(f"ERROR en la secuencia automática: {exc}")
            app.log("Verifique el robot y vuelva a llevarlo a HOME antes de continuar.")
            app.homed = False
            self.forzar_espera_home()
            app.set_estado("ERROR en el ciclo. Coloque el robot en HOME para reintentar.")
        finally:
            app.set_busy(False)

    # ------------------------------------------------------------------
    def _esperar_pieza_lista(self):
        """Bloquea hasta ver el flanco de subida de Pieza_Lista.

        Devuelve False (y aborta el ciclo forzando re-home) si se pierde
        alguna conexión mientras se espera.
        """
        app = self.app
        self._prev_pieza = bool(app.opcua_state.get("Pieza_Lista", False))
        while self.running:
            time.sleep(0.15)
            if not (app.robot_connected and app.opcua_connected):
                app.log("Conexión perdida esperando Pieza_Lista. Cancelando ciclo.")
                app.homed = False
                self.forzar_espera_home()
                app.set_estado("Conexión perdida. Coloque el robot en HOME para reintentar.")
                return False
            pieza = bool(app.opcua_state.get("Pieza_Lista", False))
            if pieza and not self._prev_pieza:
                self._prev_pieza = pieza
                return True
            self._prev_pieza = pieza
        return False

    # ------------------------------------------------------------------
    def _mover_a(self, nombre_posicion, velocidad):
        coords = self.app.positions.get(nombre_posicion)
        if coords is None:
            raise RuntimeError(f"No existe la posición guardada '{nombre_posicion}'.")
        self.app.robot.send_coords(coords, velocidad)
        if not wait_until_stopped(self.app.robot):
            raise RuntimeError(f"Tiempo de espera agotado moviéndose a '{nombre_posicion}'.")

    def _mover_home(self, velocidad):
        self.app.robot.send_angles(HOME_ANGLES, velocidad)
        if not wait_until_stopped(self.app.robot):
            raise RuntimeError("Tiempo de espera agotado moviéndose a HOME.")

    def _gripper(self, valor, velocidad):
        self.app.robot.set_gripper(valor, velocidad)
        wait_until_gripper_stopped(self.app.robot)
