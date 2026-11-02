import os, re, glob, sys
from urllib.parse import quote
ROOT = sys.argv[1]
os.chdir(ROOT)
def title(md):
    t = open(md, encoding='utf-8').readline().strip().lstrip('# ').strip()
    t = re.sub(r'^Documento de Apoyo No\. ', '', t).rstrip('.')
    return t
def link(p, text): return f'[{text}]({quote(p)})'
def docs(port):
    out = []
    for md in glob.glob(port + '/**/*.md', recursive=True):
        if 'md_img' in md: continue
        docx = md[:-3] + '.docx'
        if not os.path.exists(docx): continue
        out.append((md, docx))
    def key(x):
        b = os.path.basename(x[0]); m = re.match(r'(?:DA-)?(\d+)(?:\.(\d+))?', b)
        g = 1 if b.startswith('Guia') else 0
        return (g, int(m.group(1)) if m else 999, int(m.group(2) or 0) if m else 0, x[0])
    return sorted(out, key=key)
L = []
L.append('# JetCobot – Transferencias de conocimiento SENA 2026 (ROS 2 Humble)\n')
L.append('Material de dos transferencias de conocimiento del SENA, diseñadas por Julián René Cháux Cedeño:\n')
L.append('1. **Celda robótica colaborativa con visión artificial**: JetCobot (myCobot 280) con ROS 2 Humble, MoveIt 2, Gazebo y OpenCV/YOLO, de la simulación en el PC al robot real con una NVIDIA Jetson AGX Orin.')
L.append('2. **Robot móvil autónomo de tracción diferencial**: construcción, RoboClaw, ROS 2 Humble en Jetson (Nano, Orin Nano, AGX Orin) o Raspberry Pi, lidar, cámaras, SLAM, Nav2 e integración con la celda del cobot mediante una App web de logística.\n')
L.append('Cada documento de apoyo (DA) está en dos formatos: **`.docx`** (versión oficial, formato GFPI-F-135) y **`.md`**, que se lee directamente en GitHub y permite **copiar y pegar los comandos**. En los bloques de comandos el encabezado indica dónde se ejecutan: **Terminal – PC**, **Terminal – robot** (Jetson o Raspberry Pi) o ambos.\n')
L.append('## Contenido del repositorio\n')
L.append('| Carpeta / archivo | Contenido |\n|---|---|')
items = [('Portafolio_Transferencia_2026', 'Transferencia de la celda del cobot: guía de aprendizaje, DA-01 a DA-17 y `jc_ws.zip` (paquetes `jc_*`).'),
         ('Portafolio_Robot_Movil_2026', 'Transferencia del robot móvil: guía de aprendizaje, carpetas 8 a 21 con sus DA y `mr_ws.zip` (paquetes `mr_*`).'),
         ('JetcobotAppPrincipal_v1', 'Aplicación principal del JetCobot: control del robot, secuencias y cliente OPC UA.'),
         ('JetcobotControlGUI', 'Interfaz gráfica de control del JetCobot: paneles, visión por cámara y diagnóstico.'),
         ('JetcobotOPCUA', 'Comunicación OPC UA entre el JetCobot y un PLC, con un programa de prueba.'),
         ('coordenadasrecogerpieza', 'Pose de recogida de piezas del JetCobot (X, Y, Z, R, P, Y) y distancia del gripper a la cámara.'),
         ('ver_camaras.py', 'Muestra dos cámaras USB lado a lado (OpenCV).'),
         ('tools', 'Herramientas: `docx2md.py` (convierte los DA de Word a Markdown) y `gen_readme.py` (genera este README).'),
         ('habilitarpantalla.txt', 'Configuración para usar la Jetson por acceso remoto sin pantalla conectada.')]
for p, d in items:
    if os.path.exists(p): L.append(f'| {link(p, p)} | {d} |')
L.append('')
L.append('## Espacio de trabajo común: `~/robots_ws`\n')
L.append('Las dos transferencias usan **un solo espacio de trabajo ROS 2, `~/robots_ws`**, en el PC y en el computador del robot. '
         'El código completo se entrega como **reserva** en dos archivos comprimidos; cada DA, en su **Paso 0**, copia de la reserva solo los paquetes que usa.\n')
L.append('**Terminal – PC y robot**\n')
L.append('```bash\nREPO=https://raw.githubusercontent.com/jchauxdev/JetCobot/main\n# cobot (DA-02)\nmkdir -p ~/jc_reserva && cd ~/jc_reserva\nwget $REPO/Portafolio_Transferencia_2026/jc_ws.zip && unzip jc_ws.zip\n'
         '# robot móvil (DA-9.1)\nmkdir -p ~/mr_reserva && cd ~/mr_reserva\nwget $REPO/Portafolio_Robot_Movil_2026/mr_ws.zip && unzip mr_ws.zip\n'
         '# espacio de trabajo común (vacío al inicio)\nmkdir -p ~/robots_ws/src && cd ~/robots_ws && colcon build\n```\n')
L.append('Para saber qué espacio de trabajo está activo en una terminal (equivalente de `roscd` en ROS 1): `printenv COLCON_PREFIX_PATH`, `ros2 pkg prefix <paquete>` y `colcon_cd` (DA-02, Paso 7.1, y DA-9.1, Paso 6).\n')
for port, name in (('Portafolio_Transferencia_2026', 'Transferencia 1 – Celda robótica colaborativa (JetCobot)'),
                   ('Portafolio_Robot_Movil_2026', 'Transferencia 2 – Robot móvil autónomo')):
    L.append(f'## {name}\n')
    L.append('| Documento | Markdown (copiar comandos) | Word |\n|---|---|---|')
    for md, docx in docs(port):
        b = os.path.basename(md)[:-3]
        sub = os.path.relpath(os.path.dirname(md), port)
        t = title(md)
        if b.startswith('Guia'): t = 'Guía de aprendizaje'
        L.append(f'| {t} | {link(md, b + ".md")} | {link(docx, "docx")} |')
    L.append('')
L.append('## Actualizar los `.md` después de editar un `.docx`\n')
L.append('Los `.md` se generan a partir de los `.docx`. Después de modificar un documento en Word, regenérelos desde la carpeta del repositorio (requiere Python 3 con `lxml` y `Pillow`):\n')
L.append('**Terminal – PC**\n')
L.append('```bash\npip install lxml pillow\n# un documento\npython3 tools/docx2md.py "Portafolio_Transferencia_2026/DA-02_Entorno_ROS2_Humble_PC.docx"\n# todos los documentos y este README\nfind Portafolio_Robot_Movil_2026 Portafolio_Transferencia_2026 -name "*.docx" ! -name "~\\$*" ! -path "*REPOSITORIOS*" -print0 | xargs -0 python3 tools/docx2md.py\npython3 tools/gen_readme.py .\n```\n')
L.append('En Windows use `python` en lugar de `python3` y ejecute los comandos en Git Bash.\n')
L.append('## Archivos que no están en el repositorio\n')
L.append('GitHub no acepta archivos de más de 100 MB. No se incluyen:\n')
L.append('- Imágenes de JetPack (carpetas `ISO JETPACK`): descárguelas de [JetPack Archive](https://developer.nvidia.com/embedded/jetpack-archive) '
         '(Jetson Nano: [JetPack 4.6.6](https://developer.nvidia.com/jetpack-sdk-466); Jetson Orin: [JetPack 6.2.3](https://developer.nvidia.com/embedded/jetpack-sdk-623)), como se explica en los DA de la carpeta 11.')
L.append('- Video de configuración del RoboClaw (carpeta 10): disponible con el instructor.\n')
L.append('## Autor\n\nJulián René Cháux Cedeño – SENA, 2026.\n')
open('README.md', 'w', encoding='utf-8').write('\n'.join(L))
print('README.md', len(L), 'líneas')
