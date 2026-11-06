# Documento de Apoyo No. DA-03 – Arquitectura de ROS 2: nodos, tópicos, servicios, acciones, mensajes y parámetros.

> Versión en Markdown del documento de apoyo, para consultar y copiar comandos desde GitHub. El documento de Word (formato GFPI-F-135) no se publica en el repositorio.

**Actividad de Aprendizaje:** Explicar y aplicar los mecanismos de comunicación de ROS 2 (tópicos, servicios, acciones, parámetros, interfaces y lanzadores), seleccionando el patrón adecuado para cada función de una celda robótica.

**Parte de la transferencia:** Parte A – Simulación en el PC.

**Equipo de trabajo:** PC con Ubuntu 22.04 y ROS 2 Humble. No se usa la Jetson ni se energiza el robot.

**Duración Estimada:** 2 horas.

**Sesión:** Día 1 – 03/11/2026, 1:30 p.m. – 3:30 p.m.

**Relación con la Guía de Aprendizaje:** Actividad 3.3.2 (apropiación).

> **PARTE A · TRABAJO EN EL PC (SIMULACIÓN):**
>
> Todo el trabajo de este documento se hace en el **PC** con Ubuntu 22.04 y ROS 2 Humble, con el robot simulado (mock y Gazebo) y, cuando se indique, una cámara USB conectada al PC. **No se usa la Jetson ni se energiza el robot.** Cada bloque de comandos indica **Terminal (PC)**.

## 1. OBJETIVOS DE APRENDIZAJE

- Describir las capas de ROS 2 (rclpy/rclcpp, rcl, rmw, DDS) y el grafo computacional.
- Distinguir tópicos, servicios y acciones por su semántica temporal y elegir el patrón correcto para el cobot.
- Definir interfaces propias (`.msg`, `.srv`, `.action`) y usarlas desde Python.
- Declarar, validar y modificar parámetros en tiempo de ejecución.
- Inspeccionar un sistema en marcha con la CLI de ROS 2, `rqt_graph` y TF2.
- Crear un paquete Python propio y un archivo de lanzamiento (*launch*).

## 2. FUNDAMENTOS

### 2.1 Capas y grafo computacional

ROS 2 organiza el software en **nodos**: procesos (o componentes) con una responsabilidad acotada que se comunican por medio de un *middleware* publicador/suscriptor basado en DDS [3]. A diferencia de ROS 1, no existe un maestro central: el descubrimiento es distribuido, lo que habilita sistemas multi-computador (en la Parte B, la Jetson y el PC) y políticas de calidad de servicio por canal [1]. La Figura 1 resume la pila de software.

![imagen](md_img/DA_03_Arquitectura_ROS2_01.jpg)

*Figura 1. Capas de ROS 2. El código del usuario solo interactúa con rclpy/rclcpp; la implementación DDS se elige con la variable RMW_IMPLEMENTATION. Fuente: elaboración propia a partir de [1], [2].*

El **grafo de ROS** es el conjunto de nodos y de los canales que los conectan en un instante dado. Cada canal tiene un **nombre** (p. ej. `/joint_states`) y un **tipo de interfaz** (p. ej. `sensor_msgs/msg/JointState`). Dos extremos solo se conectan si coinciden nombre, tipo y perfiles QoS compatibles.

### 2.2 Patrones de comunicación

![imagen](md_img/DA_03_Arquitectura_ROS2_02.jpg)

*Figura 2. Tópicos, servicios y acciones con las interfaces didácticas de jc_apps.*

*Tabla 1. Comparación de los mecanismos de comunicación de ROS 2.*

| **Patrón** | **Semántica** | **Cuándo usarlo en la celda** | **Ejemplo en robots\_ws** |
|---|---|---|---|
| Tópico | Flujo continuo, asíncrono, N publicadores : M suscriptores; sin confirmación. | Datos periódicos de sensores y estado. | `/joint_states`, `/camera/image_raw`, `/jc/detections` |
| Servicio | Petición–respuesta, 1:1; el cliente espera el resultado. | Operaciones cortas y atómicas. | `/jc/set_gripper`, `/jetcobot_bridge/power_on` |
| Acción | Meta de larga duración con realimentación periódica, resultado final y **cancelación**. | Movimientos del robot y tareas compuestas. | `/arm_controller/follow_joint_trajectory`, `/jc/pick_place` |
| Parámetro | Configuración con nombre y tipo, propia de cada nodo; modificable en caliente. | Puertos, velocidades, umbrales. | `port`, `baud`, `velocity_scaling`, `plane_z` |

Una acción se implementa internamente con tres servicios (enviar meta, cancelar, obtener resultado) y dos tópicos (realimentación y estado) [2]. Por eso el robot real puede ser comandado por MoveIt 2 y cancelado en mitad de una trayectoria: el puente `jetcobot_bridge` atiende la cancelación con `stop()` del robot.

### 2.3 Calidad de servicio (QoS)

*Tabla 2. Políticas QoS más relevantes.*

| **Política** | **Opciones** | **Uso recomendado** |
|---|---|---|
| Reliability | `reliable` / `best_effort` | Comandos y estado: reliable. Imágenes y sensores de alta tasa: best\_effort (`qos_profile_sensor_data`). |
| Durability | `volatile` / `transient_local` | `/robot_description` usa transient\_local para que nodos que arrancan tarde reciban el URDF. |
| History / Depth | `keep_last(N)` / `keep_all` | Profundidad pequeña (1–10) para datos en tiempo real. |
| Deadline, Lifespan, Liveliness | Períodos y vencimientos | Supervisión de sensores críticos (avanzado). |

> **Precaución:**
>
> Un publicador `best_effort` **no** es compatible con un suscriptor `reliable`: la conexión no se establece y no aparece error explícito. Diagnóstico: `ros2 topic info -v /topico`.

### 2.4 Interfaces: mensajes, servicios y acciones

Las interfaces se describen en archivos de texto y `rosidl` genera el código para C++ y Python. El paquete `jc_interfaces` define las interfaces propias de la celda; por ejemplo:

**jc_interfaces/action/PickPlace.action**

```
# Accion de la celda (Dia 5): recoger el objeto 'label' y dejarlo en 'place_pose'.
string label
geometry_msgs/PoseStamped place_pose
bool use_place_pose         # false => el servidor usa el contenedor asignado a la clase
---
bool success
string message
---
string stage
float32 progress
```

Las tres secciones separadas por `---` son **meta**, **resultado** y **realimentación**. Los paquetes de interfaces deben ser `ament_cmake` y declarar `rosidl_default_generators` (ver `CMakeLists.txt` del paquete).

### 2.5 Marcos de referencia y TF2

TF2 mantiene un árbol de transformaciones entre marcos con marca de tiempo [4]. ROS sigue la convención de REP 103: unidades SI (m, rad, s) y marcos dextrógiros con x adelante, y a la izquierda, z arriba; para cámaras, el marco *óptico* tiene z hacia adelante, x a la derecha e y hacia abajo [5]. `robot_state_publisher` publica el árbol del robot a partir del URDF y de `/joint_states`.

## 3. PROCEDIMIENTO PASO A PASO

### Paso 0. Incorporar al robots_ws el material de este documento

El espacio de trabajo `~/robots_ws` se construye a medida que avanza la transferencia: cada documento incorpora **solo** el material que usa. Agregue desde el repositorio robots\_ws (DA-02, Paso 7) lo siguiente y revise su contenido antes de ejecutarlo:

| **Paquete / carpeta** | **Para qué sirve** | **Qué contiene** | **Dónde se usa** |
|---|---|---|---|
| `src/jc_interfaces` | Define los mensajes, servicios y acciones propios de la celda, para que todos los nodos (visión, movimiento, pick and place) se entiendan con los mismos tipos de datos. | msg/ DetectedObject y DetectedObjectArray; srv/ MoveToNamed, MoveToPose y SetGripper; action/ Countdown y PickPlace. Paquete ament\_cmake: genera las interfaces en C++ y Python al compilar. | PC (Parte A). En la Parte B también en la Jetson AGX Orin (DA-13). Lo usan casi todos los demás paquetes (y mr\_cobot\_bridge en la integración con el robot móvil). |
| `src/jc_apps` | Nodos didácticos en Python para aprender tópicos, servicios, acciones y parámetros; también trae la cinemática, las trayectorias y el pick and place de los DA siguientes. | talker, listener, param\_demo, gripper\_service\_demo, countdown\_server y countdown\_client (DA-03); fk\_check, trajectory\_demo y square\_demo (DA-05, DA-07); pick\_place\_node y launch celda (DA-12); pruebas en test/. | PC (Parte A). En la Parte B también en la Jetson AGX Orin (DA-13). |

**Terminal 1 (PC)**

```bash
# trae lo nuevo del repositorio (correcciones y mejoras)
cd ~/robots_ws && git pull
cd ~/robots_ws && git sparse-checkout add src/jc_interfaces
cd ~/robots_ws && git sparse-checkout add src/jc_apps
# instala las dependencias de los paquetes agregados
rosdep install --from-paths ~/robots_ws/src --ignore-src -r -y --skip-keys "mr_navigation jc_driver"
cd ~/robots_ws
colcon build --symlink-install
source install/setup.bash
# explore la estructura
tree -L 2 src/
# paquetes del workspace hasta ahora
ros2 pkg list | grep -E "jc_|mi_celda"
# equivalentes de roscd (DA-02, Paso 7.1): ahora ya funcionan
ros2 pkg prefix jc_interfaces
colcon_cd jc_interfaces && pwd
```

> **Resultado esperado:**
>
> `Summary: 2 packages finished` (primero `jc_interfaces`, porque `jc_apps` depende de él). Compruebe la interfaz generada con `ros2 interface show jc_interfaces/srv/SetGripper`: debe mostrar `float64 opening`, `---`, `bool success` y `string message`.

Revise `jc_apps/setup.py`: la sección `entry_points` asocia cada ejecutable (`talker`, `listener`, …) con la función `main` de su módulo. Es lo mismo que hará en el Paso 5 con su propio paquete.

### Paso 1. Primer contacto con el grafo

Abra la Terminal 1 y lance el publicador. Déjela ejecutando: imprime un mensaje por cada publicación.

**Terminal 1 (PC) – déjela ejecutando**

```bash
ros2 run jc_apps talker --ros-args -p rate_hz:=2.0
```

Abra la Terminal 2 y lance el suscriptor. Déjela ejecutando: muestra los mensajes que recibe del publicador.

**Terminal 2 (PC) – déjela ejecutando**

```bash
ros2 run jc_apps listener
```

Con las Terminales 1 y 2 ejecutando, abra la Terminal 3 e inspeccione el grafo. ros2 topic hz y ros2 topic echo siguen midiendo hasta que pulse Ctrl + C; rqt\_graph abre una ventana.

**Terminal 3 (PC)**

```bash
ros2 node list
ros2 node info /talker
ros2 topic list -t
ros2 topic info -v /celda/estado
ros2 topic hz /celda/estado
ros2 topic echo /celda/estado --once
ros2 run rqt_graph rqt_graph
```

> **Resultado esperado:**
>
> `ros2 topic hz` reporta ≈ 2,0 Hz. `rqt_graph` muestra `/talker → /celda/estado → /listener`.

![imagen](md_img/DA_03_Arquitectura_ROS2_03.jpg)

Al terminar, detenga el publicador y el suscriptor con Ctrl + C en las Terminales 1 y 2.

Revise el código fuente de `jc_apps/talker.py` (fragmento):

**jc_apps/talker.py**

```
class Talker(Node):
    def __init__(self):
        super().__init__("talker")
        self.declare_parameter("rate_hz", 1.0)
        self.pub = self.create_publisher(String, "/celda/estado", 10)   # profundidad QoS = 10
        self.n = 0
        self.timer = self.create_timer(1.0 / self.get_parameter("rate_hz").value, self.tick)
    def tick(self):
        self.n += 1
        self.pub.publish(String(data=f"celda OK #{self.n}"))
```

### Paso 2. Servicio con interfaz propia

En la Terminal 1 lance el servidor del servicio y déjela ejecutando.

**Terminal 1 (PC) – déjela ejecutando**

```bash
ros2 run jc_apps gripper_service_demo
```

En la Terminal 2 consulte el servicio y llámelo:

**Terminal 2 (PC)**

```bash
ros2 service list -t | grep demo
ros2 service call /demo/set_gripper jc_interfaces/srv/SetGripper "{opening: 0.5}"
# debe rechazarse
ros2 service call /demo/set_gripper jc_interfaces/srv/SetGripper "{opening: 1.7}"
```

> **Resultado esperado:**
>
> `success: true, message: 'Pinza al 50 % (valor pymycobot 50)'`
>
> Con 1.7: `success: false, message: 'opening debe estar en [0, 1]'` (validación en el servidor).

Al terminar, detenga el servidor con Ctrl + C en la Terminal 1.

### Paso 3. Acción con realimentación y cancelación

En la Terminal 1 lance el servidor de la acción y déjela ejecutando.

**Terminal 1 (PC) – déjela ejecutando**

```bash
ros2 run jc_apps countdown_server
```

En la Terminal 2 envíe metas a la acción:

**Terminal 2 (PC)**

```bash
ros2 action list -t
ros2 action send_goal --feedback /demo/countdown jc_interfaces/action/Countdown "{seconds: 5}"
# cliente en Python; pruebe Ctrl+C para cancelar
ros2 run jc_apps countdown_client 8
```

Analice en `countdown_server.py` el uso de `gh.publish_feedback()`, `gh.is_cancel_requested`, `gh.canceled()` y `gh.succeed()`, y por qué se usa un `MultiThreadedExecutor`: mientras la meta se ejecuta, el servidor debe seguir atendiendo la petición de cancelación.

Al terminar, detenga el servidor con Ctrl + C en la Terminal 1.

### Paso 4. Parámetros

En la Terminal 1 lance el nodo con parámetros y déjela ejecutando.

**Terminal 1 (PC) – déjela ejecutando**

```bash
ros2 run jc_apps param_demo
```

En la Terminal 2 consulte y cambie sus parámetros:

**Terminal 2 (PC)**

```bash
ros2 param list /param_demo
ros2 param describe /param_demo velocidad
# aceptado
ros2 param set /param_demo velocidad 0.5
# rechazado: fuera de [0.01, 1.0]
ros2 param set /param_demo velocidad 2.0
# aceptado por la validación del callback
ros2 param set /param_demo modo real
# exporta a YAML
ros2 param dump /param_demo > param_demo.yaml
```

Al terminar, detenga el nodo con Ctrl + C en la Terminal 1.

### Paso 5. Crear su propio paquete

En la Terminal 1 cree el paquete y abra los dos archivos que va a editar:

**Terminal 1 (PC)**

```bash
cd ~/robots_ws/src
ros2 pkg create --build-type ament_python mi_celda --dependencies rclpy sensor_msgs
# archivo del nodo: pegue el código de monitor.py (abajo) y guarde
gedit ~/robots_ws/src/mi_celda/mi_celda/monitor.py
# registre el ejecutable: setup.py debe quedar como se muestra abajo
gedit ~/robots_ws/src/mi_celda/setup.py
```

**mi_celda/mi_celda/monitor.py**

```
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
class Monitor(Node):
    """Avisa cuando alguna articulacion se acerca a menos de 'margen_deg' de su limite."""
    LIM = {"joint1": 168, "joint2": 135, "joint3": 150, "joint4": 145, "joint5": 155, "joint6": 180}
    def __init__(self):
        super().__init__("monitor_limites")
        self.margen = self.declare_parameter("margen_deg", 10.0).value
        self.create_subscription(JointState, "/joint_states", self.cb, 10)
    def cb(self, msg):
        for n, q in zip(msg.name, msg.position):
            if n in self.LIM and abs(math.degrees(q)) > self.LIM[n] - self.margen:
                self.get_logger().warn(f"{n} a {math.degrees(q):.1f} grados: cerca del limite",
                                       throttle_duration_sec=1.0)
def main():
    rclpy.init()
    rclpy.spin(Monitor())
```

ros2 pkg create ya generó setup.py; solo hay que completar entry\_points. Cada línea de console\_scripts crea un ejecutable: monitor = mi\_celda.monitor:main significa «el comando monitor ejecuta la función main del archivo mi\_celda/monitor.py». El archivo completo queda así (maintainer, correo, descripción y licencia pueden ser los suyos):

**mi_celda/setup.py (así debe quedar en el Paso 5)**

```
from setuptools import find_packages, setup
package_name = 'mi_celda'
setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='su_nombre',
    maintainer_email='su_correo@ejemplo.com',
    description='Paquete propio de la celda',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # ejecutable = paquete.modulo:funcion
            'monitor = mi_celda.monitor:main',
        ],
    },
)
```

Guarde los dos archivos y, en la Terminal 1, compile solo este paquete, cargue el workspace y ejecute el nodo:

**Terminal 1 (PC)**

```bash
cd ~/robots_ws && colcon build --packages-select mi_celda
source install/setup.bash
# Ctrl + C para detenerlo
ros2 run mi_celda monitor
```

> **Resultado esperado:**
>
> colcon termina con Summary: 1 package finished. El nodo queda esperando sin mostrar nada, porque todavía nadie publica /joint\_states; ros2 node list, en otra terminal, muestra /monitor\_limites. Si aparece «No executable found», revise la línea de entry\_points y vuelva a compilar.

### Paso 6. Archivo de lanzamiento

Un archivo de lanzamiento arranca varios nodos con un solo comando. En la Terminal 1 cree la carpeta launch y el archivo, y pegue el contenido de abajo:

**Terminal 1 (PC)**

```bash
mkdir -p ~/robots_ws/src/mi_celda/launch
gedit ~/robots_ws/src/mi_celda/launch/demo.launch.py
```

**mi_celda/launch/demo.launch.py**

```
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([
        Node(package="jc_apps", executable="talker", parameters=[{"rate_hz": 5.0}]),
        Node(package="jc_apps", executable="listener"),
        Node(package="mi_celda", executable="monitor", parameters=[{"margen_deg": 15.0}]),
    ])
```

colcon solo instala lo que setup.py le indica, y ros2 launch busca los archivos en share/mi\_celda/launch del workspace instalado. Por eso setup.py necesita dos cambios: importar os y glob al inicio, y agregar en data\_files la línea que copia launch/\*.launch.py. Abra el archivo (gedit ~/robots\_ws/src/mi\_celda/setup.py) y déjelo así; las líneas marcadas con NUEVO son las que cambian respecto al Paso 5:

**mi_celda/setup.py (así debe quedar en el Paso 6)**

```
import os                                   # NUEVO (Paso 6)
from glob import glob                       # NUEVO (Paso 6)
from setuptools import find_packages, setup
package_name = 'mi_celda'
setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # NUEVO (Paso 6): instala los archivos de launch/ en share/mi_celda/launch
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='su_nombre',
    maintainer_email='su_correo@ejemplo.com',
    description='Paquete propio de la celda',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # ejecutable = paquete.modulo:funcion
            'monitor = mi_celda.monitor:main',
        ],
    },
)
```

Guarde, compile y lance en la Terminal 1:

**Terminal 1 (PC)**

```bash
cd ~/robots_ws && colcon build --packages-select mi_celda
source install/setup.bash
# arranca los tres nodos; Ctrl + C los detiene todos
ros2 launch mi_celda demo.launch.py
```

> **Resultado esperado:**
>
> En la Terminal 1, ros2 launch informa process started para [talker-1], [listener-2] y [monitor-3], y luego se ven los mensajes de [listener-2], que recibe a 5 Hz lo que publica el talker; el monitor no imprime nada mientras nadie publique /joint\_states. En otra terminal, ros2 node list muestra /talker, /listener y /monitor\_limites. Ctrl + C en la Terminal 1 detiene los tres.

### Paso 7. TF2 con el modelo del robot

Este paso necesita el modelo del robot. Incorpore ahora `jc_description` (se estudia a fondo en DA-04) y ejecute las pruebas unitarias de `jc_apps`, que usan ese modelo:

| **Paquete / carpeta** | **Para qué sirve** | **Qué contiene** | **Dónde se usa** |
|---|---|---|---|
| `src/jc_description` | Modelo del JetCobot de Yahboom en URDF/Xacro: eslabones, articulaciones, límites y pinza. Con él se publican las TF del brazo y se ve en RViz; lo usan MoveIt y Gazebo. | urdf/ jetcobot.urdf.xacro, jetcobot\_macro.xacro, jetcobot.ros2\_control.xacro y jetcobot.gazebo.xacro; config/ros2\_controllers.yaml; launch/display.launch.py; rviz/view.rviz; scripts/importar\_modelo\_yahboom.sh, que instala en meshes/yahboom/ las mallas 3D de Yahboom (no vienen en el repositorio). | PC (Parte A). En la Parte B también en la Jetson AGX Orin (DA-13). Se estudia a fondo en el DA-04. |

Se agrega con estos comandos:

**Terminal 1 (PC)**

```bash
# trae lo nuevo del repositorio (correcciones y mejoras)
cd ~/robots_ws && git pull
cd ~/robots_ws && git sparse-checkout add src/jc_description
# mallas 3D del JetCobot de Yahboom: se descargan aparte porque no están en el repositorio
~/robots_ws/src/jc_description/scripts/importar_modelo_yahboom.sh --descargar
# instala las dependencias de los paquetes agregados
rosdep install --from-paths ~/robots_ws/src --ignore-src -r -y --skip-keys "mr_navigation jc_driver"
cd ~/robots_ws
colcon build --symlink-install
source install/setup.bash
colcon test --packages-select jc_apps && colcon test-result --verbose
```

> **Resultado esperado:**
>
> 3 pruebas de `jc_apps` aprobadas (cinemática directa en cero y en `ready`, ida y vuelta FK→IK, yaw del TCP por simetría). El workspace tiene ahora `jc_interfaces`, `jc_apps`, `jc_description` y `mi_celda`.

> **Nota:**
>
> jc\_description tiene dos formas de dibujar el robot con la misma cinemática: modelo:=yahboom, con las mallas STL de Yahboom, que se ve como el JetCobot real, y modelo:=simple, con cilindros y cajas, que no necesita archivos externos. Los lanzadores eligen solos: si encuentran las mallas instaladas usan yahboom; si no, simple, y lo avisan en la terminal. Si importar\_modelo\_yahboom.sh falla por falta de Internet, el resto del curso funciona igual con el modelo simple.

En la Terminal 1 abra el modelo en RViz2 con los deslizadores de las articulaciones y déjela ejecutando:

**Terminal 1 (PC) – déjela ejecutando**

```bash
ros2 launch jc_description display.launch.py
```

Con la Terminal 1 ejecutando, abra la Terminal 2:

**Terminal 2 (PC)**

```bash
# pose del TCP mientras mueve los deslizadores (Ctrl + C para salir)
ros2 run tf2_ros tf2_echo world tcp
# genera frames_<fecha>.pdf con el árbol de marcos
ros2 run tf2_tools view_frames
```

> **Resultado esperado:**
>
> RViz2 muestra el JetCobot de Yahboom (base, eslabones, pinza y cámara) y se mueve con los deslizadores. Con todos los deslizadores en 0 (botón Center), tf2\_echo world tcp muestra Translation: [0.141, -0.065, 0.414]. Si el brazo se ve con cilindros y cajas, faltan las mallas: ejecute importar\_modelo\_yahboom.sh --descargar y vuelva a compilar.

![imagen](md_img/DA_03_Arquitectura_ROS2_04.jpg)

*Figura 3. Árbol TF del JetCobot generado a partir del URDF de jc_description con modelo:=yahboom (verde: articulaciones de revolución; azul: prismáticas de la pinza; gris: fijas; camera_body solo existe con las mallas de Yahboom).*

## 4. VERIFICACIÓN Y EVIDENCIAS

*Tabla 3. Lista de verificación de la actividad.*

| **#** | **Criterio verificable** | **Evidencia** |
|---|---|---|
| 1 | Identifica nodos, tópicos, tipos y QoS de un sistema en marcha | Salida de `ros2 topic info -v` |
| 2 | Usa correctamente servicios y acciones (incluida la cancelación) | Registro de terminal |
| 3 | Parámetro con validación funcionando | Respuesta de `ros2 param set` rechazada/aceptada |
| 4 | Paquete `mi_celda` compilado con nodo y launch propios | Árbol del paquete + ejecución |
| 5 | Interpreta el árbol TF del robot | PDF de `view_frames` |

## 5. PREGUNTAS DE COMPRENSIÓN

1. ¿Por qué el movimiento del robot se modela como acción y no como servicio? Considere la duración, la realimentación y la cancelación.
1. Un nodo de visión publica imágenes a 30 Hz con QoS `best_effort`. ¿Qué ocurre si `rqt_image_view` se suscribe con `reliable`?
1. ¿Qué ventaja aporta que `/robot_description` use durabilidad `transient_local`?
1. Proponga el diseño de interfaces (tópicos, servicios, acciones) para agregar una banda transportadora a la celda.

## 6. SOLUCIÓN DE PROBLEMAS

*Tabla 4. Problemas frecuentes.*

| **Síntoma** | **Causa probable** | **Solución** |
|---|---|---|
| `Package 'jc_apps' not found` | No se cargó el overlay | `source ~/robots_ws/install/setup.bash` |
| El suscriptor no recibe mensajes | QoS incompatible o dominio distinto | `ros2 topic info -v`; revisar `ROS_DOMAIN_ID` |
| `ros2 action send_goal` queda esperando | Servidor no iniciado / nombre distinto | `ros2 action list -t` |
| Cambios en Python no surten efecto | Compilación sin `--symlink-install` | Recompilar con `--symlink-install` |
| El brazo se ve con cilindros y cajas en RViz2 | No están instaladas las mallas de Yahboom | ~/robots\_ws/src/jc\_description/scripts/importar\_modelo\_yahboom.sh --descargar; colcon build --symlink-install --packages-select jc\_description |
| importar\_modelo\_yahboom.sh: curl: command not found o error de descarga | Falta curl o no hay Internet | sudo apt install -y curl y repetir; sin Internet se usa el modelo simple |
| ros2 launch: file 'demo.launch.py' was not found in the share directory of package 'mi\_celda' | Falta la línea de launch en data\_files de setup.py, o no se volvió a compilar | Revise setup.py (Paso 6), colcon build --packages-select mi\_celda y source install/setup.bash |
| ros2 run mi\_celda monitor: No executable found | Falta 'monitor = mi\_celda.monitor:main' en entry\_points | Corrija setup.py (Paso 5) y vuelva a compilar |

## REFERENCIAS

**[1]** S. Macenski, T. Foote, B. Gerkey, C. Lalancette y W. Woodall, "Robot Operating System 2: Design, architecture, and uses in the wild," *Science Robotics*, vol. 7, no. 66, eabm6074, 2022, doi: 10.1126/scirobotics.abm6074.

**[2]** Open Robotics, *ROS 2 Documentation: Humble Hawksbill*. [En línea]. Disponible: [https://docs.ros.org/en/humble/](https://docs.ros.org/en/humble/)

**[3]** Object Management Group, *Data Distribution Service (DDS), v1.4*, 2015. [En línea]. Disponible: [https://www.omg.org/spec/DDS/1.4](https://www.omg.org/spec/DDS/1.4)

**[4]** T. Foote, "tf: The transform library," en *Proc. IEEE Int. Conf. Technologies for Practical Robot Applications (TePRA)*, 2013, pp. 1–6, doi: 10.1109/TePRA.2013.6556373.

**[5]** T. Foote y M. Purvis, *REP 103 – Standard Units of Measure and Coordinate Conventions*. [En línea]. Disponible: [https://www.ros.org/reps/rep-0103.html](https://www.ros.org/reps/rep-0103.html)

**[6]** J. R. Cháux Cedeño, *robots\_ws – paquetes ROS 2 del curso (repositorio en GitHub, licencia Apache-2.0), 2026. [En línea]. Disponible: https://github.com/jchauxdev/robots\_ws*
