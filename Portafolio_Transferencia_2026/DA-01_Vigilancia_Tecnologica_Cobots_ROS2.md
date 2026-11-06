# Documento de Apoyo No. DA-01 – Vigilancia tecnológica y estado del arte: cobots, visión artificial y ROS 2 en la industria.

> Versión en Markdown del documento de apoyo, para consultar y copiar comandos desde GitHub. El documento de Word (formato GFPI-F-135) no se publica en el repositorio.

**Actividad de Aprendizaje:** Identificar, mediante un ejercicio de vigilancia tecnológica, cómo se usan hoy los robots colaborativos con visión artificial y ROS 2 en la industria, y ubicar la celda de la transferencia frente a ese estado del arte.

**Parte de la transferencia:** Contexto, antes de la Parte A.

**Equipo de trabajo:** PC con navegador web y hoja de cálculo (no requiere ROS ni el robot).

**Duración Estimada:** 1 hora en sesión + 2 horas de trabajo independiente previo.

**Sesión:** Día 1 – 03/11/2026, 9:00 a.m. – 10:00 a.m. (trabajo independiente antes del 03/11/2026).

**Relación con la Guía de Aprendizaje:** Actividad 3.2.1 (contextualización e identificación de conocimientos).

> **CONTEXTO · ANTES DE LA PARTE A:**
>
> Actividad de contexto: se trabaja en el PC con navegador y hoja de cálculo. No requiere ROS 2, la Jetson ni el robot.

Trabajo en equipos de dos o tres participantes. La actividad continúa la introducción a ROS y ROS 2 (actividad 3.1.1 y su presentación): allí se mostraron las cifras de adopción y algunos casos; aquí cada equipo busca, verifica y organiza la información por sí mismo con un método explícito.

## 1. OBJETIVOS DE APRENDIZAJE

- Aplicar las etapas de un proceso de vigilancia tecnológica: necesidad, búsqueda, análisis y comunicación.
- Identificar fabricantes de robots colaborativos e industriales con integración ROS 2 y el tipo de soporte que ofrecen.
- Reconocer las aplicaciones industriales que combinan cobot, visión artificial y ROS 2.
- Relacionar cada capacidad industrial con la parte de la celda JetCobot donde se trabaja durante la transferencia.

## 2. FUNDAMENTOS

### 2.1 ¿Qué es la vigilancia tecnológica?

La vigilancia tecnológica es un proceso **organizado y sistemático** para buscar, captar, analizar y comunicar información sobre tecnologías, con el fin de apoyar decisiones; la norma UNE 166006:2018 la define como parte de un sistema de vigilancia e inteligencia en la gestión de la I+D+i [1]. Se diferencia de una búsqueda ocasional en que define antes **qué se necesita saber**, **dónde** buscar y **cómo** registrar y validar lo encontrado (fuente, fecha y vigencia).

*Tabla 1. Etapas del proceso de vigilancia aplicadas a la actividad.*

| **Etapa** | **Pregunta que responde** | **Producto en esta actividad** |
|---|---|---|
| 1. Necesidad | ¿Qué decisión queremos apoyar? | Pregunta de vigilancia del equipo (Paso 1) |
| 2. Búsqueda | ¿Dónde está la información confiable? | Lista de fuentes y palabras clave |
| 3. Análisis | ¿Qué significa lo encontrado y qué tan vigente es? | Matriz de vigilancia (Tabla 4) |
| 4. Comunicación | ¿Qué conclusiones compartimos? | Análisis de brechas (Tabla 5) y conclusiones |

### 2.2 Fuentes recomendadas

*Tabla 2. Fuentes para la vigilancia de cobots con ROS 2.*

| **Tipo de fuente** | **Ejemplos** | **Qué aporta** |
|---|---|---|
| Comunidad ROS | Open Robotics Discourse (anuncios, reporte anual de métricas) [2]; ROS-Industrial [9] | Adopción, drivers nuevos, paquetes industriales |
| Fabricantes | Documentación y repositorios oficiales de drivers ROS 2 (p. ej. [5], [6]) | Modelos soportados, distribución de ROS 2, mantenimiento |
| Literatura científica | IEEE Xplore, Scopus, Google Scholar; artículo de referencia de ROS 2 [11] | Casos de uso evaluados y comparaciones |
| Patentes | Google Patents, WIPO Patentscope (búsqueda por «collaborative robot» + «vision») | Tendencias de desarrollo tecnológico |
| Normas | ISO 10218-1/-2:2025 e ISO/TS 15066 [12], [13] | Requisitos de seguridad de aplicaciones con cobots |
| Plataformas de cómputo | NVIDIA Isaac ROS (percepción acelerada en Jetson) [10] | Integración de IA con ROS 2 |

> **Precaución:**
>
> Registre siempre la **fecha de consulta**: la información de drivers y versiones cambia en pocos meses. Prefiera la fuente primaria (fabricante, repositorio oficial, anuncio de Open Robotics) a blogs o videos de terceros, y marque como «sin verificar» lo que no pueda confirmar.

### 2.3 Punto de partida verificado

Los siguientes datos se verificaron en las fuentes citadas (consulta: octubre de 2026) y sirven como punto de partida; cada equipo debe ampliarlos y verificarlos de nuevo:

*Tabla 3. Hechos de partida para la vigilancia.*

| **Hecho** | **Fuente** |
|---|---|
| En 2025 se descargaron ≈ 984 millones de paquetes ROS (+85 %); el 91,2 % de las descargas de octubre fueron de ROS 2; Open Robotics registra 1 579 empresas que usan ROS (+26 %). | [2] |
| Humble (48,5 %) y Jazzy (24,5 %) concentran la mayoría de las descargas de ROS. | [2] |
| Universal Robots desarrolla y documenta su propio driver ROS 2. | [5] |
| FANUC publicó en agosto de 2025 su interfaz ROS 2; Kawasaki también publicó la suya. | [3], [6] |
| En septiembre de 2025 se anunciaron drivers ROS 2 soportados por el fabricante para FANUC, Kawasaki, Neura, Kassow, Delta, Dorna, Aubo, Fairino y Hanwha. | [4] |
| KUKA mantiene drivers ROS 2 (kuka\_drivers) y Yaskawa ofrece MotoROS2, que corre en el controlador del robot. | [7], [8] |

Aplicaciones industriales típicas donde se combinan cobot, visión y ROS 2: recogida y depósito guiados por visión (*pick and place*), alimentación de máquinas (*machine tending*), paletizado, inspección de calidad, ensamble con localización de piezas y logística interna con robots móviles. La celda JetCobot de esta transferencia es un **modelo a escala** de la primera: localizar piezas con una cámara y moverlas con un brazo planificado por MoveIt 2.

## 3. PROCEDIMIENTO

### Paso 1. Definir la pregunta de vigilancia (trabajo independiente previo)

Cada equipo redacta una pregunta concreta, por ejemplo: «¿Qué cobots con driver ROS 2 oficial se usan en aplicaciones de recogida guiada por visión y con qué distribución de ROS 2 trabajan?». Defina 5–8 palabras clave en español e inglés (p. ej. *collaborative robot*, *ROS 2 driver*, *MoveIt 2*, *bin picking*, *vision-guided*).

### Paso 2. Buscar y registrar (trabajo independiente previo, 2 horas)

Complete al menos **6 filas** de la matriz (Tabla 4): 4 fabricantes de cobots o robots industriales y 2 casos de aplicación documentados. Use las fuentes de la Tabla 2 y anote la fecha de consulta.

*Tabla 4. Matriz de vigilancia tecnológica (diligenciar).*

| **Fabricante / modelo** | **Carga útil / alcance** | **Driver ROS 2 (oficial o comunidad) y distribución** | **MoveIt 2 / ros2\_control** | **Visión usada** | **Aplicación documentada** | **Fuente y fecha** |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |

### Paso 3. Socializar y comparar (sesión, 25 minutos)

1. Cada equipo presenta en 3 minutos su pregunta, sus fuentes y los dos hallazgos más relevantes.
1. El grupo consolida una sola matriz y señala la información contradictoria o sin verificar.
1. Se discute: ¿qué distribución de ROS 2 predomina en los drivers industriales? ¿qué tan frecuente es la visión integrada? ¿qué papel tiene la simulación antes de la puesta en marcha?

### Paso 4. Análisis de brechas frente a la celda (sesión, 25 minutos)

Relacione cada capacidad industrial con su equivalente en la celda JetCobot y con el documento donde se trabaja. Las primeras filas están diligenciadas como ejemplo:

*Tabla 5. Análisis de brechas: de la industria a la celda (completar).*

| **Capacidad en la industria** | **Equivalente en la celda JetCobot** | **Parte y documento** | **Brecha / limitación de la celda** |
|---|---|---|---|
| Recogida guiada por visión | Detección de piezas o frutas y pick & place | A: DA-10, DA-12 · B: DA-16, DA-17 | Carga útil y precisión menores |
| Calibración cámara–robot | Calibración mano-ojo (AX = XB) | A: DA-09 (sim) · B: DA-16 (real) |  |
| Planificación libre de colisiones | MoveIt 2 con escena de planificación | A: DA-05 |  |
| Puesta en marcha virtual | Gazebo con ros2\_control | A: DA-06, DA-12 |  |
| Detección con IA en el borde | YOLO en el PC y TensorRT en la Jetson | A: DA-11 · B: DA-16 |  |
| Seguridad colaborativa | Protocolo de seguridad, parada y velocidad limitada | B: DA-14, DA-17 |  |
|  |  |  |  |

Cierre: el equipo redacta **tres conclusiones** que orientan la semana (por ejemplo, qué capacidad industrial quiere demostrar con mayor rigor en su proyecto final).

## 4. VERIFICACIÓN Y EVIDENCIAS

*Tabla 6. Evidencias de la actividad.*

| **#** | **Criterio** | **Evidencia** |
|---|---|---|
| 1 | Pregunta de vigilancia y palabras clave definidas | Texto del Paso 1 |
| 2 | Matriz con ≥ 6 filas, cada una con fuente primaria y fecha de consulta | Tabla 4 |
| 3 | Información contradictoria o sin verificar identificada | Matriz consolidada del grupo |
| 4 | Análisis de brechas completo y tres conclusiones | Tabla 5 + conclusiones |

## REFERENCIAS

**[1]** AENOR, *UNE 166006:2018 – Gestión de la I+D+i: Sistema de vigilancia e inteligencia*. Madrid: AENOR, 2018.

**[2]** K. Scott, *2025 ROS Metrics Report*, Open Robotics Discourse, 19 feb. 2026. [En línea]. Disponible: [https://discourse.openrobotics.org/t/2025-ros-metrics-report/52575](https://discourse.openrobotics.org/t/2025-ros-metrics-report/52575)

**[3]** Open Robotics, *OEM Supported ROS 2 Driver Releases*, Open Robotics Discourse, ago. 2025. [En línea]. Disponible: [https://discourse.openrobotics.org/t/oem-supported-ros-2-driver-releases/49646](https://discourse.openrobotics.org/t/oem-supported-ros-2-driver-releases/49646)

**[4]** Open Robotics, *Nine More Robot Arms Now Have ROS 2 Drivers, Including FANUC and Kawasaki*, Open Robotics Discourse, sep. 2025. [En línea]. Disponible: [https://discourse.openrobotics.org/t/nine-more-robot-arms-now-have-ros-2-drivers-including-fanuc-and-kawasaki/50156](https://discourse.openrobotics.org/t/nine-more-robot-arms-now-have-ros-2-drivers-including-fanuc-and-kawasaki/50156)

**[5]** Universal Robots, *Universal Robots ROS 2 Driver Documentation*. [En línea]. Disponible: [https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/)

**[6]** FANUC America, *ROS 2 Driver*. [En línea]. Disponible: [https://fanucamerica.com/solutions/ros-2](https://fanucamerica.com/solutions/ros-2)

**[7]** KUKA, *kuka\_drivers: ROS 2 drivers for KUKA robots*. [En línea]. Disponible: [https://github.com/kroshu/kuka_drivers](https://github.com/kroshu/kuka_drivers)

**[8]** Yaskawa, *MotoROS2: ROS 2 interface for Yaskawa Motoman robot controllers*. [En línea]. Disponible: [https://github.com/Yaskawa-Global/motoros2](https://github.com/Yaskawa-Global/motoros2)

**[9]** ROS-Industrial Consortium, *ROS-Industrial*. [En línea]. Disponible: [https://rosindustrial.org](https://rosindustrial.org)

**[10]** NVIDIA, *Isaac ROS*. [En línea]. Disponible: [https://developer.nvidia.com/isaac/ros](https://developer.nvidia.com/isaac/ros)

**[11]** S. Macenski, T. Foote, B. Gerkey, C. Lalancette y W. Woodall, "Robot Operating System 2: Design, architecture, and uses in the wild," *Science Robotics*, vol. 7, no. 66, eabm6074, 2022, doi: 10.1126/scirobotics.abm6074.

**[12]** International Organization for Standardization, *ISO 10218-1:2025 y ISO 10218-2:2025, Robotics — Safety requirements — Part 1: Industrial robots; Part 2: Industrial robot applications and robot cells*. Ginebra: ISO, 2025.

**[13]** International Organization for Standardization, *ISO/TS 15066:2016, Robots and robotic devices — Collaborative robots*. Ginebra: ISO, 2016.

**[14]** J. R. Cháux Cedeño, *robots\_ws – paquetes ROS 2 del curso (repositorio en GitHub, licencia Apache-2.0), 2026. [En línea]. Disponible: https://github.com/jchauxdev/robots\_ws*
