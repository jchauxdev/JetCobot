# Documento de Apoyo No. DA-15 – Práctica: transferencia de las trayectorias al cobot real.

> Versión en Markdown del documento de apoyo, para consultar y copiar comandos desde GitHub. El documento de Word (formato GFPI-F-135) no se publica en el repositorio.

**Actividad de Aprendizaje:** Ejecutar en el cobot real las trayectorias desarrolladas en simulación, siguiendo el protocolo simulación → real y comparando cuantitativamente lo comandado con lo medido.

**Parte de la transferencia:** Parte B – Robot real con la Jetson AGX Orin.

**Equipo de trabajo:** Jetson AGX Orin conectada al JetCobot (y a la cámara) + PC en la misma red y con el mismo ROS\_DOMAIN\_ID.

**Duración Estimada:** 1 hora.

**Sesión:** Día 4 – 06/11/2026, 8:00 a.m. – 9:00 a.m.

**Relación con la Guía de Aprendizaje:** Actividad 3.4.5 (transferencia).

> **PARTE B · TRABAJO CON EL ROBOT (JETSON AGX ORIN + JETCOBOT):**
>
> Este documento se trabaja con la **Jetson AGX Orin** conectada al JetCobot y con el **PC** en la misma red. Cada bloque de comandos indica dónde se ejecuta: **Terminal (Jetson)** o **Terminal (PC)**. Requisito: haber completado la Parte A en simulación (DA-02 a DA-12).

## 1. OBJETIVOS DE APRENDIZAJE

- Completar las etapas 3, 4 y 5 del protocolo de transferencia simulación → real iniciado en DA-07.
- Ejecutar sin cambios en el robot real los nodos Python y C++ desarrollados en la Parte A.
- Comparar las trayectorias comandadas con las medidas en el robot real y con la línea base de Gazebo.
- Aplicar el protocolo de seguridad durante la ejecución con el robot.

## 2. FUNDAMENTOS

Los nodos de trayectorias solo usan la acción `/arm_controller/follow_joint_trajectory` o los servicios de `motion_server`, que existen igual en simulación y con el robot real. En el robot real, el puente `jetcobot_bridge` (DA-14) re-muestrea la trayectoria a 10 Hz y la envía con `send_angles` en modo refresco [2]; por ello, tramos muy cortos (&lt; 0,1 s) se fusionan. La interpolación del controlador simulado [1] y la del firmware del robot no son idénticas: la comparación con la línea base de Gazebo cuantifica esa diferencia.

*Tabla 1. Protocolo de transferencia simulación → real.*

| **Etapa** | **Plataforma** | **Dónde** | **Criterio para avanzar** |
|---|---|---|---|
| 1 | Mock (sin física) | PC – Parte A (DA-07) | error\_code = 0; sin colisiones en RViz2 |
| 2 | Gazebo | PC – Parte A (DA-07) | error\_code = 0; línea base medida |
| 3 | Puente simulado | Jetson + PC (Paso 1) | Misma secuencia de estados que en simulación |
| 4 | Robot real, 20 % vel. | Jetson + PC (Paso 2) | Error final ≤ 2°; observación sin riesgos |
| 5 | Robot real, vel. nominal | Jetson + PC (Paso 4) | Repetibilidad en 5 ciclos |

> **Seguridad:**
>
> Aplique las reglas de DA-14 y la evaluación de riesgos de la celda [4], [5].
>
> Antes de la etapa 4 revise que la trayectoria no cruce la mesa ni el cableado; inicie siempre desde `ready`.
>
> Una persona supervisa con la parada (`/jetcobot_bridge/stop`) lista mientras otra ejecuta.

## 3. PROCEDIMIENTO PASO A PASO

### Paso 0. Actualizar robots_ws

Antes de empezar, traiga lo nuevo del repositorio robots\_ws y vuelva a compilar, en la Jetson y en el PC:

**Terminal (Jetson y PC)**

```bash
# trae lo nuevo del repositorio (correcciones y mejoras)
cd ~/robots_ws && git pull
colcon build --symlink-install
source install/setup.bash
```

### Paso 1. Etapa 3: puente simulado en la Jetson

En la Terminal 1 entre a la Jetson por SSH (ssh usuario@IP\_JETSON y tmux new -A -s celda), lance la celda con el puente simulado y déjela ejecutando:

**Terminal 1 (PC → Jetson por SSH + tmux) – déjela ejecutando**

```bash
ros2 launch jc_bringup real.launch.py simulate:=true rviz:=false
```

En la Terminal 2 del PC abra RViz2 y déjela ejecutando:

**Terminal 2 (PC) – déjela ejecutando**

```bash
ros2 launch jc_moveit_config rviz.launch.py
```

En la Terminal 3 del PC ejecute los programas uno a uno:

**Terminal 3 (PC)**

```bash
ros2 run jc_apps trajectory_demo --ros-args -p segment_time:=2.5
ros2 run jc_motion trajectory_client --ros-args -p segment_time:=2.5
ros2 run jc_apps square_demo --ros-args -p side:=0.04 -p z:=0.14
# generador propio de DA-07
ros2 run mi_celda barrido
```

> **Resultado esperado:**
>
> La misma secuencia de estados y `error_code=0` que en la Parte A, ahora con el puente del robot (sin hardware) en la Jetson y los nodos en el PC.

### Paso 2. Etapa 4: robot real al 20 % de velocidad

En la Terminal 1 (Jetson) detenga la celda simulada con Ctrl + C y lance la celda con el robot real, con el robot energizado y la zona despejada:

**Terminal 1 (PC → Jetson por SSH + tmux) – déjela ejecutando**

```bash
# el servidor de movimiento usa escalado 0,2
ros2 launch jc_bringup real.launch.py port:=/dev/ttyUSB0 rviz:=false
```

En la Terminal 3 del PC grabe los datos de la prueba (Ctrl + C al terminar):

**Terminal 3 (PC) – déjela ejecutando**

```bash
ros2 bag record -o etapa4 /joint_states /arm_controller/follow_joint_trajectory/_action/feedback
```

En la Terminal 4 ejecute los programas; la Terminal 2 sigue con RViz2:

**Terminal 4 (PC)**

```bash
ros2 run jc_apps trajectory_demo --ros-args -p segment_time:=4.0
ros2 run jc_apps square_demo
```

Los nodos corren en el PC y comandan el robot por la red: es el mismo programa de la Parte A.

> **INSERTAR IMAGEN / CAPTURA (por el instructor):**
>
> *Video corto o secuencia de fotografías del JetCobot ejecutando* `square_demo` *(etapa 4).*

### Paso 3. Comparar con la línea base de Gazebo

Con la bolsa `etapa4` y la Tabla 2 de DA-07, complete para cada punto de paso de `trajectory_demo`:

*Tabla 2. Comparación comandado vs. medido en el robot real y en Gazebo (diligenciar).*

| **Punto** | **q comandada [°]** | **q medida real [°]** | **q medida Gazebo [°]** | **Error real máx. [°]** | **Llegada real [s]** |
|---|---|---|---|---|---|
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |
| 3 |  |  |  |  |  |
| 4 |  |  |  |  |  |
| 5 |  |  |  |  |  |

Analice: ¿el error final cumple ≤ 2°? ¿el robot real llega antes o después que el simulado? ¿qué parte de la diferencia se explica por el re-muestreo a 10 Hz del puente y qué parte por la dinámica del robot?

### Paso 4. Etapa 5: velocidad nominal y repetibilidad

Aumente el escalado de velocidad a 0,5 como máximo (parámetro de `motion_server` o `velocity_scaling` en los servicios) y ejecute 5 veces square\_demo en la Terminal 4. La parametrización temporal TOTG mantiene los límites de velocidad y aceleración [3].

*Tabla 3. Repetibilidad a velocidad nominal (diligenciar).*

| **Ciclo** | **Duración [s]** | **Error final máx. [°]** | **Observaciones** |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |

## 4. VERIFICACIÓN Y EVIDENCIAS

*Tabla 4. Evidencias de la práctica.*

| **#** | **Criterio** | **Evidencia** |
|---|---|---|
| 1 | Etapa 3: los nodos de la Parte A funcionan con el puente simulado | Registro de terminal |
| 2 | Etapa 4: trayectorias en el robot real con error final ≤ 2° | Tabla 2 + bag `etapa4` + video |
| 3 | Comparación real vs. Gazebo analizada | Párrafo de análisis |
| 4 | Etapa 5: repetibilidad en 5 ciclos | Tabla 3 |
| 5 | Protocolo de seguridad aplicado | Observación directa del instructor |

## 5. SOLUCIÓN DE PROBLEMAS

*Tabla 5. Problemas frecuentes.*

| **Síntoma** | **Causa probable** | **Solución** |
|---|---|---|
| El robot real 'salta' al primer punto | El primer punto no es el estado actual | Iniciar en `ready` o incluir el estado actual como primer punto |
| Error final &gt; 2° en el real | Carga, holgura o tolerancia | Revisar `goal_tolerance_deg` y los desfases (DA-14) |
| `GOAL_TOLERANCE_VIOLATED` | Trayectoria muy rápida para el robot | Aumentar `segment_time`; reducir el escalado |
| El PC no encuentra la acción | Dominio o `ROS_LOCALHOST_ONLY` distintos | Revisar la configuración de red (DA-13, Paso 4) |

## REFERENCIAS

**[1]** ros-controls, *ros2\_control Documentation (Humble)*. [En línea]. Disponible: [https://control.ros.org/humble/](https://control.ros.org/humble/)

**[2]** Elephant Robotics, *pymycobot – MyCobot 280 Python API* (v4.0.x). [En línea]. Disponible: [https://github.com/elephantrobotics/pymycobot/blob/main/docs/MyCobot_280_en.md](https://github.com/elephantrobotics/pymycobot/blob/main/docs/MyCobot_280_en.md)

**[3]** T. Kunz y M. Stilman, "Time-optimal trajectory generation for path following with bounded acceleration and velocity," en *Robotics: Science and Systems VIII*, 2012, doi: 10.15607/RSS.2012.VIII.027.

**[4]** International Organization for Standardization, *ISO 10218-1:2025 y ISO 10218-2:2025, Robotics — Safety requirements — Part 1: Industrial robots; Part 2: Industrial robot applications and robot cells*. Ginebra: ISO, 2025.

**[5]** International Organization for Standardization, *ISO/TS 15066:2016, Robots and robotic devices — Collaborative robots*. Ginebra: ISO, 2016.

**[6]** J. R. Cháux Cedeño, *robots\_ws – paquetes ROS 2 del curso (repositorio en GitHub, licencia Apache-2.0), 2026. [En línea]. Disponible: https://github.com/jchauxdev/robots\_ws*
