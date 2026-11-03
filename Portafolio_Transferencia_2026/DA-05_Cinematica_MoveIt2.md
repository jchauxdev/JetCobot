# Documento de Apoyo No. DA-05 – Cinemática directa e inversa y planificación de movimientos con MoveIt 2.

> Versión en Markdown del documento de apoyo, para consultar y copiar comandos desde GitHub. El documento de Word (formato GFPI-F-135) no se publica en el repositorio.

**Actividad de Aprendizaje:** Calcular la cinemática directa e inversa del cobot y planificar movimientos libres de colisión con MoveIt 2, interpretando los resultados (multiplicidad de soluciones, singularidades, alcance).

**Parte de la transferencia:** Parte A – Simulación en el PC.

**Equipo de trabajo:** PC con Ubuntu 22.04 y ROS 2 Humble. No se usa la Jetson ni se energiza el robot.

**Duración Estimada:** 2 horas.

**Sesión:** Día 2 – 04/11/2026, 8:00 a.m. – 10:00 a.m.

**Relación con la Guía de Aprendizaje:** Actividad 3.3.4 (apropiación).

> **PARTE A · TRABAJO EN EL PC (SIMULACIÓN):**
>
> Todo el trabajo de este documento se hace en el **PC** con Ubuntu 22.04 y ROS 2 Humble, con el robot simulado (mock y Gazebo) y, cuando se indique, una cámara USB conectada al PC. **No se usa la Jetson ni se energiza el robot.** Cada bloque de comandos indica **Terminal (PC)**.

## 1. OBJETIVOS DE APRENDIZAJE

- Formular la cinemática directa (FK) como producto de transformaciones homogéneas y calcular el Jacobiano geométrico.
- Resolver la cinemática inversa (IK) de forma numérica (mínimos cuadrados amortiguados) y analizar su multiplicidad.
- Evaluar la manipulabilidad y el espacio de trabajo útil del cobot.
- Describir la arquitectura de MoveIt 2 (move\_group, SRDF, IK, OMPL, escena de planificación, ejecución).
- Planificar y ejecutar movimientos articulares, de pose y cartesianos desde RViz2, la CLI, Python y C++.

## 2. FUNDAMENTOS

### 2.1 Cinemática directa

Para un manipulador serie de *n* articulaciones, la pose del efector final respecto a la base es el producto de las transformaciones de cada articulación (ecuación (1) de DA-04) [2], [1]:

$${T}_{world}^{tcp}\left( q \right)={T}_{world}^{0}\left( \prod_{i=1}^{6} {T}_{i-1}^{i}\left( {q}_{i} \right) \right){T}_{6}^{tcp}=\left[  \right] \qquad (1)$$

El **Jacobiano geométrico** relaciona velocidades articulares con la velocidad espacial del TCP. Para articulaciones de revolución con eje unitario **z**ᵢ y origen **o**ᵢ expresados en la base:

$$\left[  \right]=J\left( q \right) \bar{q},  {J}_{i}=\left[  \right] \qquad (2)$$

En una **singularidad** J pierde rango y el robot pierde movilidad en alguna dirección. El índice de manipulabilidad de Yoshikawa cuantifica la distancia a la singularidad [4]:

$$w\left( q \right)=\sqrt{det\left( J{J}^{T} \right)} \qquad (3)$$

### 2.2 Cinemática inversa

La IK busca **q** tal que **T**(**q**) = **T**d. Para el JetCobot (eje de muñeca no esférica y desplazamientos laterales) se usan métodos numéricos. El método de mínimos cuadrados amortiguados (DLS) itera [5]:

$$\Delta q={J}^{T}{\left( J{J}^{T}+{λ}^{2}I \right)}^{-1}e,  e=\left[  \right] \qquad (4)$$

El amortiguamiento λ evita velocidades enormes cerca de singularidades a costa de un pequeño error. En `jc_apps/kinematics.py` se implementan (1)–(4) en ~100 líneas de NumPy a partir del URDF (el error de orientación se calcula con la forma eje-ángulo, equivalente a (4) para errores pequeños). MoveIt 2 usa por defecto el plugin **KDL** [6], también numérico (Newton–Raphson con reinicios aleatorios dentro de un tiempo límite). Consecuencias prácticas:

- **Multiplicidad**: una misma pose admite varias configuraciones (codo arriba/abajo, muñeca girada). En la validación, `/compute_ik` devolvió para (0,18; −0,06; 0,12) m con TCP hacia abajo la solución q = (1,5; −85,8; 88,7; −92,9; 0; 1,5)°, distinta de la configuración `ready`.
- **Incompletitud**: un solver numérico puede no encontrar una solución que existe. Al barrer la mesa con `/compute_ik` (50 ms, 8 intentos por punto) aparecieron celdas aisladas sin solución dentro de la zona alcanzable (Figura 1); aumentar el tiempo, usar semillas o un solver alternativo (p. ej. `pick_ik`) mitiga el problema.

![imagen](md_img/DA_05_Cinematica_MoveIt2_01.jpg)

*Figura 1. Espacio de trabajo del modelo: nube de FK (gris) y celdas de la mesa donde existe agarre vertical con el TCP a 20 mm de altura según MoveIt (verde). Se marcan las piezas y depósitos del mundo de simulación.*

La zona de agarre vertical es una corona entre ≈ 0,14 m y 0,29 m del eje de J1 (con algunos puntos más cercanos): demasiado cerca, el codo no puede plegarse; demasiado lejos, el brazo no alcanza con la herramienta vertical. **Diseñe la celda (piezas, depósitos, cámara) dentro de esa corona.**

![imagen](md_img/DA_05_Cinematica_MoveIt2_02.jpg)

*Figura 2. Manipulabilidad (3) a lo largo de una recta con la herramienta vertical, calculada con la IK DLS de jc_apps.*

### 2.3 MoveIt 2

MoveIt es el marco de manipulación más usado en ROS [7]. En ROS 2 el nodo central es `move_group` (Figura 3), que combina la descripción del robot (URDF + SRDF), un plugin de IK, el planificador OMPL, la escena de planificación (colisiones), la parametrización temporal y la ejecución mediante controladores `FollowJointTrajectory` [8].

![imagen](md_img/DA_05_Cinematica_MoveIt2_03.jpg)

*Figura 3. Arquitectura de MoveIt 2 tal como se configura en jc_moveit_config.*

*Tabla 1. Configuración de MoveIt 2 del JetCobot.*

| **Elemento** | **Archivo en jc\_moveit\_config** | **Contenido** |
|---|---|---|
| SRDF | config/jetcobot.srdf | Grupos `arm` (cadena base\_link→tcp) y `gripper`; estados `home`, `ready`, `observe`, `open`, `close`; matriz de colisiones deshabilitadas. |
| IK | config/kinematics.yaml | KDL, resolución 0,005, timeout 0,05 s. |
| Límites | config/joint\_limits.yaml | 1,5 rad/s y 3 rad/s² por articulación; escalado por defecto 30 %. |
| Planificador | config/ompl\_planning.yaml | RRTConnect por defecto [10]; RRT\*, PRM disponibles [9]; adaptadores con TOTG [11]. |
| Controladores | config/moveit\_controllers.yaml | `arm_controller`, `gripper_controller` (FollowJointTrajectory). |

> **Nota:**
>
> En un proyecto nuevo esta configuración se genera con el *MoveIt Setup Assistant* (`ros2 launch moveit_setup_assistant setup_assistant.launch.py`). En robots\_ws se escribió a mano para controlar cada parámetro; compare ambos enfoques como ejercicio.

## 3. PROCEDIMIENTO PASO A PASO

### Paso 0. Incorporar al robots_ws el material de este documento

El espacio de trabajo `~/robots_ws` se construye a medida que avanza la transferencia: cada documento incorpora **solo** el material que usa. Agregue desde el repositorio robots\_ws (DA-02, Paso 7) lo siguiente y revise su contenido antes de ejecutarlo:

| **Paquete / carpeta** | **Para qué sirve** | **Qué contiene** | **Dónde se usa** |
|---|---|---|---|
| `src/jc_moveit_config` | Configuración de MoveIt 2 para planificar movimientos del brazo sin chocar. | SRDF (grupos arm y gripper, poses home, ready y observe), kinematics.yaml (KDL), OMPL, límites de articulaciones y controladores; escrita a mano. | PC (Parte A). En la Parte B también en la Jetson AGX Orin (DA-13). |
| `src/jc_motion` | Nodos en C++ que mueven el brazo con MoveIt (MoveGroupInterface) y los ofrecen como servicios al resto de la celda. | motion\_server (servicios /jc/move\_to\_pose, /jc/move\_to\_named y /jc/set\_gripper), pose\_goal\_demo y trajectory\_client. | PC (Parte A). En la Parte B también en la Jetson AGX Orin (DA-13). |
| `src/jc_bringup` | Arranque de la celda completa: un launch por situación (sin hardware, simulación en Gazebo y robot real). | launch/ mock.launch.py (este documento), sim.launch.py (Gazebo, DA-06) y real.launch.py (Parte B); config/celda.yaml; mundos y modelos de Gazebo. | PC (Parte A). En la Parte B también en la Jetson AGX Orin (DA-13). |

**Terminal (PC)**

```bash
cd ~/robots_ws && git sparse-checkout add src/jc_moveit_config
cd ~/robots_ws && git sparse-checkout add src/jc_motion
cd ~/robots_ws && git sparse-checkout add src/jc_bringup
# instala las dependencias de los paquetes agregados
rosdep install --from-paths ~/robots_ws/src --ignore-src -r -y --skip-keys "mr_navigation jc_driver"
cd ~/robots_ws
colcon build --symlink-install --packages-select jc_moveit_config jc_motion jc_bringup
source install/setup.bash
# explore la estructura
tree -L 2 src/
# paquetes del workspace hasta ahora
ros2 pkg list | grep -E "jc_|mi_celda"
```

> **Resultado esperado:**
>
> `Summary: 3 packages finished`. `jc_motion` es C++ y es el que más tarda (1–3 minutos); si el PC se queda sin memoria use `--parallel-workers 2`. `jc_bringup` declara también `jc_driver`, que se incorpora en la Parte B (DA-14): no hace falta para los lanzadores `mock` y `sim`.

### Paso 1. FK, Jacobiano e IK con Python (sin MoveIt)

**Python (con el overlay de robots_ws cargado)**

```
import subprocess, numpy as np
from ament_index_python.packages import get_package_share_directory as share
from jc_apps.kinematics import SerialChain
urdf = subprocess.check_output(["xacro", share("jc_description") + "/urdf/jetcobot.urdf.xacro",
                                "sim_mode:=real"]).decode()
ch = SerialChain(urdf, "world", "tcp")
q = np.radians([0, 0, -90, 0, 0, 0])
T = ch.fk(q);  print(np.round(T, 4))                 # TCP (0.1692, -0.0646, 0.1264), z hacia abajo
print("w =", ch.manipulability(q))                   # 1.79e-03
q_sol, ok, err = ch.ik(T, np.radians([10, 5, -80, -5, 0, 0]))
print(ok, err, np.degrees(q_sol).round(2))
```

> **Resultado esperado:**
>
> FK: TCP = (0,1692; −0,0646; 0,1264) m con eje z = (0, 0, −1). La IK converge (ok = True) con error &lt; 0,1 mm. Estos mismos valores verifican las pruebas unitarias de jc\_apps.

### Paso 2. Celda en modo mock y RViz2 MotionPlanning

**Terminal (PC)**

```bash
ros2 launch jc_bringup mock.launch.py
```

1. En el panel *MotionPlanning → Planning*: grupo `arm`, *Goal State* = `observe`, **Plan** y luego **Execute**.
1. Arrastre el marcador interactivo del TCP a una pose alcanzable; observe cómo el robot fantasma (naranja) solo sigue posiciones con solución de IK.
1. En *Options* cambie *Velocity Scaling* (0,1 → 0,5) y compare la duración de la trayectoria.
1. En *Context* cambie el planificador (RRTConnect, RRTstar, PRM) y registre tiempo de planificación y longitud del camino (Tabla 2).

> **INSERTAR IMAGEN / CAPTURA (por el instructor):**
>
> *Captura de RViz2 con el plugin MotionPlanning mostrando la trayectoria planificada hacia* `observe`*.*

*Tabla 2. Comparación de planificadores (diligenciar; 5 repeticiones, reportar media).*

| **Planificador** | **Tiempo de planificación [s]** | **Duración de la trayectoria [s]** | **Observaciones** |
|---|---|---|---|
| RRTConnect |  |  |  |
| RRTstar |  |  |  |
| PRM |  |  |  |

### Paso 3. Servicios de IK y FK de MoveIt desde la CLI

**Terminal (PC)**

```bash
ros2 service call /compute_ik moveit_msgs/srv/GetPositionIK "{ik_request: {group_name: arm, ik_link_name: tcp,
  avoid_collisions: true, timeout: {sec: 1}, pose_stamped: {header: {frame_id: world}, pose: {
  position: {x: 0.18, y: -0.06, z: 0.12}, orientation: {x: 0.7071, y: -0.7071, z: 0.0, w: 0.0}}}}}"
ros2 service call /compute_fk moveit_msgs/srv/GetPositionFK "{header: {frame_id: world}, fk_link_names: [tcp],
  robot_state: {joint_state: {name: [joint1, joint2, joint3, joint4, joint5, joint6],
  position: [0.0, 0.0, -1.5708, 0.0, 0.0, 0.0]}}}"
```

> **Precaución:**
>
> En ROS 2, un `geometry_msgs/Quaternion` creado sin valores es (0, 0, 0, **1**). Si solo asigna x e y, el cuaternión resultante es incorrecto y la IK falla con `NO_IK_SOLUTION (−31)`. Asigne siempre los cuatro componentes. Este error se reprodujo durante la validación del material.

La orientación (0,7071; −0,7071; 0; 0) corresponde a roll = π, pitch = 0, yaw = −π/2: herramienta vertical hacia abajo (ver `motion_client.top_down_quat`). Repita la IK varias veces: ¿obtiene siempre la misma configuración? Explique.

### Paso 4. Servicios de alto nivel de la celda (motion_server)

**Terminal (PC)**

```bash
ros2 service call /jc/move_to_named jc_interfaces/srv/MoveToNamed "{name: observe, velocity_scaling: 0.3}"
ros2 service call /jc/set_gripper jc_interfaces/srv/SetGripper "{opening: 0.3}"
ros2 service call /jc/move_to_pose jc_interfaces/srv/MoveToPose "{cartesian: false, velocity_scaling: 0.3,
  target: {header: {frame_id: world}, pose: {position: {x: 0.17, y: -0.08, z: 0.14},
  orientation: {x: 0.7071, y: -0.7071, z: 0.0, w: 0.0}}}}"
# cuadrado de 4 cm con trayectorias cartesianas
ros2 run jc_apps square_demo
```

> **Resultado esperado:**
>
> `success=True, message='OK'`; el cuadrado se ejecuta con los cuatro lados `OK (cartesiana)`, tal como se obtuvo en la validación (mock, Gazebo y robot simulado).

### Paso 5. Interfaz C++ (MoveGroupInterface)

**Terminal (PC)**

```bash
ros2 launch jc_motion pose_goal_demo.launch.py
```

Estudie `jc_motion/src/pose_goal_demo.cpp`: `setNamedTarget`, `setPoseTarget`, `plan`, `execute` y `computeCartesianPath(waypoints, eef_step = 0.005, jump_threshold = 0.0, trajectory)`, que devuelve la fracción del camino lograda (en la validación: 100 %). En `motion_server.cpp` observe además cómo se re-parametriza en el tiempo la trayectoria cartesiana con TOTG [11] para respetar el escalado de velocidad.

### Paso 6. Validar la FK propia contra TF

**Terminal (PC)**

```bash
# con la celda (mock o Gazebo) en marcha
ros2 run jc_apps fk_check
```

> **Resultado esperado:**
>
> `|dif| = 0.000 mm` entre la FK de kinematics.py y la TF de robot\_state\_publisher; también imprime w.

## 4. VERIFICACIÓN Y EVIDENCIAS

*Tabla 3. Evidencias de la actividad.*

| **#** | **Criterio** | **Evidencia** |
|---|---|---|
| 1 | FK/IK/Jacobiano calculados y contrastados con TF | Salida del Paso 1 y Paso 6 |
| 2 | Planificación y ejecución a estados con nombre y poses en RViz2 | Captura |
| 3 | Comparación de planificadores | Tabla 2 |
| 4 | Uso de /compute\_ik y explicación de la multiplicidad | Registro + respuesta escrita |
| 5 | Trayectoria cartesiana ejecutada (cuadrado) | Registro de `square_demo` |

## 5. PREGUNTAS DE ANÁLISIS

1. ¿Por qué el agarre vertical es imposible muy cerca de la base aunque esos puntos estén dentro del alcance?
1. ¿Qué ocurre con w en la configuración `home` (brazo extendido verticalmente)? Verifíquelo con kinematics.py.
1. ¿Cuándo preferir una trayectoria cartesiana sobre una planificada con OMPL? Mencione dos riesgos de la cartesiana.

## 6. SOLUCIÓN DE PROBLEMAS

*Tabla 4. Problemas frecuentes.*

| **Síntoma** | **Causa probable** | **Solución** |
|---|---|---|
| `NO_IK_SOLUTION (−31)` | Pose inalcanzable, cuaternión mal formado o timeout corto | Ver Figura 1; asignar x,y,z,w; aumentar timeout |
| Plan OK pero ejecución falla | Controlador no activo / nombres de acción distintos | `ros2 control list_controllers`; revisar moveit\_controllers.yaml |
| Cartesiana &lt; 95 % | Cruce por singularidad o límite articular | Cambiar la orientación o dividir el camino |
| `No 3D sensor plugin(s) defined for octomap updates` | Mensaje informativo (no hay sensores 3D configurados) | Ninguna; es esperado |

## REFERENCIAS

**[1]** K. M. Lynch y F. C. Park, *Modern Robotics: Mechanics, Planning, and Control*. Cambridge, U.K.: Cambridge University Press, 2017.

**[2]** B. Siciliano, L. Sciavicco, L. Villani y G. Oriolo, *Robotics: Modelling, Planning and Control*. London, U.K.: Springer, 2009, doi: 10.1007/978-1-84628-642-1.

**[3]** J. J. Craig, *Introduction to Robotics: Mechanics and Control*, 4th ed. Pearson, 2018.

**[4]** T. Yoshikawa, "Manipulability of robotic mechanisms," *The International Journal of Robotics Research*, vol. 4, no. 2, pp. 3–9, 1985, doi: 10.1177/027836498500400201.

**[5]** Y. Nakamura y H. Hanafusa, "Inverse kinematic solutions with singularity robustness for robot manipulator control," *ASME J. Dynamic Systems, Measurement, and Control*, vol. 108, no. 3, pp. 163–171, 1986, doi: 10.1115/1.3143764.

**[6]** Orocos Project, *Kinematics and Dynamics Library (KDL)*. [En línea]. Disponible: [https://www.orocos.org/kdl.html](https://www.orocos.org/kdl.html)

**[7]** D. Coleman, I. A. Şucan, S. Chitta y N. Correll, "Reducing the barrier to entry of complex robotic software: a MoveIt! case study," *Journal of Software Engineering for Robotics*, vol. 5, no. 1, pp. 3–16, 2014, arXiv: 1404.3785.

**[8]** PickNik Robotics, *MoveIt 2 Documentation – Humble*. [En línea]. Disponible: [https://moveit.picknik.ai/humble/](https://moveit.picknik.ai/humble/)

**[9]** I. A. Şucan, M. Moll y L. E. Kavraki, "The Open Motion Planning Library," *IEEE Robotics & Automation Magazine*, vol. 19, no. 4, pp. 72–82, 2012, doi: 10.1109/MRA.2012.2205651.

**[10]** J. J. Kuffner y S. M. LaValle, "RRT-Connect: An efficient approach to single-query path planning," en *Proc. IEEE ICRA*, 2000, pp. 995–1001, doi: 10.1109/ROBOT.2000.844730.

**[11]** T. Kunz y M. Stilman, "Time-optimal trajectory generation for path following with bounded acceleration and velocity," en *Robotics: Science and Systems VIII*, 2012, doi: 10.15607/RSS.2012.VIII.027.

**[12]** P. Corke, *Robotics, Vision and Control: Fundamental Algorithms in Python*, 3rd ed. Cham, Switzerland: Springer, 2023, doi: 10.1007/978-3-031-06469-2.

**[13]** J. R. Cháux Cedeño, *robots\_ws – paquetes ROS 2 del curso (repositorio en GitHub, licencia Apache-2.0), 2026. [En línea]. Disponible: https://github.com/jchauxdev/robots\_ws*
