from asyncua.sync import Client
import time
# from pymycobot import MyCobot   # API del brazo del JetCobot

PLC = "opc.tcp://192.168.20.20:4840"     # IP real del PLC
USER, PWD = "robot", "Julian&Kate120909"    # el usuario que creaste en el Paso 1

def nid(s): return f'ns=3;s={s}'         # confirma el ns con UaExpert
N_LISTA   = nid('"DB_Robot"."Pieza_Lista"')
N_RECOG   = nid('"DB_Robot"."Pieza_Recogida"')
N_LISTO   = nid('"DB_Robot"."Robot_Listo"')
N_ORIENT  = nid('"DB_Robot"."Orient_Salida"')

client = Client(PLC)
client.set_user(USER); client.set_password(PWD)
client.connect()
try:
    lista  = client.get_node(N_LISTA)
    recog  = client.get_node(N_RECOG)
    listo  = client.get_node(N_LISTO)
    orient = client.get_node(N_ORIENT)

    listo.write_value(True)      # robot en home, disponible
    recog.write_value(False)

    while True:
        if lista.read_value():                 # PLC: hay pieza en la salida
            mala = orient.read_value()          # True = defectuosa
            listo.write_value(False)

            # ---- rutina del brazo (tus posiciones) ----
            # mc.send_coords(pos_salida, vel); cerrar_pinza()
            # mc.send_coords(bin_malo if mala else bin_bueno, vel); abrir_pinza()
            # mc.send_coords(pos_home, vel)
            # -------------------------------------------

            recog.write_value(True)             # aviso: ya la recogí
            while lista.read_value():            # espera a que el PLC baje Pieza_Lista
                time.sleep(0.05)
            recog.write_value(False)            # cierra el handshake
            listo.write_value(True)             # de nuevo disponible
        time.sleep(0.05)
finally:
    client.disconnect()