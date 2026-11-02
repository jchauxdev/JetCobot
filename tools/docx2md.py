"""Convierte los documentos de apoyo (.docx) a Markdown para leerlos y copiar comandos en GitHub.

Uso: python3 docx2md.py <archivo.docx> [...]   -> escribe <archivo>.md y las imágenes en <carpeta>/md_img/
"""
import sys, os, re, io, zipfile
from lxml import etree
from PIL import Image

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
MM = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
q = lambda t: '{%s}%s' % (W, t)  # noqa: E731
SKIP_START = ('PROCESO DE GESTIÓN DE FORMACIÓN', 'Nombre del participante')


def slug(s):
    s = re.sub(r'\.docx$', '', s)
    s = s.translate(str.maketrans('áéíóúÁÉÍÓÚñÑü', 'aeiouAEIOUnNu'))
    return re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')[:40]



def omml(el):
    """OMML -> LaTeX (subconjunto: fracciones, subíndices, superíndices, raíces, delimitadores, sumatorias)."""
    m = lambda t: '{%s}%s' % (MM, t)  # noqa: E731
    def kids(e, tag):
        x = e.find(m(tag)); return conv(x) if x is not None else ''
    def conv(e):
        out = []
        for c in e:
            t = c.tag
            if t == m('r'): out.append(''.join(x.text or '' for x in c.iter(m('t'))))
            elif t == m('f'): out.append('\\frac{%s}{%s}' % (kids(c, 'num'), kids(c, 'den')))
            elif t == m('sSub'): out.append('{%s}_{%s}' % (kids(c, 'e'), kids(c, 'sub')))
            elif t == m('sSup'): out.append('{%s}^{%s}' % (kids(c, 'e'), kids(c, 'sup')))
            elif t == m('sSubSup'): out.append('{%s}_{%s}^{%s}' % (kids(c, 'e'), kids(c, 'sub'), kids(c, 'sup')))
            elif t == m('rad'): out.append('\\sqrt{%s}' % kids(c, 'e'))
            elif t == m('d'):
                pr = c.find(m('dPr')); b = pr.find(m('begChr')) if pr is not None else None; e2 = pr.find(m('endChr')) if pr is not None else None
                bc = b.get(m('val')) if b is not None else '('; ec = e2.get(m('val')) if e2 is not None else ')'
                inner = ', '.join(conv(x) for x in c.findall(m('e')))
                out.append('\\left%s %s \\right%s' % (bc if bc not in '{}' else '\\' + bc, inner, ec if ec not in '{}' else '\\' + ec))
            elif t == m('nary'):
                pr = c.find(m('naryPr')); ch = pr.find(m('chr')) if pr is not None else None
                op = {'∑': '\\sum', '∏': '\\prod', '∫': '\\int'}.get(ch.get(m('val')) if ch is not None else '∫', '\\int')
                out.append('%s_{%s}^{%s} %s' % (op, kids(c, 'sub'), kids(c, 'sup'), kids(c, 'e')))
            elif t == m('func'): out.append('\\%s %s' % (kids(c, 'fName').strip(), kids(c, 'e')) if kids(c, 'fName').strip() in ('sin', 'cos', 'tan', 'log', 'ln', 'exp', 'atan2', 'arctan') else kids(c, 'fName') + kids(c, 'e'))
            elif t in (m('acc'), m('bar')): out.append('\\bar{%s}' % kids(c, 'e'))
            elif t in (m('e'), m('num'), m('den'), m('oMath'), m('box'), m('borderBox'), m('groupChr'), m('limLow'), m('limUpp'), m('eqArr')):
                out.append(conv(c))
        s = ''.join(out)
        for a, b in (('ω', '\\omega '), ('θ', '\\theta '), ('Δ', '\\Delta '), ('π', '\\pi '), ('⋅', '\\cdot '), ('·', '\\cdot '), ('−', '-'), ('±', '\\pm '), ('≤', '\\le '), ('≥', '\\ge '), ('→', '\\to '), ('α', '\\alpha '), ('β', '\\beta '), ('μ', '\\mu ')):
            s = s.replace(a, b)
        return s
    return conv(el)


class Conv:
    def __init__(s, path):
        s.path = path
        z = zipfile.ZipFile(path); s.z = z
        s.doc = etree.fromstring(z.read('word/document.xml'))
        s.rels = {r.get('Id'): (r.get('Target'), r.get('TargetMode')) for r in
                  etree.fromstring(z.read('word/_rels/document.xml.rels'))}
        s.numfmt = {}
        if 'word/numbering.xml' in z.namelist():
            nb = etree.fromstring(z.read('word/numbering.xml'))
            absf = {}
            for a in nb.findall(q('abstractNum')):
                lv = a.find(q('lvl') + '/' + q('numFmt'))
                absf[a.get(q('abstractNumId'))] = lv.get(q('val')) if lv is not None else 'bullet'
            for n in nb.findall(q('num')):
                a = n.find(q('abstractNumId'))
                s.numfmt[n.get(q('numId'))] = absf.get(a.get(q('val')) if a is not None else '', 'bullet')
        s.dir = os.path.dirname(os.path.abspath(path)); s.base = os.path.basename(path)
        s.imgdir = os.path.join(s.dir, 'md_img'); s.nimg = 0; s.out = []; s.counters = {}

    # ---------------------------------------------------------------- texto en línea
    @staticmethod
    def rfmt(r):
        rp = r.find(q('rPr'))
        if rp is None: return (False, False, False)
        f = rp.find(q('rFonts')); code = f is not None and 'Consolas' in (f.get(q('ascii')) or '') + (f.get(q('hAnsi')) or '')
        b = rp.find(q('b')) is not None and rp.find(q('b')).get(q('val')) not in ('0', 'false')
        i = rp.find(q('i')) is not None and rp.find(q('i')).get(q('val')) not in ('0', 'false')
        return (code, b, i)

    def runs(s, p):
        """Lista de (texto, (code,b,i), link)."""
        out = []
        for el in p:
            if el.tag == q('r'):
                t = ''.join((x.text or '') if x.tag == q('t') else ('\t' if x.tag == q('tab') else '')
                            for x in el if x.tag in (q('t'), q('tab')))
                if t: out.append((t, s.rfmt(el), None))
            elif el.tag == q('hyperlink'):
                rid = el.get('{%s}id' % R); url = s.rels.get(rid, (None,))[0] if rid else None
                for r in el.iter(q('r')):
                    t = ''.join(x.text or '' for x in r.iter(q('t')))
                    if t: out.append((t, s.rfmt(r), url))
            elif el.tag in (q('ins'), q('smartTag'), q('sdt')):
                out += s.runs(el.find(q('sdtContent')) if el.tag == q('sdt') and el.find(q('sdtContent')) is not None else el)
            elif el.tag == '{%s}oMath' % MM or el.tag == '{%s}oMathPara' % MM:
                maths = [el] if el.tag == '{%s}oMath' % MM else el.findall('{%s}oMath' % MM)
                t = ' \\quad '.join(omml(x) for x in maths).strip()
                if t: out.append((t, ('math', False, False), None))
        return out

    @staticmethod
    def inline(runs):
        # agrupa por formato
        groups = []
        for t, f, link in runs:
            if groups and groups[-1][1] == f and groups[-1][2] == link: groups[-1][0] += t
            else: groups.append([t, f, link])
        out = []
        for t, (code, b, i), link in groups:
            if not t.strip(): out.append(t); continue
            lead = t[:len(t) - len(t.lstrip())]; trail = t[len(t.rstrip()):]; core = t.strip()
            if code == 'math':
                core = f'$${core}$$' if len(groups) <= 2 else f'${core}$'
            elif code:
                tick = '``' if '`' in core else '`'
                core = f'{tick}{core}{tick}'
            else:
                core = (core.replace('*', '\\*').replace('_', '\\_') if not link else core).replace('<', '&lt;').replace('>', '&gt;')
                if b and i: core = f'***{core}***'
                elif b: core = f'**{core}**'
                elif i: core = f'*{core}*'
            if link and link.startswith('http'): core = f'[{core}]({link})'
            out.append(lead + core + trail)
        txt = ''.join(out)
        return re.sub(r'\*\*\s*\*\*', '', txt)

    def ptext(s, p): return ''.join(t for t, _, _ in s.runs(p))

    # ---------------------------------------------------------------- imágenes
    def images(s, el):
        res = []
        for blip in el.iter('{%s}blip' % A):
            rid = blip.get('{%s}embed' % R)
            tgt = s.rels.get(rid, (None,))[0]
            if not tgt: continue
            try: data = s.z.read('word/' + tgt.lstrip('/').replace('../', ''))
            except KeyError: continue
            s.nimg += 1
            os.makedirs(s.imgdir, exist_ok=True)
            name = f'{slug(s.base)}_{s.nimg:02d}.jpg'
            try:
                im = Image.open(io.BytesIO(data))
                if im.mode in ('RGBA', 'LA', 'P'):
                    im = im.convert('RGBA'); bg = Image.new('RGB', im.size, 'white'); bg.paste(im, mask=im.split()[-1]); im = bg
                im = im.convert('RGB'); im.thumbnail((1100, 1100)); im.save(os.path.join(s.imgdir, name), 'JPEG', quality=80)
            except Exception:
                continue
            res.append(f'md_img/{name}')
        return res

    # ---------------------------------------------------------------- bloques
    def emit(s, x=''): s.out.append(x)

    def para(s, p, in_list_prev):
        ppr = p.find(q('pPr'))
        txt = s.ptext(p).strip()
        imgs = s.images(p)
        if imgs:
            for im in imgs: s.emit(f'![imagen]({im})'); s.emit()
            if txt: s.emit(s.inline(s.runs(p)).strip()); s.emit()
            return False
        if not txt: return False
        if txt.startswith(SKIP_START): return False
        lvl = None
        if ppr is not None:
            ol = ppr.find(q('outlineLvl'))
            if ol is not None: lvl = int(ol.get(q('val')))
            st = ppr.find(q('pStyle'))
            if st is not None:
                m = re.search(r'(?:Heading|Ttulo|Titulo|Título)\s*(\d)', st.get(q('val')) or '')
                if m: lvl = int(m.group(1)) - 1
        if txt.startswith('Documento de Apoyo No.') or txt.startswith('FORMATO GUÍA DE APRENDIZAJE'):
            s.emit('# ' + txt); s.emit(); return False
        if lvl is not None and lvl <= 3:
            s.emit('#' * (lvl + 2) + ' ' + txt.replace('<', '&lt;')); s.emit(); return False
        if re.match(r'^(Figura|Tabla) \d+\. ', txt):
            s.emit('*' + txt.replace('*', '\\*').replace('<', '&lt;') + '*'); s.emit(); return False
        rr = s.runs(p)
        mth = [t for t, f, _ in rr if f[0] == 'math']; rest = ''.join(t for t, f, _ in rr if f[0] != 'math').strip()
        if mth and re.fullmatch(r'(\(\d+\))?', rest):
            s.emit('$$' + ' \\quad '.join(mth) + (' \\qquad ' + rest if rest else '') + '$$'); s.emit(); return False
        np = ppr.find(q('numPr')) if ppr is not None else None
        body = s.inline(rr).strip()
        if np is not None and np.find(q('numId')) is not None and np.find(q('numId')).get(q('val')) != '0':
            il = np.find(q('ilvl')); il = int(il.get(q('val'))) if il is not None else 0
            fmt = s.numfmt.get(np.find(q('numId')).get(q('val')), 'bullet')
            mark = '1.' if fmt not in ('bullet', 'none') else '-'
            s.emit('   ' * il + f'{mark} {body}')
            return True
        if in_list_prev: s.emit()
        s.emit(body); s.emit(); return False

    def cell_paras(s, tc): return tc.findall(q('p'))

    @staticmethod
    def is_cons(p):
        f = p.find('.//' + q('rFonts')); return f is not None and 'Consolas' in (f.get(q('ascii')) or '')

    def table(s, tbl):
        rows = tbl.findall(q('tr'))
        tcs = tbl.findall('.//' + q('tc'))
        # imágenes dentro de tablas (pares de figuras)
        if tbl.find('.//{%s}blip' % A) is not None:
            for tc in tcs:
                for p in tc.findall(q('p')):
                    for im in s.images(p): s.emit(f'![imagen]({im})'); s.emit()
                    t = s.ptext(p).strip()
                    if t: s.emit('*' + t.replace('*', '\\*') + '*' if re.match(r'^Figura \d+', t) else s.inline(s.runs(p)).strip()); s.emit()
            return
        if len(tcs) == 1:
            tc = tcs[0]; shd = tc.find(q('tcPr') + '/' + q('shd'))
            fill = (shd.get(q('fill')) or '').upper() if shd is not None else ''
            ps = s.cell_paras(tc)
            if fill == 'F4F4F4':
                title = None; lines = []
                for k, p in enumerate(ps):
                    t = s.ptext(p)
                    if k == 0 and not s.is_cons(p) and t.strip(): title = t.strip(); continue
                    if not t.strip(): continue
                    ind = p.find(q('pPr') + '/' + q('ind')) if p.find(q('pPr')) is not None else None
                    if ind is not None and not t.startswith(' ') and lines and lines[-1].rstrip().endswith('\\'): t = '  ' + t
                    lines.append(t.rstrip())
                lang = 'bash' if (title is None or title.lower().startswith('terminal') or 'bashrc' in title) else ''
                if title: s.emit(f'**{title}**'); s.emit()
                s.emit('```' + lang); s.out += lines; s.emit('```'); s.emit(); return
            # recuadro (nota, precaución, resultado...)
            first = True
            for p in ps:
                t = s.ptext(p).strip()
                if not t: continue
                line = s.inline(s.runs(p)).strip()
                if first and len(t) < 60 and t.endswith(':') and not line.startswith('**'): line = f'**{t}**'
                s.emit('> ' + line); s.emit('>'); first = False
            if s.out and s.out[-1] == '>': s.out.pop()
            s.emit(); return
        # tabla normal
        grid = []
        for tr in rows:
            row = []
            for tc in tr.findall(q('tc')):
                parts = [s.inline(s.runs(p)).strip() for p in tc.findall('.//' + q('p'))]
                cell = '<br>'.join(x for x in parts if x).replace('|', '\\|')
                span = tc.find(q('tcPr') + '/' + q('gridSpan')) if tc.find(q('tcPr')) is not None else None
                row.append(cell)
                if span is not None:
                    row += [''] * (int(span.get(q('val'))) - 1)
            grid.append(row)
        if not grid: return
        n = max(len(r) for r in grid)
        grid = [r + [''] * (n - len(r)) for r in grid]
        s.emit('| ' + ' | '.join(grid[0]) + ' |'); s.emit('|' + '---|' * n)
        for r in grid[1:]: s.emit('| ' + ' | '.join(r) + ' |')
        s.emit()

    def convert(s):
        body = s.doc.find(q('body')); in_list = False
        for el in body:
            if el.tag == q('p'):
                was = in_list; in_list = s.para(el, in_list)
                if was and not in_list and s.out and s.out[-1] != '': s.emit()
            elif el.tag == q('tbl'):
                if in_list: s.emit(); in_list = False
                s.table(el)
        txt = '\n'.join(s.out)
        txt = re.sub(r'(\n *(?:-|\d+\.) [^\n]*)\n(?=[^\s\n])(?! *(?:-|\d+\.) )', r'\1\n\n', txt)
        txt = re.sub(r'\n{3,}', '\n\n', txt).strip() + '\n'
        aviso = (f'> Versión en Markdown del documento [{s.base}]({s.base.replace(" ", "%20")}) para consultar y copiar '
                 'comandos desde GitHub. El documento de Word es la versión oficial (formato GFPI-F-135).\n\n')
        i = txt.find('\n')
        txt = txt[:i + 1] + '\n' + aviso + txt[i + 1:].lstrip('\n') if txt.startswith('# ') else aviso + txt
        mdp = os.path.splitext(s.path)[0] + '.md'
        open(mdp, 'w', encoding='utf-8').write(txt)
        return mdp, s.nimg


if __name__ == '__main__':
    for f in sys.argv[1:]:
        try:
            mdp, n = Conv(f).convert(); print(f'OK {n:3} img  {os.path.basename(mdp)}')
        except Exception as e:
            print('ERROR', os.path.basename(f), e)
