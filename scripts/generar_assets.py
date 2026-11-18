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

# Paleta: espacio profundo con acentos fríos, como el diseño de referencia.
FONDO_A, FONDO_B = "#0b1430", "#03050c"
CIAN, BLANCO, GRIS, GRIS_CLARO = "#7fd4ff", "#eef3ff", "#8b98b8", "#a9b6d3"
VERDE, VIOLETA, AMBAR, ROJO = "#6ee7b7", "#b69cff", "#ffc677", "#ff6b6b"


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


O7 = Fuente("orbitron-latin-700-normal.woff2", "Orbitron", 700, "o7")
O5 = Fuente("orbitron-latin-500-normal.woff2", "Orbitron", 500, "o5")
MONO = Fuente("jetbrains-mono-latin-400-normal.woff2", "JBMono", 400, "m")
E4 = Fuente("exo-2-latin-400-normal.woff2", "Exo2", 400, "e4")
E6 = Fuente("exo-2-latin-600-normal.woff2", "Exo2", 600, "e6")
TODAS = [O7, O5, MONO, E4, E6]

CSS_BASE = """
.t1{animation:tw 3.2s ease-in-out infinite}.t2{animation:tw 5.1s ease-in-out infinite}
.t3{animation:tw 7.3s ease-in-out infinite}
@keyframes tw{0%,100%{opacity:1}50%{opacity:.22}}
.f{animation:fade 1.2s ease-out both}
@keyframes fade{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.blink{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}
.sp{animation:spin linear infinite}.un{animation:unspin linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}@keyframes unspin{to{transform:rotate(-360deg)}}
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2.6s ease-out infinite}
@keyframes pulse{0%{transform:scale(.6);opacity:.9}100%{transform:scale(2.4);opacity:0}}
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


DEFS_ESTRELLA = f"""
<radialGradient id="halo"><stop offset="0" stop-color="#fff" stop-opacity=".9"/>
<stop offset=".25" stop-color="#cfe6ff" stop-opacity=".35"/><stop offset="1" stop-color="#cfe6ff" stop-opacity="0"/></radialGradient>
<linearGradient id="rayoH" gradientUnits="userSpaceOnUse" x1="-20" y1="0" x2="20" y2="0">
<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<linearGradient id="rayoV" gradientUnits="userSpaceOnUse" x1="0" y1="-20" x2="0" y2="20">
<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<symbol id="brillo" overflow="visible"><circle r="7" fill="url(#halo)"/>
<path d="M-20 0H20" stroke="url(#rayoH)" stroke-width=".9"/><path d="M0 -20V20" stroke="url(#rayoV)" stroke-width=".9"/>
<circle r="1.4" fill="#fff"/></symbol>
"""


def estrellas(rng, w, h, n, brillantes=0, banda=None):
    """Campo de estrellas en tres ritmos de titileo; banda=(x0,y0,x1,y1,grosor) concentra la mitad."""
    out = []
    colores = ["#ffffff", "#dbe8ff", "#bcd4ff", "#ffe9d1", "#ffffff"]
    for _ in range(n):
        if banda and rng.random() < 0.5:
            x0, y0, x1, y1, g = banda
            t = rng.random()
            x = x0 + (x1 - x0) * t + rng.gauss(0, g) * 0.3
            y = y0 + (y1 - y0) * t + rng.gauss(0, g)
        else:
            x, y = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.choices([.35, .5, .7, .9, 1.2, 1.6], [30, 30, 18, 10, 6, 2])[0]
        op = rng.uniform(.3, 1)
        out.append(f'<circle class="t{rng.randint(1, 3)}" cx="{x:.1f}" cy="{y:.1f}" r="{r}" '
                   f'fill="{rng.choice(colores)}" fill-opacity="{op:.2f}" '
                   f'style="animation-delay:-{rng.uniform(0, 7):.2f}s"/>')
    for _ in range(brillantes):
        x, y, s = rng.uniform(20, w - 20), rng.uniform(20, h - 20), rng.uniform(.45, 1.1)
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


def svg(w, h, etiqueta, defs, cuerpo, css_extra=""):
    usadas = [f for f in TODAS if f'class="{f.clase}"' in cuerpo]
    css = "".join(f.face() for f in usadas) + CSS_BASE + css_extra
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{esc(etiqueta)}"><title>{esc(etiqueta)}</title>'
            "<!-- Fuentes: Orbitron, JetBrains Mono y Exo 2, SIL Open Font License 1.1 (ver assets/fuentes) -->"
            f"<style>{css}</style><defs>{defs}</defs>{cuerpo}</svg>")


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
 <circle r="{r + 1}" fill="none" stroke="#a8d8ff" stroke-width="4" stroke-opacity=".28" filter="url(#borde)"/>
 <g clip-path="url(#frente)">{capa_anillos()}</g>
</g>"""
    css = ".rot{animation:rot 240s linear infinite alternate}@keyframes rot{to{transform:translateX(-170px)}}"
    return defs, cuerpo, css


def encabezado():
    W, H = 1200, 560
    rng = random.Random(2026)
    bg_def, bg = fondo(W, H)
    neb_def, neb = nebulosa([(260, 420, 380, 120, "#1b2a5e", .55), (620, 520, 300, 90, "#0f3b4a", .45),
                             (140, 140, 220, 90, "#24194a", .35), (900, 360, 260, 80, "#14244f", .35)])
    pl_def, pl, pl_css = planeta(1045, 60, 165, -18)
    o1 = elipse_path(0, 0, 760, 200)
    orbitas = f"""
<g transform="translate(560 430) rotate(-11)" fill="none" stroke="#7aa7ff" stroke-opacity=".17">
 <path id="orb1" d="{o1}"/><path d="{elipse_path(0, 0, 900, 300)}" stroke-dasharray="2 7"/>
 <circle cx="-610" cy="-118" r="2.5" fill="#9fc3ff" fill-opacity=".7" stroke="none"/>
 <circle cx="520" cy="146" r="2.5" fill="#9fc3ff" fill-opacity=".7" stroke="none"/>
 <g stroke="none"><circle r="3" fill="#fff"><animateMotion dur="48s" repeatCount="indefinite"><mpath href="#orb1"/></animateMotion></circle>
 <circle r="9" fill="url(#halo)"><animateMotion dur="48s" repeatCount="indefinite"><mpath href="#orb1"/></animateMotion></circle></g>
</g>"""
    galaxia = ('<g transform="translate(205 92) rotate(-24)" opacity=".75"><ellipse rx="34" ry="8" fill="url(#gal)"/>'
               '<ellipse rx="6" ry="3" fill="#fff" fill-opacity=".8"/></g>')
    fugaz = ('<g class="fugaz"><path d="M0 0L130 -44" stroke="url(#estela)" stroke-width="1.6" stroke-linecap="round"/>'
             '<circle r="1.8" fill="#fff"/></g>')
    css_fugaz = (".fugaz{opacity:0;animation:fugaz 11s linear infinite 3s}"
                 "@keyframes fugaz{0%{transform:translate(860px,70px);opacity:0}1.5%{opacity:1}"
                 "9%{transform:translate(520px,185px);opacity:0}100%{transform:translate(520px,185px);opacity:0}}")
    marcos = "".join(f'<path d="{d}" fill="none" stroke="{CIAN}" stroke-opacity=".45" stroke-width="1.4"/>' for d in
                     ["M24 54V24H54", f"M{W - 54} 24H{W - 24}V54", f"M24 {H - 54}V{H - 24}H54", f"M{W - 54} {H - 24}H{W - 24}V{H - 54}"])

    x0 = 70
    lineas = ["EXPLORANDO EL COSMOS", "DEL CÓDIGO"]
    size = 54
    while max(O7.ancho(l, size, 2) for l in lineas) > 820:
        size -= 1
    ys = [232, 232 + size + 16]
    titulo, recortes = [], []
    for i, (l, y) in enumerate(zip(lineas, ys)):
        ancho = O7.ancho(l, size, 2) + 10
        inicio = 0.6 + i * 1.5
        recortes.append(f'<clipPath id="rev{i}"><rect x="{x0 - 4}" y="{y - size}" width="0" height="{size + 16}">'
                        f'<animate attributeName="width" from="0" to="{ancho:.0f}" begin="{inicio}s" dur="1.4s" '
                        f'fill="freeze" calcMode="spline" keySplines=".4 0 .2 1" keyTimes="0;1"/></rect></clipPath>')
        t = texto(x0, y, l, O7, size, BLANCO, ls=2)
        titulo.append(f'<g clip-path="url(#rev{i})"><g filter="url(#resplandor)" opacity=".55">{t}</g>{t}</g>')
        titulo.append(f'<rect x="{x0}" y="{y - size + 4}" width="3" height="{size + 4}" fill="{CIAN}" opacity="0">'
                      f'<animate attributeName="x" from="{x0}" to="{x0 + ancho:.0f}" begin="{inicio}s" dur="1.4s" fill="freeze" '
                      f'calcMode="spline" keySplines=".4 0 .2 1" keyTimes="0;1"/>'
                      f'<animate attributeName="opacity" values="1;1;0" keyTimes="0;.9;1" begin="{inicio}s" dur="1.4s" fill="freeze"/></rect>')
    y_roles = ys[-1] + 62
    roles = "DATA SCIENCE STUDENT · UNIVERSIDAD TECNOLÓGICA DE BOLÍVAR"
    aprendiendo = "Learning: Geospatial · AI Engineering · AI Security · Full-stack · Software Architecture"
    assert E4.ancho(aprendiendo, 19) < W - 2 * x0, "la línea de aprendizaje no cabe"
    nombre = "DANIEL ANDRÉS JIMÉNEZ POVEA"
    texto_html = f"""
<g class="f" style="animation-delay:.1s"><path d="M{x0} 140H{x0 + 44}" stroke="{CIAN}" stroke-width="2"/>
{texto(x0 + 58, 146, nombre, O5, 16, CIAN, ls=5)}</g>
{''.join(titulo)}
<g class="f" style="animation-delay:3.4s">{texto(x0, y_roles, roles, MONO, 18, "#cfe0ff", ls=1.5)}</g>
<g class="f" style="animation-delay:3.8s">{texto(x0, y_roles + 38, aprendiendo, E4, 19, GRIS)}</g>
<g class="f" style="animation-delay:4.3s">{texto(x0, H - 64, "> Construyendo algo para el espacio", MONO, 18, CIAN)}
<rect class="blink" x="{x0 + MONO.ancho('> Construyendo algo para el espacio', 18) + 6:.0f}" y="{H - 80}" width="10" height="20" fill="{CIAN}"/></g>"""
    defs = (bg_def + neb_def + DEFS_ESTRELLA + pl_def + "".join(recortes) +
            '<filter id="resplandor" x="-5%" y="-30%" width="110%" height="160%"><feGaussianBlur stdDeviation="7"/></filter>'
            '<radialGradient id="gal"><stop offset="0" stop-color="#cfe2ff" stop-opacity=".9"/><stop offset=".4" stop-color="#6aa0ff" stop-opacity=".45"/>'
            '<stop offset="1" stop-color="#3a5cff" stop-opacity="0"/></radialGradient>'
            '<linearGradient id="estela" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="130" y2="-44">'
            '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    cuerpo = (bg + neb + estrellas(rng, W, H, 300, 9, banda=(0, 520, 1200, 140, 70)) + galaxia + orbitas +
              fugaz + pl + marcos + texto_html)
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
     "Construyendo algo para el espacio."),
]


def bitacora():
    W = 1200
    rng = random.Random(11)
    nodos = [(90, 190), (370, 168), (650, 136), (930, 96)]
    ruta = catmull([(0, 205)] + nodos)
    futuro = f"M930,96 C1010,72 1100,56 1200,40"
    partes, fondo_texto = [], 0
    for i, ((x, y), (num, titulo, cuerpo_txt)) in enumerate(zip(nodos, CAPITULOS)):
        tx = x - 10
        bloque = [texto(tx, 262, num, O5, 18, CIAN, ls=3)]
        lineas_t = envolver(titulo, E6, 24, 250)
        for j, l in enumerate(lineas_t):
            bloque.append(texto(tx, 300 + j * 30, l, E6, 24, BLANCO))
        y_p = 300 + len(lineas_t) * 30 + 12
        p, n = parrafo(tx, y_p, cuerpo_txt, E4, 19, GRIS_CLARO, 250, 29)
        bloque.append(p)
        fondo_texto = max(fondo_texto, y_p + (n - 1) * 29)
        partes.append("".join(bloque))
        if i < 3:
            partes.append(f'<circle cx="{x}" cy="{y}" r="9" fill="none" stroke="{CIAN}" stroke-width="1.5" class="pulse" '
                          f'style="animation-delay:{i * .8:.1f}s"/><circle cx="{x}" cy="{y}" r="9" fill="{FONDO_B}" '
                          f'stroke="{CIAN}" stroke-width="2"/><circle cx="{x}" cy="{y}" r="3.5" fill="{CIAN}"/>')
        else:
            partes.append(f'<circle cx="{x}" cy="{y}" r="40" fill="url(#destino)" class="latido"/>'
                          f'<circle cx="{x}" cy="{y}" r="13" fill="url(#esfera)"/>'
                          f'<circle cx="{x}" cy="{y}" r="13" fill="none" stroke="{AMBAR}" stroke-width="1.5" class="pulse"/>')
    y_linea = fondo_texto + 36
    H = y_linea + 62
    bg_def, bg = fondo(W, H, "70%", "20%")
    defs = (bg_def + DEFS_ESTRELLA +
            f'<linearGradient id="tray" x1="0" x2="1"><stop offset="0" stop-color="{CIAN}" stop-opacity=".1"/>'
            f'<stop offset="1" stop-color="{CIAN}" stop-opacity=".8"/></linearGradient>'
            f'<radialGradient id="destino"><stop offset="0" stop-color="{AMBAR}" stop-opacity=".55"/>'
            f'<stop offset="1" stop-color="{AMBAR}" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="esfera" cx="35%" cy="35%"><stop offset="0" stop-color="#fff6e0"/>'
            f'<stop offset=".5" stop-color="{AMBAR}"/><stop offset="1" stop-color="#7a4b12"/></radialGradient>')
    trayecto = (f'<path id="ruta" d="{ruta}" fill="none" stroke="url(#tray)" stroke-width="2"/>'
                f'<path d="{futuro}" fill="none" stroke="{AMBAR}" stroke-opacity=".6" stroke-width="2" '
                f'stroke-dasharray="6 8" class="flujo"/>'
                '<g><circle r="12" fill="url(#halo)"/><circle r="2.6" fill="#fff"/>'
                '<animateMotion dur="9s" repeatCount="indefinite" rotate="auto"><mpath href="#ruta"/></animateMotion></g>')
    lema =(f'<path d="M60 {y_linea}H1140" stroke="{CIAN}" stroke-opacity=".18"/>'
            + texto(W / 2, y_linea + 36, "Cada cifra con su fuente, su rango y sus límites.", MONO, 17, GRIS, anchor="middle"))
    css = (".flujo{animation:flujo 1.6s linear infinite}@keyframes flujo{to{stroke-dashoffset:-14}}"
           ".latido{transform-box:fill-box;transform-origin:center;animation:latido 3.4s ease-in-out infinite}"
           "@keyframes latido{50%{transform:scale(1.25);opacity:.6}}")
    cuerpo = bg + estrellas(rng, W, H, 160, 4) + trayecto + "".join(partes) + lema
    etiqueta = "Bitácora de vuelo. " + " ".join(f"{n}. {t}: {c}" for n, t, c in CAPITULOS)
    return svg(W, H, etiqueta, defs, cuerpo, css)


# ---------------------------------------------------------------- órbitas

ORBITAS = [
    ("Data & ML", CIAN, 140, 52,["Python", "pandas", "scikit-learn", "XGBoost", "statsmodels"]),
    ("Geospatial", VERDE, 258, 76,["GeoPandas", "H3", "MapLibre", "Leaflet", "PMTiles", "Satellite data"]),
    ("AI & Security", VIOLETA, 372, 100,["Claude Code", "AI agents", "Ollama", "Threat modeling", "Docker", "gitleaks"]),
    ("Full-stack", AMBAR, 486, 128,["FastAPI", "Go", "gRPC", "PostgreSQL", "React", "Next.js", "TypeScript", "Tailwind"]),
]


def orbitas():
    W, H = 1200, 640
    cx, cy, k = 600, 300, .5
    rng = random.Random(5)
    bg_def, bg = fondo(W, H, "50%", "45%")
    capas = []
    for _, color, R, dur, techs in ORBITAS:
        capas.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{R}" ry="{R * k:.1f}" fill="none" stroke="{color}" '
                     f'stroke-opacity=".32" stroke-dasharray="3 6"/>')
        for i, t in enumerate(techs):
            st = f'style="animation-duration:{dur}s;animation-delay:-{dur * i / len(techs):.2f}s"'
            nodo = (f'<circle r="11" fill="{color}" fill-opacity=".18"/><circle r="5.5" fill="{color}"/>'
                    + texto(0, -15, t, E6, 16, BLANCO, anchor="middle",
                            extra='paint-order="stroke" stroke="#050914" stroke-width="5"'))
            # El grupo gira en el plano achatado y contra-gira sin achatar: el texto queda derecho.
            capas.append(f'<g transform="translate({cx} {cy}) scale(1 {k})"><g class="sp" {st}>'
                         f'<g transform="translate({R} 0)"><g class="un" {st}><g transform="scale(1 {1 / k:.4f})">'
                         f'<g class="prof" {st}>{nodo}</g></g></g></g></g></g>')
    nucleo = (f'<circle cx="{cx}" cy="{cy}" r="90" fill="url(#corona)" class="latido"/>'
              f'<circle cx="{cx}" cy="{cy}" r="38" fill="url(#sol)"/>'
              + texto(cx, cy + 9, "DJ", O7, 26, "#06101f", anchor="middle"))
    leyenda, x = [], 0
    items = [(n, c) for n, c, *_ in ORBITAS]
    total = sum(E6.ancho(n, 18) + 60 for n, _ in items)
    x = (W - total) / 2
    for n, c in items:
        leyenda.append(f'<circle cx="{x + 7:.0f}" cy="{H - 36}" r="6" fill="{c}"/>' + texto(x + 22, H - 30, n, E6, 18, GRIS_CLARO))
        x += E6.ancho(n, 18) + 60
    defs = (bg_def + DEFS_ESTRELLA +
            '<radialGradient id="corona"><stop offset="0" stop-color="#bfe8ff" stop-opacity=".55"/>'
            '<stop offset=".45" stop-color="#5ec8ff" stop-opacity=".15"/><stop offset="1" stop-color="#5ec8ff" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="sol" cx="40%" cy="38%"><stop offset="0" stop-color="#ffffff"/>'
            '<stop offset=".6" stop-color="#cdeeff"/><stop offset="1" stop-color="#7fd4ff"/></radialGradient>')
    css = (".prof{animation:prof linear infinite}"
           "@keyframes prof{0%{opacity:.9}25%{opacity:1}50%{opacity:.9}75%{opacity:.4}100%{opacity:.9}}"
           ".latido{transform-box:fill-box;transform-origin:center;animation:latido 5s ease-in-out infinite}"
           "@keyframes latido{50%{transform:scale(1.12);opacity:.75}}")
    cuerpo = bg + estrellas(rng, W, H, 170, 4) + nucleo + "".join(capas) + "".join(leyenda)
    etiqueta = "Sistema orbital de habilidades. " + ". ".join(f"{n}: {', '.join(t)}" for n, _, _, _, t in ORBITAS)
    return svg(W, H, etiqueta, defs, cuerpo, css)


# ---------------------------------------------------------------- misiones

def icono_globo():
    meridianos = "".join(
        f'<ellipse rx="0" ry="44" fill="none" stroke="#bfe9ff" stroke-opacity=".45">'
        f'<animate attributeName="rx" values="0;44;0" dur="7.5s" begin="-{i * 2.5}s" repeatCount="indefinite"/></ellipse>'
        for i in range(3))
    paralelos = "".join(f'<ellipse cy="{y}" rx="{rx}" ry="6" fill="none" stroke="#bfe9ff" stroke-opacity=".35"/>'
                        for y, rx in [(-24, 37), (0, 44), (24, 37)])
    orbita = elipse_path(0, 0, 66, 18)
    return ('<circle r="50" fill="none" stroke="#5ec8ff" stroke-width="5" stroke-opacity=".25" filter="url(#suave)"/>'
            '<circle r="44" fill="url(#oceano)"/>'
            f'<g clip-path="url(#globo)">{meridianos}{paralelos}</g><circle r="44" fill="url(#luz)"/>'
            f'<g transform="rotate(-20)"><path id="orbG" d="{orbita}" fill="none" stroke="#fff" stroke-opacity=".25" stroke-dasharray="2 4"/>'
            '<circle r="3" fill="#fff"><animateMotion dur="6s" repeatCount="indefinite"><mpath href="#orbG"/></animateMotion></circle></g>')


def icono_hex():
    r, d = 17, 17 * math.sqrt(3)
    centros = [(0, 0)] + [(d * math.cos(math.radians(30 + 60 * k)), d * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    out = []
    for i, (x, y) in enumerate(centros):
        pts = " ".join(f"{x + r * math.cos(math.radians(60 * k)):.1f},{y + r * math.sin(math.radians(60 * k)):.1f}" for k in range(6))
        if i == 0:
            out.append(f'<polygon points="{pts}" fill="{ROJO}" class="calor" stroke="{ROJO}"/>')
        elif i in (1, 2):
            out.append(f'<polygon points="{pts}" fill="#ff9f5d" fill-opacity=".3" stroke="#ff9f5d" stroke-opacity=".7"/>')
        else:
            out.append(f'<polygon points="{pts}" fill="#7fd4ff" fill-opacity=".05" stroke="#7fd4ff" stroke-opacity=".5"/>')
    return "".join(out)


def icono_escudo():
    return ('<path d="M0,-46 L38,-31 L38,4 C38,28 20,41 0,50 C-20,41 -38,28 -38,4 L-38,-31 Z" fill="#7fd4ff" fill-opacity=".07" '
            'stroke="#7fd4ff" stroke-width="2"/>'
            '<path d="M-14,2 L-4,12 L16,-10" fill="none" stroke="#6ee7b7" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle r="5" fill="{ROJO}" class="ataque"/><circle cx="41" r="8" fill="none" stroke="{ROJO}" stroke-width="2" class="choque"/>')


def icono_manglar():
    return ('<circle r="46" fill="#0a2a3a"/>'
            '<path d="M-38,10 C-30,-30 20,-44 38,-12 C46,10 20,36 -6,34 C-24,33 -40,28 -38,10Z" fill="#2f8f5b" class="perdida" style="animation-delay:-1s"/>'
            '<path d="M-24,8 C-18,-18 14,-28 26,-8 C32,8 14,24 -4,22 C-16,21 -26,18 -24,8Z" fill="#3fbf7a"/>'
            '<path d="M-10,6 C-8,-6 6,-10 12,-2 C14,6 6,12 -2,11 C-8,10 -11,9 -10,6Z" fill="#7ee8a8"/>'
            '<circle r="46" fill="none" stroke="#6ee7b7" stroke-opacity=".4" stroke-dasharray="3 5"/>')


def icono_barras():
    alturas = [34, 58, 26, 72, 48]
    return "".join(f'<rect x="{-42 + i * 18}" y="{36 - h}" width="11" height="{h}" rx="2" fill="{CIAN}" '
                   f'fill-opacity="{.45 + i * .1:.2f}" class="barra" style="animation-delay:-{i * .45:.2f}s"/>'
                   for i, h in enumerate(alturas)) + '<path d="M-48 38H48" stroke="#7fd4ff" stroke-opacity=".5"/>'


def icono_documento():
    lineas = "".join(f'<path d="M-20 {y}H{w}" stroke="#a9b6d3" stroke-opacity=".6" stroke-width="3" stroke-linecap="round"/>'
                     for y, w in [(-24, 18), (-12, 20), (0, 8), (12, 14)])
    return ('<rect x="-32" y="-44" width="64" height="86" rx="7" fill="#7fd4ff" fill-opacity=".06" stroke="#7fd4ff" stroke-width="2"/>'
            + lineas +
            '<circle cx="26" cy="32" r="16" fill="#0b1224" stroke="#6ee7b7" stroke-width="2"/>'
            '<path d="M18,32 L24,38 L34,26" fill="none" stroke="#6ee7b7" stroke-width="3.5" stroke-linecap="round" '
            'stroke-linejoin="round" stroke-dasharray="30" class="trazo"/>')


MISIONES = [
    dict(archivo="mision-01-agroversex", idioma="en", nombre="AGROVERSEx", icono=icono_globo, vivo=True,
         lema="Your land seen from space, down to your field.",
         cifra=("49,349", "regions mapped with NASA open data")),
    dict(archivo="mision-02-hexvial", idioma="es", nombre="HEXVIAL", icono=icono_hex, vivo=True,
         lema="Dónde se concentra el riesgo vial en Bogotá.",
         cifra=("31 %", "del riesgo vial en 13 de 123 sectores")),
    dict(archivo="mision-03-bsa", idioma="en", nombre="BSA", icono=icono_escudo, vivo=False,
         lema="When a coding agent gets fooled, what actually stops it?",
         cifra=("336", "sealed runs, 7 permission setups")),
    dict(archivo="mision-04-deforestacion", idioma="es", nombre="EL PARAÍSO QUE SE BORRA", icono=icono_manglar, vivo=True,
         lema="Los manglares de Cartagena de Indias.",
         cifra=("53", "años de manglar documentados")),
    dict(archivo="mision-05-medicamentos", idioma="es", nombre="TABLERO DE MEDICAMENTOS", icono=icono_barras, vivo=True,
         lema="Auditoría farmacoeconómica de una EPS.",
         cifra=("28.482", "dispensaciones analizadas en vivo")),
    dict(archivo="mision-06-rfa", idioma="en", nombre="RFA SCHOLARLY WRITING", icono=icono_documento, vivo=False,
         lema="Scholarly writing without invented sources.",
         cifra=("22", "citation styles, verified references")),
]


def mision(i, m):
    W, H, P = 600, 300, 34
    rng = random.Random(100 + i)
    es = m["idioma"] == "es"
    etiqueta_mision = f"{'MISIÓN' if es else 'MISSION'} {i:02d}"
    estado = ("EN LÍNEA" if es else "LIVE") if m["vivo"] else ("CÓDIGO ABIERTO" if es else "OPEN SOURCE")
    color_estado = VERDE if m["vivo"] else VIOLETA
    x_estado = P + MONO.ancho(etiqueta_mision, 14, 3) + 18
    cab = (texto(P, 52, etiqueta_mision, MONO, 14, CIAN, ls=3) +
           f'<circle cx="{x_estado + 5:.0f}" cy="47" r="4.5" fill="{color_estado}" class="t1"/>' +
           texto(x_estado + 16, 52, estado, MONO, 14, color_estado, ls=2))
    size = 30
    while O7.ancho(m["nombre"], size, 1) > 400:
        size -= 1
    y = 100
    partes = [cab, texto(P, y, m["nombre"], O7, size, BLANCO, ls=1)]
    y += 36
    lema = envolver(m["lema"], E6, 21, 420)
    if len(lema) == 2:  # reparte las palabras para no dejar una sola en la segunda línea
        palabras = m["lema"].split()
        corte = min(range(1, len(palabras)), key=lambda c: max(E6.ancho(" ".join(palabras[:c]), 21),
                                                                 E6.ancho(" ".join(palabras[c:]), 21)))
        lema = [" ".join(palabras[:corte]), " ".join(palabras[corte:])]
    for l in lema:
        partes.append(texto(P, y, l, E6, 21, "#dbe6ff"))
        y += 28
    num, lab = m["cifra"]
    y_cifra = H - 64
    assert y - 28 + 8 < y_cifra - 40, f"{m['archivo']}: el lema choca con la cifra"
    partes.append(texto(P, y_cifra, num, O5, 40, CIAN))
    partes.append(texto(P, y_cifra + 30, lab, MONO, 14, GRIS))
    defs = (DEFS_ESTRELLA +
            f'<clipPath id="tarjeta"><rect width="{W}" height="{H}" rx="18"/></clipPath>'
            '<clipPath id="globo"><circle r="44"/></clipPath><filter id="suave"><feGaussianBlur stdDeviation="4"/></filter>'
            '<radialGradient id="oceano" cx="38%" cy="35%"><stop offset="0" stop-color="#4fb3e8"/><stop offset=".55" stop-color="#145d8c"/>'
            '<stop offset="1" stop-color="#061a2e"/></radialGradient>'
            '<radialGradient id="luz" cx="32%" cy="30%" r="80%"><stop offset="0" stop-color="#fff" stop-opacity=".18"/>'
            '<stop offset=".5" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".7"/></radialGradient>'
            '<linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1630"/>'
            '<stop offset="1" stop-color="#060a16"/></linearGradient>'
            f'<linearGradient id="borde_t" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{CIAN}" stop-opacity=".7"/>'
            f'<stop offset=".5" stop-color="{CIAN}" stop-opacity=".08"/><stop offset="1" stop-color="{VIOLETA}" stop-opacity=".5"/></linearGradient>'
            f'<linearGradient id="barrido" x1="0" x2="1"><stop offset="0" stop-color="{CIAN}" stop-opacity="0"/>'
            f'<stop offset=".5" stop-color="{CIAN}" stop-opacity=".35"/><stop offset="1" stop-color="{CIAN}" stop-opacity="0"/></linearGradient>')
    esquinas = "".join(f'<path d="{d}" fill="none" stroke="{CIAN}" stroke-width="2" stroke-opacity=".8"/>' for d in
                       ["M10 34V10H34", f"M{W - 34} {H - 10}H{W - 10}V{H - 34}"])
    cuerpo = (f'<g clip-path="url(#tarjeta)"><rect width="{W}" height="{H}" fill="url(#panel)"/>'
              + estrellas(rng, W, H, 35, 1) +
              f'<rect class="barrido" width="{W}" height="2" fill="url(#barrido)"/></g>'
              f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="18" fill="none" stroke="url(#borde_t)" stroke-width="1.5"/>'
              + esquinas + f'<g transform="translate({W - 92} 112)">{m["icono"]()}</g>'
              + "".join(partes))
    css = (f".barrido{{animation:barrido 7s linear infinite}}@keyframes barrido{{from{{transform:translateY(-10px)}}to{{transform:translateY({H + 10}px)}}}}"
           ".calor{animation:calor 2.4s ease-in-out infinite}@keyframes calor{50%{fill-opacity:.25}}"
           ".ataque{animation:ataque 3s ease-in infinite}@keyframes ataque{0%{transform:translateX(95px);opacity:0}"
           "15%{opacity:1}60%{transform:translateX(41px);opacity:1}66%,100%{transform:translateX(41px);opacity:0}}"
           ".choque{transform-box:fill-box;transform-origin:center;opacity:0;animation:choque 3s ease-out infinite}"
           "@keyframes choque{0%,58%{transform:scale(.4);opacity:0}62%{opacity:1}100%{transform:scale(2.2);opacity:0}}"
           ".perdida{transform-box:fill-box;transform-origin:center;animation:perdida 6s ease-in-out infinite alternate}"
           "@keyframes perdida{to{transform:scale(.82);opacity:.55}}"
           ".barra{transform-box:fill-box;transform-origin:bottom;animation:barra 2.2s ease-in-out infinite alternate}"
           "@keyframes barra{from{transform:scaleY(.35)}}"
           ".trazo{animation:trazo 4s ease-out infinite}@keyframes trazo{0%{stroke-dashoffset:30}30%,100%{stroke-dashoffset:0}}")
    etiqueta = f"{etiqueta_mision}: {m['nombre']}. {m['lema']} {num} {lab}."
    return svg(W, H, etiqueta, defs, cuerpo, css)


# ---------------------------------------------------------------- cierre

def cierre():
    W, H = 1200, 320
    rng = random.Random(3)
    defs = (DEFS_ESTRELLA +
            f'<linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{FONDO_B}"/>'
            '<stop offset="1" stop-color="#071228"/></linearGradient>'
            '<radialGradient id="tierra" cx="50%" cy="0%" r="60%"><stop offset="0" stop-color="#0d2c5c"/>'
            '<stop offset=".25" stop-color="#071a38"/><stop offset="1" stop-color="#02060f"/></radialGradient>'
            '<radialGradient id="alba" cx="50%" cy="50%"><stop offset="0" stop-color="#ffe2b0" stop-opacity=".95"/>'
            '<stop offset=".3" stop-color="#ffb46b" stop-opacity=".45"/><stop offset="1" stop-color="#ff8a3d" stop-opacity="0"/></radialGradient>'
            '<filter id="atm" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="9"/></filter>'
            '<filter id="atm2" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="2"/></filter>')
    cx, cy, r = 600, 1660, 1420
    luces = "".join(f'<circle cx="{rng.uniform(250, 950):.0f}" cy="{rng.uniform(262, 316):.0f}" r="{rng.uniform(.6, 1.4):.1f}" '
                    f'fill="#ffcf8a" fill-opacity="{rng.uniform(.3, .8):.2f}" class="t{rng.randint(1, 3)}"/>' for _ in range(40))
    cuerpo = (f'<rect width="{W}" height="{H}" fill="url(#cielo)"/>' + estrellas(rng, W, 230, 120, 3) +
              f'<circle cx="{cx}" cy="{cy}" r="{r + 10}" fill="none" stroke="#5ec8ff" stroke-width="22" stroke-opacity=".28" filter="url(#atm)"/>'
              f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#tierra)"/>'
              f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#8fdcff" stroke-width="2.5" filter="url(#atm2)"/>'
              f'<ellipse cx="930" cy="{cy - r + 4}" rx="300" ry="26" fill="url(#alba)" class="alba"/>'
              + luces
              + texto(W / 2, 100, "Nací para el espacio.", E6, 34, BLANCO, anchor="middle")
              + texto(W / 2, 142, "Mientras llego, sigo mirando la Tierra desde arriba.", MONO, 17, GRIS, anchor="middle"))
    css = ".alba{animation:alba 9s ease-in-out infinite}@keyframes alba{50%{opacity:.55}}"
    return svg(W, H, "Nací para el espacio. Mientras llego, sigo mirando la Tierra desde arriba.", defs, cuerpo, css)


# ---------------------------------------------------------------- salida

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")


def main():
    salidas = {"hero": encabezado(), "bitacora": bitacora(), "orbitas": orbitas(), "cierre": cierre()}
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
