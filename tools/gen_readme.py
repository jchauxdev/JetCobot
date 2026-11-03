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
L.append('Cada documento de apoyo (DA) se publica en **`.md`**, que se lee directamente en GitHub y permite **copiar y pegar los comandos**. Los `.docx` (versión oficial, formato GFPI-F-135) y los `.pdf` no se suben al repositorio. En los bloques de comandos el encabezado indica dónde se ejecutan: **Terminal – PC**, **Terminal – robot** (Jetson o Raspberry Pi) o ambos.\n')
L.append('## Contenido del repositorio\n')
L.append('Los paquetes ROS 2 (`mr_*` y `jc_*`) están en el repositorio aparte [jchauxdev/robots_ws](https://github.com/jchauxdev/robots_ws).\n')
L.append('| Carpeta / archivo | Contenido |\n|---|---|')
items = [('Portafolio_Transferencia_2026', 'Transferencia de la celda del cobot: guía de aprendizaje y DA-01 a DA-17.'),
         ('Portafolio_Robot_Movil_2026', 'Transferencia del robot móvil: guía de aprendizaje y carpetas 8 a 21 con sus DA.'),
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
L.append('Los paquetes ROS 2 de las dos transferencias están en el repositorio **[jchauxdev/robots_ws](https://github.com/jchauxdev/robots_ws)**. '
         'Ese repositorio **es** el espacio de trabajo `~/robots_ws`: se clona vacío una vez por equipo y cada DA, en su **Paso 0**, '
         'agrega solo los paquetes que usa. Las correcciones del instructor se reciben con `git pull`.\n')
L.append('**Terminal – PC y computadores del robot con Ubuntu 22.04 (Orin Nano, AGX Orin, Raspberry Pi)**\n')
L.append('```bash\nsudo apt install -y git\ngit clone --filter=blob:none --sparse https://github.com/jchauxdev/robots_ws.git ~/robots_ws\n'
         'mkdir -p ~/robots_ws/src && cd ~/robots_ws && colcon build\n# Paso 0 de cada DA (ejemplo): agregar paquetes\n'
         'git sparse-checkout add src/mr_base src/mr_sim\n# recibir correcciones\ngit pull\n```\n')
L.append('La Jetson Nano (Ubuntu 18.04, git 2.17) usa el método clásico de sparse-checkout descrito en su DA-11.2.\n')
L.append('Para saber qué espacio de trabajo está activo en una terminal (equivalente de `roscd` en ROS 1): `printenv COLCON_PREFIX_PATH`, `ros2 pkg prefix <paquete>` y `colcon_cd` (DA-02, Paso 7.1, y DA-9.1, Paso 5).\n')
for port, name in (('Portafolio_Transferencia_2026', 'Transferencia 1 – Celda robótica colaborativa (JetCobot)'),
                   ('Portafolio_Robot_Movil_2026', 'Transferencia 2 – Robot móvil autónomo')):
    L.append(f'## {name}\n')
    L.append('| Documento | Markdown (copiar comandos) |\n|---|---|')
    for md, docx in docs(port):
        b = os.path.basename(md)[:-3]
        sub = os.path.relpath(os.path.dirname(md), port)
        t = title(md)
        if b.startswith('Guia'): t = 'Guía de aprendizaje'
        L.append(f'| {t} | {link(md, b + ".md")} |')
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
