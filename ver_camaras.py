#!/usr/bin/env python3
"""Muestra las dos camaras USB (Microdia y Logitech C930) lado a lado."""
import cv2

DISPOSITIVOS = ["/dev/video0", "/dev/video2"]
ANCHO, ALTO = 640, 480

def abrir(dev):
    cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir {dev}")
    return cap

def main():
    caps = [abrir(d) for d in DISPOSITIVOS]
    ventana = "Camaras USB (q para salir)"
    cv2.namedWindow(ventana, cv2.WINDOW_NORMAL)
    try:
        while True:
            frames = []
            for dev, cap in zip(DISPOSITIVOS, caps):
                ok, frame = cap.read()
                if not ok:
                    frame = cv2.putText(
                        cv2.UMat(ALTO, ANCHO, cv2.CV_8UC3).get() * 0,
                        f"Sin senal: {dev}", (20, ALTO // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
                    )
                if frame.shape[:2] != (ALTO, ANCHO):
                    frame = cv2.resize(frame, (ANCHO, ALTO))
                frames.append(frame)
            combinada = cv2.hconcat(frames)
            cv2.imshow(ventana, combinada)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
    finally:
        for cap in caps:
            cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
