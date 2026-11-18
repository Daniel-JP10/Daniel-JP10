"""Genera los SVG animados del README de perfil.

Uso: python scripts/generar_assets.py
Las fuentes (SIL OFL 1.1) se incrustan en base64 porque GitHub no deja que un SVG
dentro de <img> cargue recursos externos.
"""
import base64
import html
import math
import random
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from fontTools.ttLib import TTFont

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"
FUENTES = ASSETS / "fuentes"

# Paleta general: casi negro, texto frío y un acento dorado cálido (anillos del planeta, amanecer).
# Cada tarjeta de misión usa en cambio los colores reales de su propia web (ver TEMAS).
FONDO_A, FONDO_B = "#0d1322", "#04060b"
BLANCO, GRIS, GRIS_CLARO, ACERO = "#eef1f6", "#8e97a8", "#b4bccb", "#c3cfe3"
ORO = "#f0c36a"


class Fuente:
    def __init__(self, archivo, familia, peso, clase):
        t = TTFont(FUENTES / archivo)
        self.cmap, self.hmtx, self.upm = t.getBestCmap(), t["hmtx"], t["head"].unitsPerEm
        self.familia, self.peso, self.clase = familia, peso, clase
        self.b64 = base64.b64encode((FUENTES / archivo).read_bytes()).decode()

    def ancho(self, s, size, ls=0):
        espacio = self.cmap[32]
        u = sum(self.hmtx[self.cmap.get(ord(c), espacio)][0] for c in s)
        return u * size / self.upm + ls * len(s)

    def face(self):
        return (f"@font-face{{font-family:'{self.familia}';font-weight:{self.peso};"
                f"src:url(data:font/woff2;base64,{self.b64}) format('woff2')}}"
                f".{self.clase}{{font-family:'{self.familia}';font-weight:{self.peso}}}")


MONO = Fuente("jetbrains-mono-latin-400-normal.woff2", "JBMono", 400, "m")
E2 = Fuente("exo-2-latin-200-normal.woff2", "Exo2", 200, "e2")
E3 = Fuente("exo-2-latin-300-normal.woff2", "Exo2", 300, "e3")
E4 = Fuente("exo-2-latin-400-normal.woff2", "Exo2", 400, "e4")
E6 = Fuente("exo-2-latin-600-normal.woff2", "Exo2", 600, "e6")
TODAS = [MONO, E2, E3, E4, E6]

CSS_BASE = """
.t1{animation:tw 3.2s ease-in-out infinite}.t2{animation:tw 5.1s ease-in-out infinite}
.t3{animation:tw 7.3s ease-in-out infinite}
@keyframes tw{0%,100%{opacity:1}50%{opacity:.22}}
.f{animation:fade 1.4s ease-out both}
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.blink{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}
.sp{animation:spin linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 3.2s ease-out infinite}
@keyframes pulse{0%{transform:scale(.7);opacity:.6}100%{transform:scale(2.2);opacity:0}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def esc(s):
    return html.escape(s, quote=True)


def texto(x, y, s, f, size, fill, ls=0, anchor=None, extra=""):
    a = f' text-anchor="{anchor}"' if anchor else ""
    l = f' letter-spacing="{ls}"' if ls else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{f.clase}" font-size="{size}" '
            f'fill="{fill}"{l}{a} {extra}>{esc(s)}</text>')


def envolver(s, f, size, ancho):
    lineas, actual = [], ""
    for palabra in s.split():
        prueba = f"{actual} {palabra}".strip()
        if actual and f.ancho(prueba, size) > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    return lineas + ([actual] if actual else [])


def parrafo(x, y, s, f, size, fill, ancho, alto_linea):
    lineas = envolver(s, f, size, ancho)
    spans = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else alto_linea}">{esc(l)}</tspan>'
                    for i, l in enumerate(lineas))
    return f'<text x="{x}" y="{y}" class="{f.clase}" font-size="{size}" fill="{fill}">{spans}</text>', len(lineas)


DEFS_ESTRELLA = """
<radialGradient id="halo"><stop offset="0" stop-color="#fff" stop-opacity=".85"/>
<stop offset=".25" stop-color="#e6ecf5" stop-opacity=".3"/><stop offset="1" stop-color="#e6ecf5" stop-opacity="0"/></radialGradient>
<linearGradient id="rayoH" gradientUnits="userSpaceOnUse" x1="-20" y1="0" x2="20" y2="0">
<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<linearGradient id="rayoV" gradientUnits="userSpaceOnUse" x1="0" y1="-20" x2="0" y2="20">
<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<symbol id="brillo" overflow="visible"><circle r="6" fill="url(#halo)"/>
<path d="M-18 0H18" stroke="url(#rayoH)" stroke-width=".8"/><path d="M0 -18V18" stroke="url(#rayoV)" stroke-width=".8"/>
<circle r="1.3" fill="#fff"/></symbol>
"""


def estrellas(rng, w, h, n, brillantes=0, banda=None, evitar=(0, 30, 1000, 110)):
    """Campo de estrellas en tres ritmos de titileo; banda=(x0,y0,x1,y1,grosor) concentra la mitad.
    evitar=(x0,y0,x1,y1): zona de texto donde no caen las estrellas brillantes (por defecto, la cabecera)."""
    out = []
    colores = ["#ffffff", "#e8edf6", "#dfe6f2", "#f3eadb", "#ffffff"]
    for _ in range(n):
        if banda and rng.random() < 0.5:
            x0, y0, x1, y1, g = banda
            t = rng.random()
            x = x0 + (x1 - x0) * t + rng.gauss(0, g) * 0.3
            y = y0 + (y1 - y0) * t + rng.gauss(0, g)
        else:
            x, y = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.choices([.35, .5, .7, .9, 1.2, 1.6], [30, 30, 18, 10, 6, 2])[0]
        op = rng.uniform(.25, .9)
        out.append(f'<circle class="t{rng.randint(1, 3)}" cx="{x:.1f}" cy="{y:.1f}" r="{r}" '
                   f'fill="{rng.choice(colores)}" fill-opacity="{op:.2f}" '
                   f'style="animation-delay:-{rng.uniform(0, 7):.2f}s"/>')
    for _ in range(brillantes):
        x, y, s = rng.uniform(20, w - 20), rng.uniform(20, h - 20), rng.uniform(.4, .9)
        while evitar[0] < x < evitar[2] and evitar[1] < y < evitar[3]:
            x, y = rng.uniform(20, w - 20), rng.uniform(20, h - 20)
        out.append(f'<use href="#brillo" class="t{rng.randint(1, 3)}" transform="translate({x:.1f} {y:.1f}) '
                   f'scale({s:.2f})" style="animation-delay:-{rng.uniform(0, 7):.2f}s"/>')
    return "".join(out)


def fondo(w, h, cx="30%", cy="60%"):
    return (f'<radialGradient id="bg" cx="{cx}" cy="{cy}" r="85%"><stop offset="0" stop-color="{FONDO_A}"/>'
            f'<stop offset="1" stop-color="{FONDO_B}"/></radialGradient>', f'<rect width="{w}" height="{h}" fill="url(#bg)"/>')


def nebulosa(nubes):
    """Nubes de gas tenues: (cx, cy, rx, ry, color, opacidad)."""
    defs, cuerpo = ['<filter id="neb" x="-50%" y="-50%" width="200%" height="200%">'
                    '<feGaussianBlur stdDeviation="45"/></filter>'], []
    for cx, cy, rx, ry, c, o in nubes:
        cuerpo.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{c}" opacity="{o}" filter="url(#neb)"/>')
    return "".join(defs), "".join(cuerpo)


def svg(w, h, etiqueta, defs, cuerpo, css_extra="", margen=(0, 0, 0, 0)):
    """margen (izq, der, arriba, abajo): borde transparente; en las tarjetas va solo del lado interior,
    así dos tarjetas al 50 % quedan separadas y con sus bordes exteriores alineados con los paneles."""
    mi, md, ma, mb = margen
    usadas = [f for f in TODAS if f'class="{f.clase}"' in cuerpo]
    css = "".join(f.face() for f in usadas) + CSS_BASE + css_extra
    W, H = w + mi + md, h + ma + mb
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'role="img" aria-label="{esc(etiqueta)}"><title>{esc(etiqueta)}</title>'
            "<!-- Fuentes: JetBrains Mono y Exo 2, SIL Open Font License 1.1 (ver assets/fuentes) -->"
            f'<style>{css}</style><defs>{defs}<clipPath id="redondo"><rect width="{w}" height="{h}" rx="18"/></clipPath></defs>'
            f'<g transform="translate({mi} {ma})"><g clip-path="url(#redondo)">{cuerpo}'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="none" stroke="#fff" stroke-opacity=".07"/>'
            f'</g></g></svg>')


def cabecera(es, en, y=74):
    """Título de sección: español en Exo 2 Light espaciado, inglés en mono."""
    t = texto(60, y, es, E3, 34, BLANCO, ls=6)
    x = 60 + E3.ancho(es, 34, 6) + 16
    return t + texto(x, y, f"/ {en}", MONO, 20, GRIS, ls=1)


def elipse_path(cx, cy, rx, ry):
    return f"M{cx - rx},{cy} a{rx},{ry} 0 1,0 {2 * rx},0 a{rx},{ry} 0 1,0 {-2 * rx},0"


# ---------------------------------------------------------------- encabezado

def planeta(cx, cy, r, inclinacion):
    """Planeta con anillos, bandas con textura de turbulencia y luz desde arriba a la izquierda."""
    anillos = [(1.20, 5, "#8f8676", .30), (1.30, 13, "#c9c0ad", .55), (1.43, 19, "#e3dccb", .78),
               (1.62, 15, "#c2b8a3", .55), (1.75, 7, "#a49a87", .35), (1.84, 2.5, "#8d8371", .25)]
    def capa_anillos():
        return "".join(f'<ellipse rx="{r * k:.1f}" ry="{r * k * .22:.1f}" fill="none" stroke="{c}" '
                       f'stroke-width="{sw}" stroke-opacity="{o}"/>' for k, sw, c, o in anillos)
    bandas_col = ["#ddd7ca", "#d3ccbc", "#c8bfac", "#d8d1c2", "#c1b8a4", "#cfc8b7", "#e0dbcf",
                  "#c5bca8", "#d5cebf", "#bbb19c", "#cbc3b1", "#dbd5c8"]
    rng = random.Random(7)
    bandas, y = [], -r
    while y < r:
        alto = rng.uniform(8, 30)
        bandas.append(f'<rect x="{-2 * r}" y="{y:.1f}" width="{4 * r}" height="{alto + 1:.1f}" fill="{rng.choice(bandas_col)}"/>')
        y += alto
    manchas = "".join(f'<ellipse cx="{rng.uniform(-1.8 * r, 1.8 * r):.0f}" cy="{rng.uniform(-.7 * r, .7 * r):.0f}" '
                      f'rx="{rng.uniform(10, 26):.0f}" ry="{rng.uniform(3, 7):.0f}" fill="#fff" opacity=".12"/>'
                      for _ in range(14))
    defs = f"""
<clipPath id="pl"><circle r="{r}"/></clipPath>
<clipPath id="atras"><rect x="{-3 * r}" y="{-r}" width="{6 * r}" height="{r}"/></clipPath>
<clipPath id="frente"><rect x="{-3 * r}" y="0" width="{6 * r}" height="{r}"/></clipPath>
<filter id="tex" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".004 .09" numOctaves="3" seed="4"/>
<feDisplacementMap in="SourceGraphic" scale="9"/><feGaussianBlur stdDeviation="1.2"/></filter>
<radialGradient id="sombra" cx="32%" cy="28%" r="78%"><stop offset="0" stop-color="#fff" stop-opacity=".16"/>
<stop offset=".42" stop-color="#000" stop-opacity="0"/><stop offset=".78" stop-color="#01030a" stop-opacity=".62"/>
<stop offset="1" stop-color="#01030a" stop-opacity=".94"/></radialGradient>
<filter id="borde"><feGaussianBlur stdDeviation="3"/></filter>
"""
    cuerpo = f"""
<g transform="translate({cx} {cy}) rotate({inclinacion})">
 <g clip-path="url(#atras)">{capa_anillos()}</g>
 <g clip-path="url(#pl)">
  <g class="rot"><g filter="url(#tex)">{''.join(bandas)}{manchas}</g></g>
  <ellipse cy="{r * .2:.0f}" rx="{r * 1.45:.0f}" ry="{r * .3:.0f}" fill="none" stroke="#000" stroke-width="10" stroke-opacity=".28"/>
  <circle r="{r}" fill="url(#sombra)"/>
 </g>
 <circle r="{r + 1}" fill="none" stroke="#e6e9ef" stroke-width="3" stroke-opacity=".18" filter="url(#borde)"/>
 <g clip-path="url(#frente)">{capa_anillos()}</g>
</g>"""
    css = ".rot{animation:rot 240s linear infinite alternate}@keyframes rot{to{transform:translateX(-170px)}}"
    return defs, cuerpo, css


def encabezado():
    W, H = 1200, 560
    rng = random.Random(2026)
    bg_def, bg = fondo(W, H)
    neb_def, neb = nebulosa([(260, 420, 380, 120, "#18213a", .6), (620, 520, 300, 90, "#132a33", .45),
                             (140, 140, 220, 90, "#1d1a2e", .4), (900, 360, 260, 80, "#151d33", .4)])
    pl_def, pl, pl_css = planeta(1045, 60, 165, -18)
    o1 = elipse_path(0, 0, 760, 200)
    orbitas = f"""
<g transform="translate(560 430) rotate(-11)" fill="none" stroke="{ACERO}" stroke-opacity=".12">
 <path id="orb1" d="{o1}"/><path d="{elipse_path(0, 0, 900, 300)}" stroke-dasharray="2 7"/>
 <g stroke="none"><circle r="2.6" fill="#fff"><animateMotion dur="48s" repeatCount="indefinite"><mpath href="#orb1"/></animateMotion></circle>
 <circle r="8" fill="url(#halo)"><animateMotion dur="48s" repeatCount="indefinite"><mpath href="#orb1"/></animateMotion></circle></g>
</g>"""
    galaxia = ('<g transform="translate(205 92) rotate(-24)" opacity=".6"><ellipse rx="34" ry="8" fill="url(#gal)"/>'
               '<ellipse rx="6" ry="3" fill="#fff" fill-opacity=".8"/></g>')
    fugaz = ('<g class="fugaz"><path d="M0 0L130 -44" stroke="url(#estela)" stroke-width="1.4" stroke-linecap="round"/>'
             '<circle r="1.6" fill="#fff"/></g>')
    css_fugaz = (".fugaz{opacity:0;animation:fugaz 13s linear infinite 3s}"
                 "@keyframes fugaz{0%{transform:translate(860px,70px);opacity:0}1.5%{opacity:.9}"
                 "8%{transform:translate(520px,185px);opacity:0}100%{transform:translate(520px,185px);opacity:0}}")

    x0 = 70
    linea = "EXPLORANDO EL COSMOS DEL CÓDIGO"
    size, ls = 52, 5
    while E6.ancho(linea, size, ls) > W - 2 * x0:
        size -= 1
    y = 282
    ancho = E6.ancho(linea, size, ls) + 10
    recortes = [f'<clipPath id="rev0"><rect x="{x0 - 4}" y="{y - size - 4}" width="0" height="{size + 20}">'
                f'<animate attributeName="width" from="0" to="{ancho:.0f}" begin=".6s" dur="2.2s" '
                f'fill="freeze" calcMode="spline" keySplines=".4 0 .2 1" keyTimes="0;1"/></rect></clipPath>']
    titulo = [f'<g clip-path="url(#rev0)">{texto(x0, y, linea, E6, size, "url(#tinta)", ls=ls)}</g>',
              f'<path d="M{x0} {y + 26}H{x0 + 120}" stroke="{ORO}" stroke-width="1.5" class="f" style="animation-delay:2.6s"/>']
    y_roles = y + 82
    roles = "DATA SCIENCE STUDENT · UNIVERSIDAD TECNOLÓGICA DE BOLÍVAR"
    aprendiendo = "Learning: Geospatial · AI Engineering · AI Security · Full-stack · Software Architecture"
    assert E3.ancho(aprendiendo, 23) < W - 2 * x0, "la línea de aprendizaje no cabe"
    assert MONO.ancho(roles, 21, 2) < W - 2 * x0, "la línea de roles no cabe"
    nombre = "DANIEL ANDRÉS JIMÉNEZ POVEA"
    terminal = "> Construyendo algo para el espacio"
    texto_html = f"""
<g class="f" style="animation-delay:.1s">{texto(x0, 200, nombre, MONO, 19, GRIS_CLARO, ls=5)}</g>
{''.join(titulo)}
<g class="f" style="animation-delay:3.0s">{texto(x0, y_roles, roles, MONO, 21, "#d5dbe5", ls=2)}</g>
<g class="f" style="animation-delay:3.4s">{texto(x0, y_roles + 42, aprendiendo, E3, 23, GRIS_CLARO)}</g>
<g class="f" style="animation-delay:3.9s">{texto(x0, H - 60, terminal, MONO, 21, ORO)}
<rect class="blink" x="{x0 + MONO.ancho(terminal, 21) + 6:.0f}" y="{H - 78}" width="11" height="22" fill="{ORO}" fill-opacity=".8"/></g>"""
    defs = (bg_def + neb_def + DEFS_ESTRELLA + pl_def + "".join(recortes) +
            # Luz que recorre el título: blanco, azul cielo y dorado de sol.
            f'<linearGradient id="tinta" x1="0" x2="1"><stop offset="0" stop-color="#ffffff"/>'
            f'<stop offset=".55" stop-color="#a9dcff"/><stop offset="1" stop-color="{ORO}"/></linearGradient>'
            '<radialGradient id="gal"><stop offset="0" stop-color="#e3e9f3" stop-opacity=".9"/><stop offset=".4" stop-color="#8f9fc0" stop-opacity=".4"/>'
            '<stop offset="1" stop-color="#5a6a90" stop-opacity="0"/></radialGradient>'
            '<linearGradient id="estela" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="130" y2="-44">'
            '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    cuerpo = (bg + neb + estrellas(rng, W, H, 300, 7, banda=(0, 520, 1200, 140, 70), evitar=(40, 150, 1180, 530)) + galaxia + orbitas +
              fugaz + pl + texto_html)
    return svg(W, H, f"Daniel Andrés Jiménez Povea: Explorando el cosmos del código. Data Science Student, "
               f"Universidad Tecnológica de Bolívar. {aprendiendo}. Construyendo algo para el espacio.",
               defs, cuerpo, pl_css + css_fugaz)


# ---------------------------------------------------------------- bitácora

def catmull(puntos):
    d = f"M{puntos[0][0]},{puntos[0][1]}"
    p = [puntos[0]] + puntos + [puntos[-1]]
    for i in range(1, len(p) - 2):
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p[i - 1], p[i], p[i + 1], p[i + 2]
        d += (f" C{x1 + (x2 - x0) / 6:.1f},{y1 + (y2 - y0) / 6:.1f} "
              f"{x2 - (x3 - x1) / 6:.1f},{y2 - (y3 - y1) / 6:.1f} {x2},{y2}")
    return d


CAPITULOS = [
    ("01", "Aprender a leer el mundo",
     "Empecé haciéndole preguntas a los números."),
    ("02", "La Tierra vista desde arriba",
     "Llevé esas preguntas al mapa, con datos de satélite."),
    ("03", "Qué detiene a una IA engañada",
     "En vez de suponer la respuesta, la medí."),
    ("04", "Próximo destino",
     "Lo que viene apunta más arriba."),
]


def bitacora():
    W = 1200
    rng = random.Random(11)
    nodos = [(90, 190), (370, 168), (650, 136), (930, 96)]
    ruta = catmull([(0, 205)] + nodos)
    futuro = "M930,96 C1010,72 1100,56 1200,40"
    dy = 80  # espacio para la cabecera; el resto se dibuja desplazado
    partes, fondo_texto = [], 0
    for i, ((x, y), (num, titulo, cuerpo_txt)) in enumerate(zip(nodos, CAPITULOS)):
        tx = x - 10
        bloque = [texto(tx, 262, num, MONO, 20, ORO, ls=3)]
        lineas_t = envolver(titulo, E4, 28, 262)
        for j, l in enumerate(lineas_t):
            bloque.append(texto(tx, 304 + j * 34, l, E4, 28, BLANCO))
        y_p = 304 + len(lineas_t) * 34 + 14
        p, n = parrafo(tx, y_p, cuerpo_txt, E3, 24, GRIS_CLARO, 262, 33)
        bloque.append(p)
        fondo_texto = max(fondo_texto, y_p + (n - 1) * 33)
        partes.append("".join(bloque))
        if i < 3:
            partes.append(f'<circle cx="{x}" cy="{y}" r="8" fill="none" stroke="{ACERO}" stroke-width="1" class="pulse" '
                          f'style="animation-delay:{i * .9:.1f}s"/><circle cx="{x}" cy="{y}" r="8" fill="{FONDO_B}" '
                          f'stroke="{ACERO}" stroke-width="1.5"/><circle cx="{x}" cy="{y}" r="2.8" fill="{BLANCO}"/>')
        else:
            partes.append(f'<circle cx="{x}" cy="{y}" r="34" fill="url(#destino)" class="latido"/>'
                          f'<circle cx="{x}" cy="{y}" r="11" fill="url(#esfera)"/>')
    y_linea = fondo_texto + 40
    H = y_linea + 72 + dy
    bg_def, bg = fondo(W, H, "70%", "20%")
    defs = (bg_def + DEFS_ESTRELLA +
            f'<linearGradient id="tray" x1="0" x2="1"><stop offset="0" stop-color="{ACERO}" stop-opacity=".05"/>'
            f'<stop offset="1" stop-color="{ACERO}" stop-opacity=".55"/></linearGradient>'
            f'<radialGradient id="destino"><stop offset="0" stop-color="{ORO}" stop-opacity=".35"/>'
            f'<stop offset="1" stop-color="{ORO}" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="esfera" cx="35%" cy="35%"><stop offset="0" stop-color="#fbf4e4"/>'
            f'<stop offset=".55" stop-color="{ORO}"/><stop offset="1" stop-color="#6e5a33"/></radialGradient>')
    trayecto = (f'<path id="ruta" d="{ruta}" fill="none" stroke="url(#tray)" stroke-width="1.5"/>'
                f'<path d="{futuro}" fill="none" stroke="{ORO}" stroke-opacity=".45" stroke-width="1.5" '
                f'stroke-dasharray="4 8" class="flujo"/>'
                '<g><circle r="10" fill="url(#halo)"/><circle r="2.2" fill="#fff"/>'
                '<animateMotion dur="11s" repeatCount="indefinite" rotate="auto"><mpath href="#ruta"/></animateMotion></g>')
    lema = (f'<path d="M60 {y_linea}H1140" stroke="#fff" stroke-opacity=".07"/>'
            + texto(W / 2, y_linea + 44, "Investigo por mi cuenta: cada cifra con su fuente, su rango y sus límites.",
                    E3, 24, GRIS_CLARO, anchor="middle"))
    css = (".flujo{animation:flujo 2s linear infinite}@keyframes flujo{to{stroke-dashoffset:-12}}"
           ".latido{transform-box:fill-box;transform-origin:center;animation:latido 4s ease-in-out infinite}"
           "@keyframes latido{50%{transform:scale(1.2);opacity:.6}}")
    cuerpo = (bg + estrellas(rng, W, H, 170, 3, evitar=(40, 30, 1180, H - 20)) + cabecera("BITÁCORA DE VUELO", "FLIGHT LOG")
              + f'<g transform="translate(0 {dy})">' + trayecto + "".join(partes) + lema + "</g>")
    etiqueta = "Bitácora de vuelo. " + " ".join(f"{n}. {t}: {c}" for n, t, c in CAPITULOS)
    return svg(W, H, etiqueta, defs, cuerpo, css)


# ---------------------------------------------------------------- herramientas

HERRAMIENTAS = [
    ("Data & ML", ["Python", "pandas", "NumPy", "scikit-learn", "XGBoost", "statsmodels", "Jupyter"]),
    ("Geospatial", ["GeoPandas", "Shapely", "H3", "MapLibre", "Leaflet", "PMTiles", "Satellite data"]),
    ("AI & Security", ["Claude Code", "AI agents", "Ollama", "Docker", "Threat modeling", "gitleaks"]),
    ("Full-stack", ["FastAPI", "Go", "gRPC", "PostgreSQL", "React", "Next.js", "TypeScript"]),
]


def herramientas():
    W, P = 1200, 60
    col = (W - 2 * P) / 4
    y0, paso = 160, 44
    filas = max(len(t) for _, t in HERRAMIENTAS)
    H = y0 + 70 + filas * paso + 30
    rng = random.Random(5)
    bg_def, bg = fondo(W, H, "50%", "40%")
    columnas = []
    for i, (nombre, techs) in enumerate(HERRAMIENTAS):
        x = P + i * col + (24 if i else 0)
        assert all(E3.ancho(t, 25) < col - 40 for t in techs), f"{nombre}: una tecnología no cabe"
        if i:  # línea fina entre columnas, sin cajas ni colores por categoría
            columnas.append(f'<path d="M{P + i * col:.0f} {y0 - 8}V{H - 40}" stroke="#fff" stroke-opacity=".07"/>')
        columnas.append(texto(x, y0 + 14, nombre.upper(), MONO, 18, ORO, ls=3))
        columnas.extend(texto(x, y0 + 70 + j * paso, t, E3, 25, "#dfe4ec") for j, t in enumerate(techs))
    cuerpo = (bg + estrellas(rng, W, H, 140, 3, evitar=(40, 30, 1180, H - 20)) + cabecera("HERRAMIENTAS", "TOOLKIT") + "".join(columnas))
    etiqueta = "Herramientas. " + ". ".join(f"{n}: {', '.join(t)}" for n, t in HERRAMIENTAS)
    return svg(W, H, etiqueta, bg_def + DEFS_ESTRELLA, cuerpo)


# ---------------------------------------------------------------- vía láctea (órbitas)

ORBITAS = [
    ("Data & ML", "#5cc8f5", 140, 52, ["Python", "pandas", "scikit-learn", "XGBoost", "statsmodels"]),
    ("Geospatial", "#5fd39a", 258, 76, ["GeoPandas", "H3", "MapLibre", "Leaflet", "PMTiles", "Satellite data"]),
    ("AI & Security", "#a98bfa", 372, 100, ["Claude Code", "AI agents", "Ollama", "Threat modeling", "Docker", "gitleaks"]),
    ("Full-stack", ORO, 486, 128, ["FastAPI", "Go", "gRPC", "PostgreSQL", "React", "Next.js", "TypeScript", "Tailwind"]),
]


def orbitas():
    W, H = 1200, 640
    cx, cy, k = 600, 300, .5
    rng = random.Random(5)
    bg_def, bg = fondo(W, H, "50%", "45%")
    # Banda de la vía láctea: polvo tenue y estrellas concentradas en diagonal.
    neb_def, neb = nebulosa([(600, 300, 640, 70, "#2a3556", .55), (420, 360, 300, 50, "#3a3048", .35),
                             (820, 230, 280, 45, "#24364a", .35)])
    via = f'<g transform="rotate(-14 600 300)">{neb}</g>'
    capas = []
    for _, color, R, dur, techs in ORBITAS:
        capas.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{R}" ry="{R * k:.1f}" fill="none" stroke="{color}" '
                     f'stroke-opacity=".3" stroke-dasharray="3 6"/>')
        for i, tech in enumerate(techs):
            st = f'style="animation-duration:{dur}s;animation-delay:-{dur * i / len(techs):.2f}s"'
            nodo = (f'<circle r="11" fill="{color}" fill-opacity=".2"/><circle r="5.5" fill="{color}"/>'
                    + texto(0, -16, tech, E6, 18, BLANCO, anchor="middle",
                            extra='paint-order="stroke" stroke="#050914" stroke-width="5"'))
            # El grupo gira en el plano achatado y contra-gira sin achatar: el texto queda derecho.
            capas.append(f'<g transform="translate({cx} {cy}) scale(1 {k})"><g class="sp" {st}>'
                         f'<g transform="translate({R} 0)"><g class="un" {st}><g transform="scale(1 {1 / k:.4f})">'
                         f'<g class="prof" {st}>{nodo}</g></g></g></g></g></g>')
    nucleo = (f'<circle cx="{cx}" cy="{cy}" r="90" fill="url(#corona)" class="latido"/>'
              f'<circle cx="{cx}" cy="{cy}" r="38" fill="url(#sol)"/>'
              + texto(cx, cy + 9, "DJ", E6, 26, "#3a2a08", ls=2, anchor="middle"))
    leyenda = []
    total = sum(E4.ancho(n, 20) + 60 for n, *_ in ORBITAS)
    x = (W - total) / 2
    for n, c, *_ in ORBITAS:
        leyenda.append(f'<circle cx="{x + 7:.0f}" cy="{H - 38}" r="6" fill="{c}"/>' + texto(x + 22, H - 31, n, E4, 20, GRIS_CLARO))
        x += E4.ancho(n, 20) + 60
    defs = (bg_def + neb_def + DEFS_ESTRELLA +
            f'<radialGradient id="corona"><stop offset="0" stop-color="{ORO}" stop-opacity=".5"/>'
            f'<stop offset=".45" stop-color="{ORO}" stop-opacity=".12"/><stop offset="1" stop-color="{ORO}" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="sol" cx="40%" cy="38%"><stop offset="0" stop-color="#fffaf0"/>'
            f'<stop offset=".6" stop-color="#ffe2a8"/><stop offset="1" stop-color="{ORO}"/></radialGradient>')
    css = (".un{animation:unspin linear infinite}@keyframes unspin{to{transform:rotate(-360deg)}}"
           ".prof{animation:prof linear infinite}"
           "@keyframes prof{0%{opacity:.9}25%{opacity:1}50%{opacity:.9}75%{opacity:.6}100%{opacity:.9}}"
           ".latido{transform-box:fill-box;transform-origin:center;animation:latido 5s ease-in-out infinite}"
           "@keyframes latido{50%{transform:scale(1.12);opacity:.75}}")
    cuerpo = (bg + via + estrellas(rng, W, H, 420, 0, banda=(0, 450, 1200, 150, 55))
              + nucleo + "".join(capas) + "".join(leyenda))
    etiqueta = "Vía láctea de habilidades. " + ". ".join(f"{n}: {', '.join(t)}" for n, _, _, _, t in ORBITAS)
    return svg(W, H, etiqueta, defs, cuerpo, css)


# ---------------------------------------------------------------- misiones
# Cada tarjeta toma los colores reales de su proyecto (variables CSS de su web, o su logo).
# Un valor de color puede ser una lista: entonces es un degradado horizontal.

TEMAS = {
    # agroversex.pages.dev: --fondo #03100b, --hoja #0f2a1d, --acento #7be0a0, --agua #4fd1c5
    "agro": dict(fondo=("#0f2a1d", "#03100b"), titulo="#e8f3ec", lema="#e8f3ec", sub="#a7c4b3",
                 cifra=["#7be0a0", "#4fd1c5"], linea="#2f6b4a", punto="#7be0a0", icono="#7be0a0", icono2="#4fd1c5"),
    # hexvial.vercel.app: fondo blanco, texto #1a1d20, escala del mapa #fdcc8a -> #e34a33 -> #b30000
    "hex": dict(fondo=("#ffffff", "#f1f4f8"), titulo="#1a1d20", lema="#1a1d20", sub="#606979", claro=True,
                cifra=["#fc8d59", "#e34a33", "#b30000"], linea="#d0d7de", punto="#e34a33", icono="#e34a33", icono2="#fdcc8a"),
    # logo de BSA: azul marino, letras plateadas, cian eléctrico y engranaje dorado
    "bsa": dict(fondo=("#15253f", "#070f1d"), titulo=["#ffffff", "#c9d1dc", "#8e9aab"], lema="#dbe2ec", sub="#8fa0b8",
                cifra=["#e9eef5", "#4cc9f0"], linea="#2a3b55", punto="#4cc9f0", icono="#c9d1dc", icono2="#4cc9f0"),
    # rfa no tiene web: identidad académica de tinta índigo y lavanda
    "rfa": dict(fondo=("#1d1838", "#0b0918"), titulo="#f1ecff", lema="#e6e0fa", sub="#a99fc4",
                cifra=["#c4b5fd", "#a78bfa"], linea="#3a3163", punto="#a78bfa", icono="#c4b5fd", icono2="#a78bfa"),
    # proyecto-deforestacion.vercel.app: --green-dark #1a3c27, --green-light #7FB069, --green-pale #A8D5A0, --teal #2A9D8F
    "manglar": dict(fondo=("#1f4a30", "#0c2014"), titulo="#ffffff", lema="#e8f5e3", sub="#a8d5a0",
                    cifra=["#a8d5a0", "#7fb069"], linea="#2d5a3d", punto="#7fb069", icono="#7fb069", icono2="#2a9d8f"),
    # tablero-medicamentos.vercel.app: fondo #071739, degradado #38bdf8 -> #67e8f9 -> #34d399
    "tablero": dict(fondo=("#0f2a66", "#071739"), titulo="#ffffff", lema="#dbe6ff", sub="#94a8cc",
                    cifra=["#38bdf8", "#67e8f9", "#34d399"], linea="#1e3a6b", punto="#34d399", icono="#38bdf8", icono2="#34d399"),
}


def relleno(id_, valor):
    """Devuelve (defs, fill): un color tal cual, o un degradado horizontal si es una lista."""
    if isinstance(valor, str):
        return "", valor
    stops = "".join(f'<stop offset="{k / (len(valor) - 1):.2f}" stop-color="{c}"/>' for k, c in enumerate(valor))
    return f'<linearGradient id="{id_}" x1="0" x2="1">{stops}</linearGradient>', f"url(#{id_})"


def icono_globo(t):
    meridianos = "".join(
        f'<ellipse rx="0" ry="44" fill="none" stroke="{t["icono"]}" stroke-opacity=".7">'
        f'<animate attributeName="rx" values="0;44;0" dur="9s" begin="-{i * 3}s" repeatCount="indefinite"/></ellipse>'
        for i in range(3))
    return (f'<circle r="44" fill="{t["icono2"]}" fill-opacity=".08" stroke="{t["icono"]}" stroke-width="2"/>{meridianos}'
            f'<path d="M-44 0H44M-38 -22H38M-38 22H38" stroke="{t["icono2"]}" stroke-opacity=".6"/>')


def icono_hex(t):
    # Los colores del mapa de HEXVIAL: el sector más riesgoso al centro.
    escala = ["#b30000", "#e34a33", "#fc8d59", "#e34a33", "#fdcc8a", "#fc8d59", "#fef0d9"]
    r, d = 17, 17 * math.sqrt(3)
    centros = [(0, 0)] + [(d * math.cos(math.radians(30 + 60 * k)), d * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    out = []
    for i, (x, y) in enumerate(centros):
        pts = " ".join(f"{x + r * math.cos(math.radians(60 * k)):.1f},{y + r * math.sin(math.radians(60 * k)):.1f}" for k in range(6))
        out.append(f'<polygon points="{pts}" fill="{escala[i]}" stroke="#fff" stroke-width="2"{" class=\"calor\"" if i == 0 else ""}/>')
    return "".join(out)


def icono_escudo(t):
    return (f'<path d="M0,-46 L38,-31 L38,4 C38,28 20,41 0,50 C-20,41 -38,28 -38,4 L-38,-31 Z" fill="{t["icono2"]}" fill-opacity=".1" '
            f'stroke="{t["icono"]}" stroke-width="2"/>'
            f'<path d="M-14,2 L-4,12 L16,-10" fill="none" stroke="{t["icono2"]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
            '<circle r="4" fill="#e0b04a" class="ataque"/>')


def icono_manglar(t):
    return (f'<path d="M-38,10 C-30,-30 20,-44 38,-12 C46,10 20,36 -6,34 C-24,33 -40,28 -38,10Z" fill="{t["icono2"]}" fill-opacity=".25" '
            f'stroke="{t["icono2"]}" stroke-width="1.5" class="perdida"/>'
            f'<path d="M-24,8 C-18,-18 14,-28 26,-8 C32,8 14,24 -4,22 C-16,21 -26,18 -24,8Z" fill="{t["icono"]}" fill-opacity=".55"/>'
            f'<path d="M-10,6 C-8,-6 6,-10 12,-2 C14,6 6,12 -2,11 C-8,10 -11,9 -10,6Z" fill="#a8d5a0"/>')


def icono_barras(t):
    alturas = [34, 58, 26, 72, 48]
    return ("".join(f'<rect x="{-42 + i * 18}" y="{36 - h}" width="10" height="{h}" rx="1.5" '
                    f'fill="{t["icono"] if i % 2 else t["icono2"]}" class="barra" style="animation-delay:-{i * .45:.2f}s"/>'
                    for i, h in enumerate(alturas)) + f'<path d="M-48 38H48" stroke="{t["icono"]}" stroke-opacity=".5"/>')


def icono_documento(t):
    lineas = "".join(f'<path d="M-20 {y}H{w}" stroke="{t["icono"]}" stroke-opacity=".6" stroke-width="2.5" stroke-linecap="round"/>'
                     for y, w in [(-24, 18), (-12, 20), (0, 8), (12, 14)])
    return (f'<rect x="-32" y="-44" width="64" height="86" rx="6" fill="{t["icono2"]}" fill-opacity=".1" stroke="{t["icono"]}" stroke-width="2"/>'
            + lineas + f'<path d="M14,30 L22,38 L36,22" fill="none" stroke="{t["icono2"]}" stroke-width="3" stroke-linecap="round" '
            'stroke-linejoin="round" stroke-dasharray="30" class="trazo"/>')


MISIONES = [
    dict(archivo="mision-01-agroversex", idioma="en", nombre="AGROVERSEx", icono=icono_globo, tema="agro", vivo=True,
         lema="Your land seen from space, down to your field.",
         cifra=("49,349", "regions mapped with NASA open data")),
    dict(archivo="mision-02-hexvial", idioma="es", nombre="HEXVIAL", icono=icono_hex, tema="hex", vivo=True,
         lema="Dónde se concentra el riesgo vial en Bogotá.",
         cifra=("31 %", "del riesgo vial en 13 de 123 sectores")),
    dict(archivo="mision-03-bsa", idioma="en", nombre="BSA", icono=icono_escudo, tema="bsa", vivo=False,
         lema="When a coding agent gets fooled, what actually stops it?",
         cifra=("336", "sealed runs, 7 permission setups")),
    dict(archivo="mision-04-rfa", idioma="en", nombre="RFA SCHOLARLY WRITING", icono=icono_documento, tema="rfa", vivo=False,
         lema="Scholarly writing without invented sources.",
         cifra=("22", "citation styles, verified references")),
    dict(archivo="mision-05-deforestacion", idioma="es", nombre="EL PARAÍSO QUE SE BORRA", icono=icono_manglar, tema="manglar",
         vivo=True, lema="Los manglares de Cartagena de Indias.",
         cifra=("53", "años de manglar documentados")),
    dict(archivo="mision-06-medicamentos", idioma="es", nombre="TABLERO DE MEDICAMENTOS", icono=icono_barras, tema="tablero",
         vivo=True, lema="Auditoría farmacoeconómica de una EPS.",
         cifra=("28.482", "dispensaciones analizadas en vivo")),
]


def mision(i, m):
    # La tarjeta se ve a ~0,67 de su tamaño en GitHub: ningún texto baja de 18 px aquí.
    W, H, P = 600, 380, 36
    t = TEMAS[m["tema"]]
    claro = t.get("claro", False)
    rng = random.Random(100 + i)
    es = m["idioma"] == "es"
    etiqueta_mision = f"{'MISIÓN' if es else 'MISSION'} {i:02d}"
    estado = ("EN LÍNEA" if es else "LIVE") if m["vivo"] else ("CÓDIGO ABIERTO" if es else "OPEN SOURCE")
    # Estado como píldora de borde fino, igual que las etiquetas de AGROVERSEx y el tablero.
    x_p = P + MONO.ancho(etiqueta_mision, 18, 2) + 20
    w_p = MONO.ancho(estado, 16, 1) + 44
    cab = (texto(P, 58, etiqueta_mision, MONO, 18, t["sub"], ls=2) +
           f'<rect x="{x_p:.0f}" y="36" width="{w_p:.0f}" height="30" rx="15" fill="{t["linea"]}" fill-opacity=".25" '
           f'stroke="{t["linea"]}"/>'
           f'<circle cx="{x_p + 16:.0f}" cy="51" r="4" fill="{t["punto"]}" class="t1"/>' +
           texto(x_p + 28, 57, estado, MONO, 16, t["lema"], ls=1))
    d_tit, f_tit = relleno("g_titulo", t["titulo"])
    d_cif, f_cif = relleno("g_cifra", t["cifra"])
    size, ls = 38, 3
    while E6.ancho(m["nombre"], size, ls) > 470:
        size -= 1
    y = 122
    partes = [cab, texto(P, y, m["nombre"], E6, size, f_tit, ls=ls)]
    y += 48
    lema = envolver(m["lema"], E4, 25, 500)
    if len(lema) == 2:  # reparte las palabras para no dejar una sola en la segunda línea
        palabras = m["lema"].split()
        corte = min(range(1, len(palabras)), key=lambda c: max(E4.ancho(" ".join(palabras[:c]), 25),
                                                                 E4.ancho(" ".join(palabras[c:]), 25)))
        lema = [" ".join(palabras[:corte]), " ".join(palabras[corte:])]
    for l in lema:
        partes.append(texto(P, y, l, E4, 25, t["lema"]))
        y += 33
    num, lab = m["cifra"]
    y_cifra = H - 80
    assert y - 33 + 10 < y_cifra - 52, f"{m['archivo']}: el lema choca con la cifra"
    assert MONO.ancho(lab, 18) < W - 2 * P, f"{m['archivo']}: la etiqueta de la cifra no cabe"
    partes.append(texto(P, y_cifra, num, E3, 60, f_cif, ls=1))
    partes.append(texto(P, y_cifra + 38, lab, MONO, 18, t["sub"]))
    defs = (DEFS_ESTRELLA + d_tit + d_cif +
            f'<linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["fondo"][0]}"/>'
            f'<stop offset="1" stop-color="{t["fondo"][1]}"/></linearGradient>'
            f'<radialGradient id="brillo_t" cx="85%" cy="15%" r="60%"><stop offset="0" stop-color="{t["icono2"]}" '
            f'stop-opacity="{.10 if claro else .16}"/><stop offset="1" stop-color="{t["icono2"]}" stop-opacity="0"/></radialGradient>')
    cuerpo = (f'<rect width="{W}" height="{H}" fill="url(#panel)"/><rect width="{W}" height="{H}" fill="url(#brillo_t)"/>'
              + ("" if claro else estrellas(rng, W, H, 30, 0))
              + f'<g transform="translate({W - 66} 58) scale(.48)">{m["icono"](t)}</g>'
              + "".join(partes)
              # Marco azul noche como el resto de paneles, con un filo interior del color del proyecto.
              + f'<rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="15" fill="none" stroke="#141c30" stroke-width="8"/>'
              + f'<rect x="8.5" y="8.5" width="{W - 17}" height="{H - 17}" rx="11" fill="none" stroke="{t["punto"]}" '
                f'stroke-opacity=".45"/>')
    css = (".calor{animation:calor 3s ease-in-out infinite}@keyframes calor{50%{fill-opacity:.55}}"
           ".ataque{animation:ataque 3.6s ease-in infinite}@keyframes ataque{0%{transform:translateX(90px);opacity:0}"
           "15%{opacity:1}60%{transform:translateX(42px);opacity:1}68%,100%{transform:translateX(42px);opacity:0}}"
           ".perdida{transform-box:fill-box;transform-origin:center;animation:perdida 6s ease-in-out infinite alternate}"
           "@keyframes perdida{to{transform:scale(.85);opacity:.4}}"
           ".barra{transform-box:fill-box;transform-origin:bottom;animation:barra 2.6s ease-in-out infinite alternate}"
           "@keyframes barra{from{transform:scaleY(.4)}}"
           ".trazo{animation:trazo 4.5s ease-out infinite}@keyframes trazo{0%{stroke-dashoffset:30}30%,100%{stroke-dashoffset:0}}")
    etiqueta = f"{etiqueta_mision}: {m['nombre']}. {m['lema']} {num} {lab}."
    return svg(W, H, etiqueta, defs, cuerpo, css, margen=(0, 12, 0, 18) if i % 2 else (12, 0, 0, 18))


# ---------------------------------------------------------------- cierre

FRASE = ("I was born for space.",
         "Until I reach it, I read the Earth from above, one dataset at a time.")


def cierre():
    W, H = 1200, 320
    rng = random.Random(3)
    defs = (DEFS_ESTRELLA +
            f'<linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{FONDO_B}"/>'
            '<stop offset="1" stop-color="#0a1120"/></linearGradient>'
            '<radialGradient id="tierra" cx="50%" cy="0%" r="60%"><stop offset="0" stop-color="#14284a"/>'
            '<stop offset=".25" stop-color="#0b1830"/><stop offset="1" stop-color="#03060d"/></radialGradient>'
            '<radialGradient id="alba" cx="50%" cy="50%"><stop offset="0" stop-color="#f6e6c4" stop-opacity=".9"/>'
            '<stop offset=".3" stop-color="#e2bf86" stop-opacity=".4"/><stop offset="1" stop-color="#c9955a" stop-opacity="0"/></radialGradient>'
            '<filter id="atm" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="9"/></filter>'
            '<filter id="atm2" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="2"/></filter>')
    cx, cy, r = 600, 1660, 1420
    luces = "".join(f'<circle cx="{rng.uniform(250, 950):.0f}" cy="{rng.uniform(262, 316):.0f}" r="{rng.uniform(.6, 1.3):.1f}" '
                    f'fill="#f0d9a8" fill-opacity="{rng.uniform(.25, .7):.2f}" class="t{rng.randint(1, 3)}"/>' for _ in range(40))
    cuerpo = (f'<rect width="{W}" height="{H}" fill="url(#cielo)"/>' + estrellas(rng, W, 230, 110, 2, evitar=(150, 40, 1050, 180)) +
              f'<circle cx="{cx}" cy="{cy}" r="{r + 10}" fill="none" stroke="#8fb3d9" stroke-width="22" stroke-opacity=".2" filter="url(#atm)"/>'
              f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#tierra)"/>'
              f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#c4d8ee" stroke-width="2" stroke-opacity=".8" filter="url(#atm2)"/>'
              f'<ellipse cx="930" cy="{cy - r + 4}" rx="300" ry="24" fill="url(#alba)" class="alba"/>'
              + luces
              + texto(W / 2, 100, FRASE[0], E3, 48, BLANCO, ls=2, anchor="middle")
              + texto(W / 2, 150, FRASE[1], E3, 25, GRIS_CLARO, anchor="middle"))
    assert E3.ancho(FRASE[1], 25) < W - 80, "la frase de cierre no cabe"
    css = ".alba{animation:alba 9s ease-in-out infinite}@keyframes alba{50%{opacity:.55}}"
    return svg(W, H, " ".join(FRASE), defs, cuerpo, css)


def titulo_misiones():
    W, H = 1200, 116
    bg_def, bg = fondo(W, H, "20%", "50%")
    cuerpo = bg + estrellas(random.Random(21), W, H, 60, 1) + cabecera("MISIONES", "MISSIONS", y=72)
    return svg(W, H, "Misiones. Missions.", bg_def + DEFS_ESTRELLA, cuerpo)


def hackatones():
    W, H = 1200, 370
    rng = random.Random(31)
    bg_def, bg = fondo(W, H, "80%", "50%")
    p, n = parrafo(60, 246, "I took part and built AGROVERSEx, a digital twin that helps farmers compare "
                   "crop rotations with satellite data.", E3, 25, GRIS_CLARO, 800, 35)
    insignia = (f'<g transform="translate(1030 196)">'
                f'<g class="sp" style="animation-duration:40s"><circle r="78" fill="none" stroke="{ORO}" '
                f'stroke-opacity=".35" stroke-dasharray="2 8"/><circle cx="78" r="3.5" fill="{BLANCO}"/></g>'
                f'<circle r="54" fill="none" stroke="{ORO}" stroke-opacity=".7"/>'
                + texto(0, 10, "2026", E3, 30, ORO, ls=4, anchor="middle") + "</g>")
    cuerpo = (bg + estrellas(rng, W, H, 110, 2, evitar=(40, 30, 920, 340)) + cabecera("HACKATONES", "HACKATHONS")
              + texto(60, 150, "NASA SPACE APPS CHALLENGE 2026", E3, 32, BLANCO, ls=4)
              + texto(60, 194, "Field Shift: Adapting Farms with NASA Data", MONO, 20, ORO)
              + p + texto(60, 246 + n * 35 + 14, "github.com/Daniel-JP10/AGROVERSEx", MONO, 19, GRIS)
              + insignia)
    assert 246 + n * 35 + 14 < H - 20, "el panel de hackatones no cabe"
    return svg(W, H, "Hackatones. I took part in NASA Space Apps Challenge 2026, Field Shift: Adapting Farms with "
               "NASA Data, and built AGROVERSEx.", bg_def + DEFS_ESTRELLA, cuerpo)


# ---------------------------------------------------------------- salida

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")


def main():
    salidas = {"hero": encabezado(), "bitacora": bitacora(), "herramientas": herramientas(), "orbitas": orbitas(), "cierre": cierre(),
               "misiones": titulo_misiones(), "hackatones": hackatones()}
    salidas.update({m["archivo"]: mision(i, m) for i, m in enumerate(MISIONES, 1)})
    for nombre, contenido in salidas.items():
        ET.fromstring(contenido)  # autocomprobación: XML bien formado
        assert not EMOJI.search(contenido), f"{nombre}: contiene emojis"
        (ASSETS / f"{nombre}.svg").write_text(contenido, encoding="utf-8")
        print(f"{nombre}.svg  {len(contenido) / 1024:.0f} KB")
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert not EMOJI.search(readme), "README.md contiene emojis"


if __name__ == "__main__":
    main()
