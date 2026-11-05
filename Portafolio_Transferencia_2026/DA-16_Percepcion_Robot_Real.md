# Documento de Apoyo No. DA-16 – Práctica: percepción con el robot real – cámara, calibración mano-ojo, detección y despliegue de YOLO con TensorRT.

> Versión en Markdown del documento de apoyo, para consultar y copiar comandos desde GitHub. El documento de Word (formato GFPI-F-135) no se publica en el repositorio.

**Actividad de Aprendizaje:** Integrar la cámara del robot en la Jetson, calibrar la relación mano-ojo real, localizar objetos con el robot real y desplegar el detector YOLO con TensorRT, cuantificando la exactitud frente a los resultados obtenidos en simulación.

**Parte de la transferencia:** Parte B – Robot real con la Jetson AGX Orin.

**Equipo de trabajo:** Jetson AGX Orin conectada al JetCobot (y a la cámara) + PC en la misma red y con el mismo ROS\_DOMAIN\_ID.

**Duración Estimada:** 2,5 horas.

**Sesión:** Día 4 – 06/11/2026, 9:00 a.m. – 11:30 a.m.

**Relación con la Guía de Aprendizaje:** Actividad 3.4.6 (transferencia).

> **PARTE B · TRABAJO CON EL ROBOT (JETSON AGX ORIN + JETCOBOT):**
>
> Este documento se trabaja con la **Jetson AGX Orin** conectada al JetCobot y con el **PC** en la misma red. Cada bloque de comandos indica dónde se ejecuta: **Terminal (Jetson)** o **Terminal (PC)**. Requisito: haber completado la Parte A en simulación (DA-02 a DA-12).

## 1. OBJETIVOS DE APRENDIZAJE

- Publicar la cámara montada en el robot desde la Jetson y visualizarla en el PC sin saturar la red.
- Recalibrar los perfiles HSV con la cámara del robot y la iluminación del puesto de trabajo.
- Calibrar la relación mano-ojo con el robot real y validarla con una medición independiente.
- Medir exactitud, repetibilidad y latencia de la localización real y compararlas con la simulación (DA-10).
- Exportar el detector YOLO de la Parte A a TensorRT en la Jetson y usarlo como nodo ROS 2 de la celda.

## 2. FUNDAMENTOS: QUÉ CAMBIA RESPECTO A LA SIMULACIÓN

La teoría de esta práctica se estudió en la Parte A: modelo de cámara y calibraciones (DA-09), localización por intersección del rayo con el plano de la mesa (DA-10) y aprendizaje profundo (DA-11). En simulación la cámara estaba perfectamente calibrada y su pose era exacta; con el robot real se suman errores independientes de los intrínsecos (ε\_K), de la calibración mano-ojo (ε\_X), de la cinemática del robot (ε\_q) y de la altura supuesta de la pieza (ε\_z). Si son independientes, una estimación del error total es:

$${ε}_{total}≈\sqrt{{ε}_{K}^{2}+{ε}_{X}^{2}+{ε}_{q}^{2}+{ε}_{z}^{2}} \qquad (1)$$

La comparación entre la Tabla 3 de DA-10 (simulación) y la Tabla 4 de este documento (robot real) permite estimar cuánto aporta cada fuente y decidir qué calibración mejorar primero.

*Tabla 1. Cambios de la percepción al pasar al robot real.*

| **Elemento** | **Parte A (simulación)** | **Parte B (este documento)** |
|---|---|---|
| Imagen | `/wrist_camera/image_raw` (Gazebo) | `/camera/image_raw` publicada por `camera_node` en la Jetson |
| Marco de la cámara | `camera_optical_frame` (exacto) | `camera_calibrated_optical` (calibración mano-ojo real) |
| Perfiles HSV | Colores de Gazebo | Recalibrados con la cámara del robot (Paso 2) |
| Detector YOLO | `best.pt` en el PC | `best.engine` (TensorRT FP16) en la Jetson (Paso 7) |

## 3. MATERIALES

- Celda real funcionando (DA-13 y DA-14) con la cámara USB montada en la mano del robot y conectada a la Jetson.
- Tablero de ajedrez y marcador ArUco id 7 de 30 mm impresos (DA-09); regla o plantilla con 5 posiciones marcadas.
- Piezas de colores y frutas reales; el modelo `best.pt` entrenado en DA-11.

## 4. PROCEDIMIENTO PASO A PASO

### Paso 0. Actualizar robots_ws

Antes de empezar, traiga lo nuevo del repositorio robots\_ws y vuelva a compilar, en la Jetson y en el PC:

**Terminal (Jetson y PC)**

```bash
# trae lo nuevo del repositorio (correcciones y mejoras)
cd ~/robots_ws && git pull
colcon build --symlink-install
source install/setup.bash
```

### Paso 1. Cámara del robot en la Jetson

Si la cámara es la misma que calibró en DA-09 conectándola al PC, copie su `camera_info.yaml` a `~/robots_ws/src/jc_vision/config/` en la Jetson y recompile `jc_vision`. Si es otra cámara, calíbrela primero conectándola temporalmente al PC (DA-09, Paso 2).

**Terminal (Jetson, por SSH + tmux)**

```bash
ros2 launch jc_bringup real.launch.py port:=/dev/ttyUSB0 camera:=true rviz:=false compress:=true
```

**Terminal (PC)**

```bash
ros2 topic hz /camera/image_raw/compressed
ros2 run rqt_image_view rqt_image_view /camera/image_raw/compressed
ros2 service call /jc/move_to_named jc_interfaces/srv/MoveToNamed "{name: observe}"
```

> **Precaución:**
>
> En el PC visualice siempre la imagen **comprimida**: la imagen sin comprimir a 30 FPS ocupa ≈ 221 Mbit/s (DA-13). Los nodos que procesan la imagen completa (detectores, calibración) corren en la Jetson.

### Paso 2. Perfiles HSV con la cámara del robot

1. Relance la celda **sin** cámara (`camera:=false`) para liberar `/dev/video0` y lleve el robot a `observe`.
1. En la Jetson (monitor local o VNC, DA-13), ejecute `python3 ~/robots_ws/practicas/dia2_vision/cv_03_segmentacion.py --fuente /dev/video0 --nombre rojo` y repita para verde y azul, como en DA-08.
1. Copie los rangos a `~/robots_ws/src/jc_vision/config/hsv_profiles.yaml` en la Jetson, recompile `jc_vision` y registre los perfiles en Git (`mi_celda`) para no perderlos.

### Paso 3. Calibración mano-ojo con el robot real

1. Fije el marcador ArUco id 7 (30 mm) a la mesa dentro de la zona alcanzable y visible desde `observe`.
1. Con la celda lanzada con cámara (Paso 1), ejecute el nodo **en la Jetson** (procesa la imagen completa):`ros2 run jc_vision handeye_calibration --ros-args -p base_frame:=base_link -p gripper_frame:=link6_flange -p marker_length:=0.030 -p output_file:=$HOME/robots_ws/src/jc_vision/config/handeye_result.yaml`
1. Desde el **PC**, mueva el robot con RViz2/MoveIt a ≥ 12 poses que varíen J4, J5 y J6 en 15–40° manteniendo el marcador visible y a 20–35 cm. En cada pose, **espere 3 s** y capture desde el PC:`ros2 service call /handeye_calibration/capture std_srvs/srv/Trigger`
1. Calcule: `ros2 service call /handeye_calibration/compute std_srvs/srv/Trigger`. El registro muestra los 5 métodos.
1. En la Jetson, recompile `jc_vision` y publique la TF calibrada: `ros2 launch jc_bringup real.launch.py camera:=true handeye:=true rviz:=false compress:=true`.

> **Resultado esperado:**
>
> Archivo `handeye_result.yaml` con `parent_frame: link6_flange`, `child_frame: camera_calibrated_optical`, traslación, cuaternión, método, número de muestras y dispersión. Valores coherentes con la medición física del Paso 8 de DA-14 (≈ 36 mm entre pinza y cámara) y dispersión ≤ 5 mm.

*Tabla 2. Resultados de la calibración mano-ojo con el robot real (diligenciar).*

| **Método** | **t [mm]** | **Dispersión media [mm]** | **Dispersión máx. [mm]** | **Diferencia con la simulación (DA-09)** |
|---|---|---|---|---|
| TSAI |  |  |  |  |
| PARK |  |  |  |  |
| HORAUD |  |  |  |  |
| ANDREFF |  |  |  |  |
| DANIILIDIS |  |  |  |  |

Con el robot real no se conoce la transformación verdadera: la **dispersión** y la validación del Paso 4 son las únicas medidas de calidad. Como se vio en DA-09, dispersión baja no garantiza exactitud. Alternativa con interfaz gráfica: `easy_handeye2` [7].

### Paso 4. Validación independiente de la calibración

Con la TF calibrada activa, ubique el marcador ArUco en otra posición, obtenga su pose (Paso 5) y lleve el TCP 1 cm por encima del centro detectado con `/jc/move_to_pose` (escalado ≤ 0,2). Mida con regla el error horizontal en 5 posiciones distintas y reporte media y máximo.

*Tabla 3. Validación independiente de la calibración mano-ojo (diligenciar).*

| **Posición** | **Error horizontal medido [mm]** |
|---|---|
| V1 |  |
| V2 |  |
| V3 |  |
| V4 |  |
| V5 |  |
| Media / máximo |  |

### Paso 5. Detección y localización con el robot real

**Terminal (Jetson)**

```bash
ros2 launch jc_vision vision.launch.py mode:=real detector:=clasico camera_frame:=camera_calibrated_optical
```

**Terminal (PC)**

```bash
ros2 topic echo /jc/detections --once
ros2 run rqt_image_view rqt_image_view /jc/debug_image/compressed
```

Mida la exactitud y la repetibilidad con el mismo protocolo de DA-10 (Paso 3), ahora con posiciones marcadas en la mesa real (plantilla impresa o regla): 50 detecciones por posición, error medio y desviación estándar. Repita con el marco nominal `camera_frame:=camera_optical_frame` para cuantificar el aporte de la calibración.

*Tabla 4. Exactitud y repetibilidad con el robot real comparadas con la simulación (diligenciar).*

| **Posición** | **Real (x, y) [mm]** | **Error con mano-ojo [mm]** | **σ [mm]** | **Error con marco nominal [mm]** | **Error en Gazebo (DA-10) [mm]** |
|---|---|---|---|---|---|
| P1 |  |  |  |  |  |
| P2 |  |  |  |  |  |
| P3 |  |  |  |  |  |
| P4 |  |  |  |  |  |
| P5 |  |  |  |  |  |

Con la ecuación (1), estime qué fuente de error domina y proponga la siguiente acción de mejora (recalibrar intrínsecos, repetir mano-ojo, ajustar `plane_z`). Mida también la latencia captura → detección (`header.stamp` frente al reloj de recepción) y compárela con la obtenida en simulación.

### Paso 6. Entorno de aprendizaje profundo en la Jetson

Las ruedas de PyTorch de PyPI no están compiladas para la GPU de Jetson. Siga la guía de Ultralytics para NVIDIA Jetson [8]; para JetPack 6 indica (consulta: octubre de 2026) instalar `ultralytics` y luego reemplazar torch/torchvision por ruedas aarch64 compiladas para JetPack 6 (Python 3.10), además de `onnxruntime-gpu`. Verifique la versión de TensorRT del sistema (10.3 en JetPack 6.2 [10]):

**Terminal (Jetson)**

```bash
sudo apt update && sudo apt install -y python3-pip && pip install -U pip
pip install ultralytics
# Reemplazar torch/torchvision por las ruedas para JetPack 6 indicadas en la guía vigente de Ultralytics, p. ej.:
# pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torch-2.10.0-cp310-cp310-linux_aarch64.whl
# pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.25.0-cp310-cp310-linux_aarch64.whl
# debe imprimir True
python3 -c "import torch; print(torch.__version__, torch.cuda.is_available())"
# 10.x
python3 -c "import tensorrt; print(tensorrt.__version__)"
```

> **Precaución:**
>
> Las URL de las ruedas cambian con cada versión. Consulte la guía oficial el día de la instalación y anote en la bitácora las versiones exactas (`pip list | grep -E 'torch|ultralytics'`): es parte de la reproducibilidad del experimento.

### Paso 7. Exportar a TensorRT y desplegar el detector

Copie `best.pt` (entrenado en el PC en DA-11) a la Jetson, por ejemplo con `scp`, y expórtelo **en la Jetson**: los motores TensorRT son específicos del dispositivo y de la versión.

**Terminal (Jetson)**

```bash
cd ~/robots_ws/practicas/dia3_deep_learning
# -> best.engine (FP16)
python3 dl_03_yolo_entrenar.py --exportar ~/best.pt --imgsz 640
yolo benchmark model=$HOME/best.pt data=frutas.yaml imgsz=640 half=True device=0
```

Ultralytics reporta para YOLO26n en una AGX Orin **64 GB** tiempos de inferencia de ≈ 11,6 ms (PyTorch) y ≈ 2,6 ms (TensorRT FP16) por imagen, sin pre/posprocesamiento [8], [9]. Mida y reporte sus propios valores en la AGX Orin 32 GB:

*Tabla 5. Comparación de formatos en la Jetson AGX Orin 32 GB (diligenciar).*

| **Formato** | **Tamaño [MB]** | **mAP50-95** | **Inferencia [ms/img]** | **FPS de extremo a extremo (nodo ROS)** |
|---|---|---|---|---|
| PyTorch (.pt) |  |  |  |  |
| ONNX |  |  |  |  |
| TensorRT FP16 (.engine) |  |  |  |  |

**Terminal (Jetson)**

```bash
ros2 run jc_vision yolo_detector --ros-args -p model:=$HOME/best.engine -p conf:=0.5 \
     -p image_topic:=/camera/image_raw -p camera_info_topic:=/camera/camera_info \
     -p camera_frame:=camera_calibrated_optical -p plane_z:=0.035
```

**Terminal (PC)**

```bash
ros2 topic echo /jc/detections --once
ros2 run rqt_image_view rqt_image_view /jc/debug_image/compressed
```

El nodo usa el centro de la caja y el plano z = `plane_z` (ajústelo a la altura media de la fruta) para estimar la posición 3D, y publica en el mismo tópico que los detectores clásicos: **el** `pick_place_node` **funciona sin cambios** (DA-17). Si el modelo falla con la cámara del robot, capture 50–100 imágenes nuevas desde `observe` con `dl_01_captura_dataset.py`, agréguelas al dataset y reentrene en el PC (DA-11) [11].

## 5. VERIFICACIÓN Y EVIDENCIAS

*Tabla 6. Evidencias de la práctica.*

| **#** | **Criterio** | **Evidencia** |
|---|---|---|
| 1 | Cámara del robot publicada desde la Jetson y vista comprimida en el PC | Captura de `rqt_image_view` |
| 2 | Perfiles HSV recalibrados con la cámara del robot | `hsv_profiles.yaml` en Git |
| 3 | Calibración mano-ojo real con ≥ 10 muestras y validación independiente | Tablas 2 y 3 + YAML |
| 4 | Exactitud y repetibilidad reales comparadas con la simulación | Tabla 4 + análisis con la ecuación (1) |
| 5 | Detector YOLO en TensorRT publicando detecciones 3D en la celda | Tabla 5 + `topic echo` + debug\_image |

## 6. SOLUCIÓN DE PROBLEMAS

*Tabla 7. Problemas frecuentes.*

| **Síntoma** | **Causa probable** | **Solución** |
|---|---|---|
| `No se pudo abrir /dev/video0` | La cámara está en uso (`camera_node` u otro script) | Lanzar la celda con `camera:=false` antes de usar los scripts |
| Hand-eye con dispersión alta | Captura en movimiento o marcador en el borde | Esperar 3 s; centrar el marcador |
| Métodos discrepan mucho | Rotaciones pequeñas o en un solo eje | Variar J4, J5 y J6; ≥ 12 poses |
| Posiciones desplazadas constantes | Error de mano-ojo o de `plane_z` | Recalibrar; ajustar altura (DA-10, ec. 2) |
| `torch.cuda.is_available()` = False en la Jetson | Rueda de PyPI (sin CUDA) | Instalar las ruedas para JetPack 6 de la guía |
| El .engine no carga en otra Jetson | Los motores TensorRT dependen del equipo/versión | Exportar en cada dispositivo |

## REFERENCIAS

**[1]** ROS Perception, *camera\_calibration (image\_pipeline), Humble*. [En línea]. Disponible: [https://docs.ros.org/en/humble/p/camera_calibration/](https://docs.ros.org/en/humble/p/camera_calibration/)

**[2]** OpenCV team, *OpenCV 4.x Documentation*. [En línea]. Disponible: [https://docs.opencv.org/4.x/](https://docs.opencv.org/4.x/)

**[3]** F. C. Park y B. J. Martin, "Robot sensor calibration: solving AX = XB on the Euclidean group," *IEEE Trans. Robotics and Automation*, vol. 10, no. 5, pp. 717–721, 1994, doi: 10.1109/70.326576.

**[4]** R. Y. Tsai y R. K. Lenz, "A new technique for fully autonomous and efficient 3D robotics hand/eye calibration," *IEEE Trans. Robotics and Automation*, vol. 5, no. 3, pp. 345–358, 1989, doi: 10.1109/70.34770.

**[5]** S. Garrido-Jurado, R. Muñoz-Salinas, F. J. Madrid-Cuevas y M. J. Marín-Jiménez, "Automatic generation and detection of highly reliable fiducial markers under occlusion," *Pattern Recognition*, vol. 47, no. 6, pp. 2280–2292, 2014, doi: 10.1016/j.patcog.2014.01.005.

**[6]** T. Collins y A. Bartoli, "Infinitesimal plane-based pose estimation," *International Journal of Computer Vision*, vol. 109, no. 3, pp. 252–286, 2014, doi: 10.1007/s11263-014-0725-5.

**[7]** M. Esposito, *easy\_handeye2: automated, hardware-independent hand-eye calibration for ROS 2*. [En línea]. Disponible: [https://github.com/marcoesposito1988/easy_handeye2](https://github.com/marcoesposito1988/easy_handeye2)

**[8]** Ultralytics, *Quick Start Guide: NVIDIA Jetson with Ultralytics YOLO*. [En línea]. Disponible: [https://docs.ultralytics.com/guides/nvidia-jetson/](https://docs.ultralytics.com/guides/nvidia-jetson/)

**[9]** Ultralytics, *TensorRT Export for YOLO Models*. [En línea]. Disponible: [https://docs.ultralytics.com/integrations/tensorrt/](https://docs.ultralytics.com/integrations/tensorrt/)

**[10]** NVIDIA, *JetPack SDK 6.2* (Jetson Linux 36.4.3, Ubuntu 22.04, CUDA 12.6, cuDNN 9.3, TensorRT 10.3). [En línea]. Disponible: [https://developer.nvidia.com/embedded/jetpack-sdk-62](https://developer.nvidia.com/embedded/jetpack-sdk-62)

**[11]** G. Jocher y J. Qiu, *Ultralytics YOLO11*, versión 11.0.0, 2024. [En línea]. Disponible: [https://github.com/ultralytics/ultralytics](https://github.com/ultralytics/ultralytics) (licencia AGPL-3.0).

**[12]** J. R. Cháux Cedeño, *robots\_ws – paquetes ROS 2 del curso (repositorio en GitHub, licencia Apache-2.0), 2026. [En línea]. Disponible: https://github.com/jchauxdev/robots\_ws*
