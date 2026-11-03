# JetCobot – Transferencias de conocimiento SENA 2026 (ROS 2 Humble)

Material de dos transferencias de conocimiento del SENA, diseñadas por Julián René Cháux Cedeño:

1. **Celda robótica colaborativa con visión artificial**: JetCobot (myCobot 280) con ROS 2 Humble, MoveIt 2, Gazebo y OpenCV/YOLO, de la simulación en el PC al robot real con una NVIDIA Jetson AGX Orin.
2. **Robot móvil autónomo de tracción diferencial**: construcción, RoboClaw, ROS 2 Humble en Jetson (Nano, Orin Nano, AGX Orin) o Raspberry Pi, lidar, cámaras, SLAM, Nav2 e integración con la celda del cobot mediante una App web de logística.

Cada documento de apoyo (DA) está en dos formatos: **`.docx`** (versión oficial, formato GFPI-F-135) y **`.md`**, que se lee directamente en GitHub y permite **copiar y pegar los comandos**. En los bloques de comandos el encabezado indica dónde se ejecutan: **Terminal – PC**, **Terminal – robot** (Jetson o Raspberry Pi) o ambos.

## Contenido del repositorio

| Carpeta / archivo | Contenido |
|---|---|
| [Portafolio_Transferencia_2026](Portafolio_Transferencia_2026) | Transferencia de la celda del cobot: guía de aprendizaje, DA-01 a DA-17 y `jc_ws.zip` (paquetes `jc_*`). |
| [Portafolio_Robot_Movil_2026](Portafolio_Robot_Movil_2026) | Transferencia del robot móvil: guía de aprendizaje, carpetas 8 a 21 con sus DA y `mr_ws.zip` (paquetes `mr_*`). |
| [JetcobotAppPrincipal_v1](JetcobotAppPrincipal_v1) | Aplicación principal del JetCobot: control del robot, secuencias y cliente OPC UA. |
| [JetcobotControlGUI](JetcobotControlGUI) | Interfaz gráfica de control del JetCobot: paneles, visión por cámara y diagnóstico. |
| [JetcobotOPCUA](JetcobotOPCUA) | Comunicación OPC UA entre el JetCobot y un PLC, con un programa de prueba. |
| [coordenadasrecogerpieza](coordenadasrecogerpieza) | Pose de recogida de piezas del JetCobot (X, Y, Z, R, P, Y) y distancia del gripper a la cámara. |
| [ver_camaras.py](ver_camaras.py) | Muestra dos cámaras USB lado a lado (OpenCV). |
| [tools](tools) | Herramientas: `docx2md.py` (convierte los DA de Word a Markdown) y `gen_readme.py` (genera este README). |
| [habilitarpantalla.txt](habilitarpantalla.txt) | Configuración para usar la Jetson por acceso remoto sin pantalla conectada. |

## Espacio de trabajo común: `~/robots_ws`

Las dos transferencias usan **un solo espacio de trabajo ROS 2, `~/robots_ws`**, en el PC y en el computador del robot. El código completo se entrega como **reserva** en dos archivos comprimidos; cada DA, en su **Paso 0**, copia de la reserva solo los paquetes que usa.

**Terminal – PC y robot**

```bash
REPO=https://raw.githubusercontent.com/jchauxdev/JetCobot/main
# cobot (DA-02)
mkdir -p ~/jc_reserva && cd ~/jc_reserva
wget $REPO/Portafolio_Transferencia_2026/jc_ws.zip && unzip jc_ws.zip
# robot móvil (DA-9.1)
mkdir -p ~/mr_reserva && cd ~/mr_reserva
wget $REPO/Portafolio_Robot_Movil_2026/mr_ws.zip && unzip mr_ws.zip
# espacio de trabajo común (vacío al inicio)
mkdir -p ~/robots_ws/src && cd ~/robots_ws && colcon build
```

Para saber qué espacio de trabajo está activo en una terminal (equivalente de `roscd` en ROS 1): `printenv COLCON_PREFIX_PATH`, `ros2 pkg prefix <paquete>` y `colcon_cd` (DA-02, Paso 7.1, y DA-9.1, Paso 6).

## Transferencia 1 – Celda robótica colaborativa (JetCobot)

| Documento | Markdown (copiar comandos) | Word |
|---|---|---|
| DA-01 – Vigilancia tecnológica y estado del arte: cobots, visión artificial y ROS 2 en la industria | [DA-01_Vigilancia_Tecnologica_Cobots_ROS2.md](Portafolio_Transferencia_2026/DA-01_Vigilancia_Tecnologica_Cobots_ROS2.md) | [docx](Portafolio_Transferencia_2026/DA-01_Vigilancia_Tecnologica_Cobots_ROS2.docx) |
| DA-02 – Entorno de desarrollo ROS 2 Humble en el PC | [DA-02_Entorno_ROS2_Humble_PC.md](Portafolio_Transferencia_2026/DA-02_Entorno_ROS2_Humble_PC.md) | [docx](Portafolio_Transferencia_2026/DA-02_Entorno_ROS2_Humble_PC.docx) |
| DA-03 – Arquitectura de ROS 2: nodos, tópicos, servicios, acciones, mensajes y parámetros | [DA-03_Arquitectura_ROS2.md](Portafolio_Transferencia_2026/DA-03_Arquitectura_ROS2.md) | [docx](Portafolio_Transferencia_2026/DA-03_Arquitectura_ROS2.docx) |
| DA-04 – Modelado del cobot con URDF/Xacro y visualización en RViz2 | [DA-04_URDF_Xacro_RViz.md](Portafolio_Transferencia_2026/DA-04_URDF_Xacro_RViz.md) | [docx](Portafolio_Transferencia_2026/DA-04_URDF_Xacro_RViz.docx) |
| DA-05 – Cinemática directa e inversa y planificación de movimientos con MoveIt 2 | [DA-05_Cinematica_MoveIt2.md](Portafolio_Transferencia_2026/DA-05_Cinematica_MoveIt2.md) | [docx](Portafolio_Transferencia_2026/DA-05_Cinematica_MoveIt2.docx) |
| DA-06 – Simulación de la celda robótica colaborativa en Gazebo integrada con ROS 2 | [DA-06_Simulacion_Gazebo.md](Portafolio_Transferencia_2026/DA-06_Simulacion_Gazebo.md) | [docx](Portafolio_Transferencia_2026/DA-06_Simulacion_Gazebo.docx) |
| DA-07 – Práctica: programación de nodos ROS 2 (Python/C++) para trayectorias del cobot en simulación | [DA-07_Practica_Trayectorias.md](Portafolio_Transferencia_2026/DA-07_Practica_Trayectorias.md) | [docx](Portafolio_Transferencia_2026/DA-07_Practica_Trayectorias.docx) |
| DA-08 – Fundamentos de visión artificial con OpenCV: adquisición, preprocesamiento, segmentación y extracción de características | [DA-08_Fundamentos_Vision_OpenCV.md](Portafolio_Transferencia_2026/DA-08_Fundamentos_Vision_OpenCV.md) | [docx](Portafolio_Transferencia_2026/DA-08_Fundamentos_Vision_OpenCV.docx) |
| DA-09 – Integración de cámaras en ROS 2, calibración de cámara y calibración mano-ojo en simulación | [DA-09_Camaras_Calibracion_ManoOjo.md](Portafolio_Transferencia_2026/DA-09_Camaras_Calibracion_ManoOjo.md) | [docx](Portafolio_Transferencia_2026/DA-09_Camaras_Calibracion_ManoOjo.docx) |
| DA-10 – Práctica: detección y localización de objetos (color, forma y marcadores ArUco) en la celda simulada, publicando sus posiciones en tópicos ROS 2 | [DA-10_Practica_Deteccion_Localizacion.md](Portafolio_Transferencia_2026/DA-10_Practica_Deteccion_Localizacion.md) | [docx](Portafolio_Transferencia_2026/DA-10_Practica_Deteccion_Localizacion.docx) |
| DA-11 – Visión con aprendizaje profundo en el PC: PyTorch, modelos preentrenados y entrenamiento de un detector de frutas | [DA-11_Deep_Learning_PyTorch_YOLO.md](Portafolio_Transferencia_2026/DA-11_Deep_Learning_PyTorch_YOLO.md) | [docx](Portafolio_Transferencia_2026/DA-11_Deep_Learning_PyTorch_YOLO.docx) |
| DA-12 – Práctica: integración visión–cobot en la celda simulada y planteamiento del proyecto final | [DA-12_Integracion_Simulacion.md](Portafolio_Transferencia_2026/DA-12_Integracion_Simulacion.md) | [docx](Portafolio_Transferencia_2026/DA-12_Integracion_Simulacion.docx) |
| DA-13 – Jetson AGX Orin: ROS 2 Humble en el computador del robot y ejecución distribuida con el PC | [DA-13_Jetson_ROS2_Ejecucion_Distribuida.md](Portafolio_Transferencia_2026/DA-13_Jetson_ROS2_Ejecucion_Distribuida.md) | [docx](Portafolio_Transferencia_2026/DA-13_Jetson_ROS2_Ejecucion_Distribuida.docx) |
| DA-14 – Práctica: conexión del controlador del JetCobot con ROS 2 mediante su driver | [DA-14_Conexion_JetCobot_ROS2.md](Portafolio_Transferencia_2026/DA-14_Conexion_JetCobot_ROS2.md) | [docx](Portafolio_Transferencia_2026/DA-14_Conexion_JetCobot_ROS2.docx) |
| DA-15 – Práctica: transferencia de las trayectorias al cobot real | [DA-15_Trayectorias_Robot_Real.md](Portafolio_Transferencia_2026/DA-15_Trayectorias_Robot_Real.md) | [docx](Portafolio_Transferencia_2026/DA-15_Trayectorias_Robot_Real.docx) |
| DA-16 – Práctica: percepción con el robot real – cámara, calibración mano-ojo, detección y despliegue de YOLO con TensorRT | [DA-16_Percepcion_Robot_Real.md](Portafolio_Transferencia_2026/DA-16_Percepcion_Robot_Real.md) | [docx](Portafolio_Transferencia_2026/DA-16_Percepcion_Robot_Real.docx) |
| DA-17 – Proyecto final con el robot real: integración, depuración, optimización, sustentación y evaluación | [DA-17_Proyecto_Final_Robot_Real.md](Portafolio_Transferencia_2026/DA-17_Proyecto_Final_Robot_Real.md) | [docx](Portafolio_Transferencia_2026/DA-17_Proyecto_Final_Robot_Real.docx) |
| Guía de aprendizaje | [Guia_Aprendizaje_Cobot_Vision_ROS2.md](Portafolio_Transferencia_2026/Guia_Aprendizaje_Cobot_Vision_ROS2.md) | [docx](Portafolio_Transferencia_2026/Guia_Aprendizaje_Cobot_Vision_ROS2.docx) |

## Transferencia 2 – Robot móvil autónomo

| Documento | Markdown (copiar comandos) | Word |
|---|---|---|
| 8.1 – Construcción del robot móvil de tracción diferencial | [8.1. Construcción del robot.md](Portafolio_Robot_Movil_2026/8.%20CONSTRUCCI%C3%93N%20DEL%20ROBOT/DOCUMENTOS%20DE%20APOYO/8.1.%20Construcci%C3%B3n%20del%20robot.md) | [docx](Portafolio_Robot_Movil_2026/8.%20CONSTRUCCI%C3%93N%20DEL%20ROBOT/DOCUMENTOS%20DE%20APOYO/8.1.%20Construcci%C3%B3n%20del%20robot.docx) |
| 9.1 – Espacio de trabajo ROS 2 robots_ws: creación paso a paso y material de reserva | [9.1. Espacio de trabajo ROS 2 robots_ws.md](Portafolio_Robot_Movil_2026/9.%20ESPACIO%20DE%20TRABAJO%20ROS%202/DOCUMENTOS%20DE%20APOYO/9.1.%20Espacio%20de%20trabajo%20ROS%202%20robots_ws.md) | [docx](Portafolio_Robot_Movil_2026/9.%20ESPACIO%20DE%20TRABAJO%20ROS%202/DOCUMENTOS%20DE%20APOYO/9.1.%20Espacio%20de%20trabajo%20ROS%202%20robots_ws.docx) |
| 10.1 – Configuración del RoboClaw 2x15A con Basicmicro Motion Studio | [10.1. Configuración del RoboClaw.md](Portafolio_Robot_Movil_2026/10.%20CONFIGURACI%C3%93N%20ROBOCLAW/MATERIAL%20DE%20APOYO/10.1.%20Configuraci%C3%B3n%20del%20RoboClaw.md) | [docx](Portafolio_Robot_Movil_2026/10.%20CONFIGURACI%C3%93N%20ROBOCLAW/MATERIAL%20DE%20APOYO/10.1.%20Configuraci%C3%B3n%20del%20RoboClaw.docx) |
| 11.1 (Raspberry Pi 4) – Ubuntu 22.04 y ROS 2 Humble en la Raspberry Pi 4 (alternativa) | [11.1. Ubuntu 22.04 y ROS 2 Humble en Raspberry Pi 4.md](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/1.%20RASPBERRY%20PI%204/DOCUMENTOS%20DE%20APOYO/11.1.%20Ubuntu%2022.04%20y%20ROS%202%20Humble%20en%20Raspberry%20Pi%204.md) | [docx](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/1.%20RASPBERRY%20PI%204/DOCUMENTOS%20DE%20APOYO/11.1.%20Ubuntu%2022.04%20y%20ROS%202%20Humble%20en%20Raspberry%20Pi%204.docx) |
| 11.1 (Jetson Nano) – Instalación de JetPack 4.6.6 (Ubuntu 18.04) en la Jetson Nano: descarga de la imagen, grabación de la microSD o SDK Manager | [11.1. Instalación de Linux JETSON NANO (JetPack 4.6.6).md](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/2.%20JETSON%20NANO/DOCUMENTOS%20DE%20APOYO/11.1.%20Instalaci%C3%B3n%20de%20Linux%20JETSON%20NANO%20%28JetPack%204.6.6%29.md) | [docx](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/2.%20JETSON%20NANO/DOCUMENTOS%20DE%20APOYO/11.1.%20Instalaci%C3%B3n%20de%20Linux%20JETSON%20NANO%20%28JetPack%204.6.6%29.docx) |
| 11.1 (Jetson AGX Orin) – Ubuntu 22.04 con JetPack 6.2 y ROS 2 Humble en la Jetson AGX Orin Developer Kit | [11.1. Jetson AGX Orin como computador del robot.md](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/3.%20JETSON%20AGX%20ORIN/11.1.%20Jetson%20AGX%20Orin%20como%20computador%20del%20robot.md) | [docx](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/3.%20JETSON%20AGX%20ORIN/11.1.%20Jetson%20AGX%20Orin%20como%20computador%20del%20robot.docx) |
| 11.1 (Jetson Orin Nano) – Ubuntu 22.04 con JetPack 6.2 y ROS 2 Humble en la Jetson Orin Nano Developer Kit de 8 GB | [11.1. Jetson Orin Nano DK 8GB - Ubuntu 22.04, JetPack 6.2 y ROS 2 Humble.md](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/4.%20JETSON%20ORIN%20NANO%20DK%208GB/DOCUMENTOS%20DE%20APOYO/11.1.%20Jetson%20Orin%20Nano%20DK%208GB%20-%20Ubuntu%2022.04%2C%20JetPack%206.2%20y%20ROS%202%20Humble.md) | [docx](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/4.%20JETSON%20ORIN%20NANO%20DK%208GB/DOCUMENTOS%20DE%20APOYO/11.1.%20Jetson%20Orin%20Nano%20DK%208GB%20-%20Ubuntu%2022.04%2C%20JetPack%206.2%20y%20ROS%202%20Humble.docx) |
| 11.1 (SSH) – Conexión remota al robot por SSH y edición con VS Code | [11.1. Configurar SSH remoto y VS Code.md](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/5.%20CONFIGURAR%20SSH%20VSCODE/11.1.%20Configurar%20SSH%20remoto%20y%20VS%20Code.md) | [docx](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/5.%20CONFIGURAR%20SSH%20VSCODE/11.1.%20Configurar%20SSH%20remoto%20y%20VS%20Code.docx) |
| 11.1 (VNC) – Escritorio remoto del robot con x11vnc, Remmina y TightVNC | [11.1. Acceso remoto con x11vnc y TightVNC.md](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/6.%20TIGHTVNC/11.1.%20Acceso%20remoto%20con%20x11vnc%20y%20TightVNC.md) | [docx](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/6.%20TIGHTVNC/11.1.%20Acceso%20remoto%20con%20x11vnc%20y%20TightVNC.docx) |
| 11.2 (Jetson Nano) – ROS 2 Humble en la Jetson Nano mediante contenedores Docker | [11.2. ROS 2 Humble en la Jetson Nano (Docker).md](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/2.%20JETSON%20NANO/DOCUMENTOS%20DE%20APOYO/11.2.%20ROS%202%20Humble%20en%20la%20Jetson%20Nano%20%28Docker%29.md) | [docx](Portafolio_Robot_Movil_2026/11.%20INSTALACI%C3%93N%20DE%20LINUX%20-%20ROS%202%20-%20RPI%20-%20JETSON/2.%20JETSON%20NANO/DOCUMENTOS%20DE%20APOYO/11.2.%20ROS%202%20Humble%20en%20la%20Jetson%20Nano%20%28Docker%29.docx) |
| 12.1 – Driver ROS 2 del RoboClaw: instalación, configuración, odometría y pruebas | [12.1. Driver ROS 2 del RoboClaw (mr_base).md](Portafolio_Robot_Movil_2026/12.%20LIBRER%C3%8DA%20CONTROL%20MOTORES%20-%20ROBOCLAW/DOCUMENTOS%20DE%20APOYO/12.1.%20Driver%20ROS%202%20del%20RoboClaw%20%28mr_base%29.md) | [docx](Portafolio_Robot_Movil_2026/12.%20LIBRER%C3%8DA%20CONTROL%20MOTORES%20-%20ROBOCLAW/DOCUMENTOS%20DE%20APOYO/12.1.%20Driver%20ROS%202%20del%20RoboClaw%20%28mr_base%29.docx) |
| 12.2 – Calibración de la odometría: que 1 metro sea 1 metro | [12.2. Calibración de la odometría (prueba de 1 metro).md](Portafolio_Robot_Movil_2026/12.%20LIBRER%C3%8DA%20CONTROL%20MOTORES%20-%20ROBOCLAW/DOCUMENTOS%20DE%20APOYO/12.2.%20Calibraci%C3%B3n%20de%20la%20odometr%C3%ADa%20%28prueba%20de%201%20metro%29.md) | [docx](Portafolio_Robot_Movil_2026/12.%20LIBRER%C3%8DA%20CONTROL%20MOTORES%20-%20ROBOCLAW/DOCUMENTOS%20DE%20APOYO/12.2.%20Calibraci%C3%B3n%20de%20la%20odometr%C3%ADa%20%28prueba%20de%201%20metro%29.docx) |
| 12.3 – Permisos y nombres fijos de los puertos USB con reglas udev | [12.3. Reglas udev - permisos y nombres fijos.md](Portafolio_Robot_Movil_2026/12.%20LIBRER%C3%8DA%20CONTROL%20MOTORES%20-%20ROBOCLAW/DOCUMENTOS%20DE%20APOYO/14.%20REGISTRAR%20PERMISOS%20TTYACM_/12.3.%20Reglas%20udev%20-%20permisos%20y%20nombres%20fijos.md) | [docx](Portafolio_Robot_Movil_2026/12.%20LIBRER%C3%8DA%20CONTROL%20MOTORES%20-%20ROBOCLAW/DOCUMENTOS%20DE%20APOYO/14.%20REGISTRAR%20PERMISOS%20TTYACM_/12.3.%20Reglas%20udev%20-%20permisos%20y%20nombres%20fijos.docx) |
| 13.1 – Configuración de la red local de robots | [13.1. Configuración de la red local - Robots.md](Portafolio_Robot_Movil_2026/13.%20CONFIGURACI%C3%93N%20DE%20LA%20RED%20Y%20VARIABLES%20DE%20ENTORNO/DOCUMENTOS%20DE%20APOYO/13.1.%20Configuraci%C3%B3n%20de%20la%20red%20local%20-%20Robots.md) | [docx](Portafolio_Robot_Movil_2026/13.%20CONFIGURACI%C3%93N%20DE%20LA%20RED%20Y%20VARIABLES%20DE%20ENTORNO/DOCUMENTOS%20DE%20APOYO/13.1.%20Configuraci%C3%B3n%20de%20la%20red%20local%20-%20Robots.docx) |
| 13.2 – Red ROS 2: descubrimiento DDS y variables de entorno | [13.2. Configuración de la red ROS 2 y variables de entorno.md](Portafolio_Robot_Movil_2026/13.%20CONFIGURACI%C3%93N%20DE%20LA%20RED%20Y%20VARIABLES%20DE%20ENTORNO/DOCUMENTOS%20DE%20APOYO/13.2.%20Configuraci%C3%B3n%20de%20la%20red%20ROS%202%20y%20variables%20de%20entorno.md) | [docx](Portafolio_Robot_Movil_2026/13.%20CONFIGURACI%C3%93N%20DE%20LA%20RED%20Y%20VARIABLES%20DE%20ENTORNO/DOCUMENTOS%20DE%20APOYO/13.2.%20Configuraci%C3%B3n%20de%20la%20red%20ROS%202%20y%20variables%20de%20entorno.docx) |
| 13.3 – Arranque automático de los drivers del robot con systemd | [13.3. Arranque automático de los drivers (systemd).md](Portafolio_Robot_Movil_2026/13.%20CONFIGURACI%C3%93N%20DE%20LA%20RED%20Y%20VARIABLES%20DE%20ENTORNO/DOCUMENTOS%20DE%20APOYO/13.3.%20Arranque%20autom%C3%A1tico%20de%20los%20drivers%20%28systemd%29.md) | [docx](Portafolio_Robot_Movil_2026/13.%20CONFIGURACI%C3%93N%20DE%20LA%20RED%20Y%20VARIABLES%20DE%20ENTORNO/DOCUMENTOS%20DE%20APOYO/13.3.%20Arranque%20autom%C3%A1tico%20de%20los%20drivers%20%28systemd%29.docx) |
| 14.1 – Modelo URDF/Xacro del robot y visualización en RViz2 | [14.1. Modelo URDF y visualización del robot en RViz2.md](Portafolio_Robot_Movil_2026/14.%20ROBOT%20EN%20RVIZ/DOCUMENTOS%20DE%20APOYO/14.1.%20Modelo%20URDF%20y%20visualizaci%C3%B3n%20del%20robot%20en%20RViz2.md) | [docx](Portafolio_Robot_Movil_2026/14.%20ROBOT%20EN%20RVIZ/DOCUMENTOS%20DE%20APOYO/14.1.%20Modelo%20URDF%20y%20visualizaci%C3%B3n%20del%20robot%20en%20RViz2.docx) |
| 15.1 – Cámara RGB USB en ROS 2 | [15.1. Cámara RGB USB en ROS 2.md](Portafolio_Robot_Movil_2026/15.%20INSTALACI%C3%93N%20Y%20CONFIGURACI%C3%93N%20C%C3%81MARA%20WEB/DOCUMENTOS%20DE%20APOYO/15.1.%20C%C3%A1mara%20RGB%20USB%20en%20ROS%202.md) | [docx](Portafolio_Robot_Movil_2026/15.%20INSTALACI%C3%93N%20Y%20CONFIGURACI%C3%93N%20C%C3%81MARA%20WEB/DOCUMENTOS%20DE%20APOYO/15.1.%20C%C3%A1mara%20RGB%20USB%20en%20ROS%202.docx) |
| 16.1 – Lidar RPLidar A1 en ROS 2 (y Hokuyo URG-04LX como alternativa) | [16.1. RPLidar A1 en ROS 2.md](Portafolio_Robot_Movil_2026/16.%20INSTALACI%C3%93N%20Y%20CONFIGURACI%C3%93N%20LIDAR/DOCUMENTOS%20DE%20APOYO/16.1.%20RPLidar%20A1%20en%20ROS%202.md) | [docx](Portafolio_Robot_Movil_2026/16.%20INSTALACI%C3%93N%20Y%20CONFIGURACI%C3%93N%20LIDAR/DOCUMENTOS%20DE%20APOYO/16.1.%20RPLidar%20A1%20en%20ROS%202.docx) |
| 17.1 – Generación del mapa del entorno con slam_toolbox | [17.1. Generación del mapa con slam_toolbox.md](Portafolio_Robot_Movil_2026/17.%20GENERACI%C3%93N%20DE%20MAPA/DOCUMENTOS%20DE%20APOYO/17.1.%20Generaci%C3%B3n%20del%20mapa%20con%20slam_toolbox.md) | [docx](Portafolio_Robot_Movil_2026/17.%20GENERACI%C3%93N%20DE%20MAPA/DOCUMENTOS%20DE%20APOYO/17.1.%20Generaci%C3%B3n%20del%20mapa%20con%20slam_toolbox.docx) |
| 18.1 – Navegación autónoma con Nav2: localización AMCL y seguimiento de trayectorias | [18.1. Navegación autónoma con Nav2.md](Portafolio_Robot_Movil_2026/18.%20SEGUIMIENTO%20DE%20TRAYECTORIAS/DOCUMENTOS%20DE%20APOYO/18.1.%20Navegaci%C3%B3n%20aut%C3%B3noma%20con%20Nav2.md) | [docx](Portafolio_Robot_Movil_2026/18.%20SEGUIMIENTO%20DE%20TRAYECTORIAS/DOCUMENTOS%20DE%20APOYO/18.1.%20Navegaci%C3%B3n%20aut%C3%B3noma%20con%20Nav2.docx) |
| 18.2 – Puntos con nombre en el mapa y orden «ir al punto X» | [18.2. Puntos con nombre y orden ir al punto X.md](Portafolio_Robot_Movil_2026/18.%20SEGUIMIENTO%20DE%20TRAYECTORIAS/DOCUMENTOS%20DE%20APOYO/18.2.%20Puntos%20con%20nombre%20y%20orden%20ir%20al%20punto%20X.md) | [docx](Portafolio_Robot_Movil_2026/18.%20SEGUIMIENTO%20DE%20TRAYECTORIAS/DOCUMENTOS%20DE%20APOYO/18.2.%20Puntos%20con%20nombre%20y%20orden%20ir%20al%20punto%20X.docx) |
| 19.1 – Teleoperación del robot: teclado y celular (App web) | [19.1. Teleoperación del robot (teclado y celular).md](Portafolio_Robot_Movil_2026/19.%20TELEOPERACI%C3%93N%20ROBOT%20ROS%202/19.1.%20Teleoperaci%C3%B3n%20del%20robot%20%28teclado%20y%20celular%29.md) | [docx](Portafolio_Robot_Movil_2026/19.%20TELEOPERACI%C3%93N%20ROBOT%20ROS%202/19.1.%20Teleoperaci%C3%B3n%20del%20robot%20%28teclado%20y%20celular%29.docx) |
| 20.1 – Cámara de profundidad Intel RealSense D435i en el robot móvil | [20.1. RealSense D435i en el robot móvil.md](Portafolio_Robot_Movil_2026/20.%20C%C3%81MARA%20DE%20PROFUNDIDAD%20REALSENSE%20D435i/DOCUMENTOS%20DE%20APOYO/20.1.%20RealSense%20D435i%20en%20el%20robot%20m%C3%B3vil.md) | [docx](Portafolio_Robot_Movil_2026/20.%20C%C3%81MARA%20DE%20PROFUNDIDAD%20REALSENSE%20D435i/DOCUMENTOS%20DE%20APOYO/20.1.%20RealSense%20D435i%20en%20el%20robot%20m%C3%B3vil.docx) |
| 21.1 – Integración robot móvil – cobot con una App web de logística | [21.1. Integración robot móvil - cobot con App de logística.md](Portafolio_Robot_Movil_2026/21.%20INTEGRACI%C3%93N%20ROBOT%20M%C3%93VIL%20-%20COBOT/DOCUMENTOS%20DE%20APOYO/21.1.%20Integraci%C3%B3n%20robot%20m%C3%B3vil%20-%20cobot%20con%20App%20de%20log%C3%ADstica.md) | [docx](Portafolio_Robot_Movil_2026/21.%20INTEGRACI%C3%93N%20ROBOT%20M%C3%93VIL%20-%20COBOT/DOCUMENTOS%20DE%20APOYO/21.1.%20Integraci%C3%B3n%20robot%20m%C3%B3vil%20-%20cobot%20con%20App%20de%20log%C3%ADstica.docx) |
| Guía de aprendizaje | [Guia_Aprendizaje_Robot_Movil_ROS2.md](Portafolio_Robot_Movil_2026/Guia_Aprendizaje_Robot_Movil_ROS2.md) | [docx](Portafolio_Robot_Movil_2026/Guia_Aprendizaje_Robot_Movil_ROS2.docx) |

## Actualizar los `.md` después de editar un `.docx`

Los `.md` se generan a partir de los `.docx`. Después de modificar un documento en Word, regenérelos desde la carpeta del repositorio (requiere Python 3 con `lxml` y `Pillow`):

**Terminal – PC**

```bash
pip install lxml pillow
# un documento
python3 tools/docx2md.py "Portafolio_Transferencia_2026/DA-02_Entorno_ROS2_Humble_PC.docx"
# todos los documentos y este README
find Portafolio_Robot_Movil_2026 Portafolio_Transferencia_2026 -name "*.docx" ! -name "~\$*" ! -path "*REPOSITORIOS*" -print0 | xargs -0 python3 tools/docx2md.py
python3 tools/gen_readme.py .
```

En Windows use `python` en lugar de `python3` y ejecute los comandos en Git Bash.

## Archivos que no están en el repositorio

GitHub no acepta archivos de más de 100 MB. No se incluyen:

- Imágenes de JetPack (carpetas `ISO JETPACK`): descárguelas de [JetPack Archive](https://developer.nvidia.com/embedded/jetpack-archive) (Jetson Nano: [JetPack 4.6.6](https://developer.nvidia.com/jetpack-sdk-466); Jetson Orin: [JetPack 6.2.3](https://developer.nvidia.com/embedded/jetpack-sdk-623)), como se explica en los DA de la carpeta 11.
- Video de configuración del RoboClaw (carpeta 10): disponible con el instructor.

## Autor

Julián René Cháux Cedeño – SENA, 2026.
