#!/usr/bin/env python3
"""Construye correos transaccionales de Tradeview Markets a partir de specs JSON.

Estándar del equipo de desarrollo: un solo archivo HTML por correo, maquetado con tablas, CSS 100% inline
(sin <style>, sin flexbox), imágenes por URL del bucket S3 y variables Jinja {{ data['...'] }}.

La estructura y los estilos salen de la BASE (base/): base.html (esqueleto), tokens.json (estilos) y
variants.json (variantes de header y footer). Este script solo arma el contenido con esos valores.

Por cada spec genera:
  produccion/<nombre>.html       -> lo que se entrega a dev (imágenes apuntando a S3, variables Jinja)
  produccion/subir-a-s3/*.png    -> imágenes del correo que todavía no tienen URL de S3 (se le piden a desarrollo)
  preview/<nombre>.html          -> archivo único con SVG incrustado, para ver y aprobar en cualquier navegador
  pdf/<nombre>.pdf               -> para compartir y aprobar diseño
Además: ABRIR-AQUI.html y LEEME.txt en la raíz de la carpeta de salida.

<nombre> = <slug>-<lang>-<entity>, ej. deposit-confirmed-es-sac.

Uso:
  python scripts/build_email.py spec1.json [spec2.json ...] --out salida
  Opciones: --no-pdf  --screenshots (PNG a 750 y 390 px)

Formato del spec: ver references/spec-format.md · Integración con backend: delivery.json
"""
import argparse, base64, datetime, html, json, re, shutil, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG_DIR = ROOT / "assets" / "svg"
PNG_DIR = ROOT / "assets" / "png"
LOCALES = ROOT / "locales"
BASE = ROOT / "base"
DELIVERY = json.loads((ROOT / "delivery.json").read_text())
TOKENS = json.loads((BASE / "tokens.json").read_text())
VARIANTS = json.loads((BASE / "variants.json").read_text())
SKELETON = (BASE / "base.html").read_text()
YEAR = str(datetime.date.today().year)

# Atajos a la base de estilos
C = {k: v["value"] for k, v in TOKENS["colors"].items()}       # colores
TY = TOKENS["type"]                                             # tipografía
LY = TOKENS["layout"]                                           # medidas generales
K = TOKENS["components"]                                        # medidas de componentes
PILLS = {k: (v["bg"], v["fg"]) for k, v in TOKENS["pills"].items()}
HERO = TOKENS["hero"]

W, PAD = LY["width"], LY["pad"]
CW = W - 2 * PAD            # ancho de contenido
G, g = LY["gap_group"], LY["gap_tight"]
ICONS = {p.stem[5:] for p in SVG_DIR.glob("icon-*.svg")}
PLATFORMS = {  # asset, ancho, alto, etiqueta por defecto
    "windows": ("brand-windows", 24, 24, "Windows"),
    "macos": ("brand-macos", 85, 20, "MacOS"),
    "ios": ("brand-appstore", 28, 28, "iPhone or iPad"),
    "android": ("brand-googleplay", 28, 28, "Android"),
    "web": ("brand-web", 24, 24, "Web version"),
}
BODY_ORDER = ["hero", "icon", "title", "subtitle", "image", "greeting", "content", "cta"]
CONTENT = {"paragraph", "pill", "list_card", "details_card", "heading", "code", "alert", "note", "steps"}
TIGHT = {  # pares de bloques que van a gap_tight (mismo grupo en Figma); el resto va a gap_group
    ("icon", "*"), ("title", "subtitle"), ("greeting", "*"), ("heading", "*"),
    ("paragraph", "paragraph"), ("paragraph", "pill"), ("paragraph", "list_card"), ("paragraph", "note"),
    ("pill", "paragraph"), ("pill", "pill"), ("details_card", "alert"), ("code", "alert"),
    ("note", "steps"), ("note", "note"),
}

# Se fijan por idioma en set_locale()
FONT = TXT = START = END = LANG = ""
LOC = {}


def fs(style):
    """font-size + line-height de un estilo de tokens.json."""
    t = TY[style]
    return f"font-size:{t['size']}px;line-height:{t['lh']}px;"


def set_locale(lang):
    global FONT, TXT, START, END, LOC, LANG
    path = LOCALES / f"{lang}.json"
    if not path.exists():
        sys.exit(f"Idioma '{lang}' sin locales/{lang}.json. Disponibles: {sorted(p.stem for p in LOCALES.glob('*.json'))}")
    LOC, LANG = json.loads(path.read_text()), lang
    FONT = LOC["font"]
    TXT = f"font-family:{FONT};color:{C['text']};"
    START, END = ("right", "left") if LOC["dir"] == "rtl" else ("left", "right")


def variant(kind, name):
    options = VARIANTS[kind]
    if name not in options:
        sys.exit(f"Variante de {kind} '{name}' no existe en base/variants.json. Disponibles: {sorted(options)}")
    return options[name]


class Ctx:
    """Recolecta los assets usados por un correo."""
    def __init__(self, spec_dir):
        self.spec_dir = spec_dir
        self.pngs = set()      # nombres de assets/png usados
        self.images = {}       # nombre destino -> ruta local de imágenes propias (banners)


def img(ctx, name, w, h, alt, style="", display="block", fluid=False, url=None):
    """<img> a {ASSET}<name>-2x.png (o a `url` si la imagen ya está en S3). En preview se incrusta.
    fluid: se encoge en pantallas angostas."""
    size = f"width:100%;max-width:{w}px;" if fluid else f"width:{w}px;"
    if url:
        src, data = url, f'data-remote="1" data-svg="{name}"'
    else:
        ctx.pngs.add(f"{name}-2x.png")
        src, data = f"{{ASSET}}{name}-2x.png", f'data-svg="{name}"'
    return (f'<img src="{src}" {data} width="{w}" height="{h}" alt="{html.escape(alt)}" '
            f'style="display:{display};border:0;outline:none;text-decoration:none;{size}height:auto;{style}">')


def logo(ctx, l, **kw):
    return img(ctx, l["asset"], l["width"], l["height"], l["alt"], url=l.get("url"), **kw)


def links(text, color=None):
    """Estilo inline para <a> que vengan sin style en el spec."""
    color = color or C["link"]
    return re.sub(r"<a (?![^>]*style=)", f'<a style="color:{color};text-decoration:underline;" ', text)


def status_icon(ctx, name, alt, size=None, style=""):
    size = size or K["icon"]["status"]
    if name not in ICONS:
        sys.exit(f"Icono '{name}' no existe. Disponibles: {sorted(ICONS)}. "
                 f"Descárgalo de Google Fonts a assets/svg/icon-{name}.svg y corre build_assets.py")
    return img(ctx, "icon-" + name, size, size, alt, style=f"height:{size}px;" + style)


def p(text, style="body", mb=None, weight=None, color=None):
    mb = g if mb is None else mb
    weight = TY[style]["weight"] if weight is None else weight
    return (f'    <p style="margin:0 0 {mb}px;{TXT}{fs(style)}font-weight:{weight};'
            f'text-align:{START};">{links(text, color)}</p>\n')


def table(inner, width="100%", style="", attrs=""):
    w = f'width="{width}" ' if width else ""
    return (f'<table role="presentation" {w}cellpadding="0" cellspacing="0" border="0" {attrs}'
            f'style="border-collapse:separate;{style}">{inner}</table>')


def outline_btn(ctx, label, href, icon=None, full=False):
    b = K["button"]
    ic = (f'<td style="padding-{START}:{b["icon_gap"]}px;vertical-align:middle;">'
          f'{img(ctx, icon, b["icon"], b["icon"], "", style="height:%spx;" % b["icon"])}</td>' if icon else "")
    inner = table(f'<tr><td style="font-family:{FONT};{fs("button")}font-weight:{TY["button"]["weight"]};color:{C["outline_button"]};'
                  f'white-space:nowrap;">{label}</td>{ic}</tr>', width="", style="margin:0 auto;")
    return table(f'<tr><td align="center" style="border:{b["border"]} solid {C["outline_button"]};border-radius:{b["radius"]}px;padding:{b["pad"]};">'
                 f'<a href="{href}" target="_blank" style="text-decoration:none;color:{C["outline_button"]};display:block;">{inner}</a></td></tr>',
                 width="100%" if full else "", style="margin:0 auto;")


def columns(cells, total, gap):
    """Columnas que se apilan solas en pantallas angostas (tablas align, sin media queries).
    cells: [(ancho, html)]. En Outlook desktop se fuerza una fila con una tabla fantasma."""
    out = f'<!--[if mso]><table role="presentation" width="{total}" cellpadding="0" cellspacing="0" border="0"><tr><![endif]-->\n'
    for i, (w, content) in enumerate(cells):
        last = i == len(cells) - 1
        align = END if (last and len(cells) == 2) else START
        out += f'<!--[if mso]><td width="{w}" valign="top"><![endif]-->\n'
        out += table(f'<tr><td valign="top">{content}</td></tr>', width=str(w), attrs=f'align="{align}" ',
                     style=f"width:100%;max-width:{w}px;" + ("" if last else f"margin-bottom:{gap}px;"))
        out += "\n<!--[if mso]></td>" + ("" if last else f'<td width="{gap}"></td>') + "<![endif]-->\n"
    out += "<!--[if mso]></tr></table><![endif]-->\n"
    # la celda contenedora encierra las tablas flotantes para que el texto siguiente no se meta al lado
    return table(f"<tr><td>\n{out}</td></tr>") + "\n"


# ---------------------------------------------------------------- bloques del body
def b_hero(ctx, b):
    """Banner con degradado (estilo 'old'): solo para correos transaccionales de depósito/retiro/transferencia/formularios."""
    size = K["icon"]["status"]
    icon = (f'<td valign="middle" style="padding-{END}:{HERO["icon_gap"]}px;width:{size}px;">{status_icon(ctx, b["icon"], b.get("alt", ""))}</td>'
            if b.get("icon") else "")
    bg = f'background-color:{HERO["fallback"]};background-image:{HERO["background"]};'
    title = (f'<td valign="middle"><h1 style="margin:0;font-family:{FONT};{fs("hero_title")}font-weight:{TY["hero_title"]["weight"]};'
             f'color:{C["text"]};text-align:{START};">{b["title"]}</h1></td>')
    return f'''  <!-- ===== HERO (degradado) ===== -->
  <tr><td bgcolor="{HERO["fallback"]}" height="{HERO["height"]}" valign="middle" style="{bg}height:{HERO["height"]}px;padding:0 {PAD}px;">
    {table(f"<tr>{icon}{title}</tr>", width="", attrs='align="center" ')}
  </td></tr>
'''


def b_icon(ctx, b, mb):
    return f'    <!-- Icono de estado -->\n    {status_icon(ctx, b["name"], b.get("alt", ""), style=f"margin:0 0 {mb}px;")}\n'


def b_title(ctx, b, mb):
    return (f'    <h1 style="margin:0 0 {mb}px;font-family:{FONT};{fs("h1")}'
            f'font-weight:{TY["h1"]["weight"]};color:{C["text"]};text-align:{START};">{b["text"]}</h1>\n')


def b_subtitle(ctx, b, mb):
    return p(b["text"], mb=mb)


def b_image(ctx, b, mb):
    src = b["src"]
    if not re.match(r"https?://", src):
        local = (ctx.spec_dir / src).resolve()
        if not local.exists():
            sys.exit(f"Imagen no encontrada: {local}")
        ctx.images[local.name] = local
        src = "{ASSET}" + local.name
    return (f'    <img src="{src}" width="{CW}" alt="{html.escape(b.get("alt", ""))}" '
            f'style="display:block;border:0;width:100%;max-width:{CW}px;height:auto;margin:0 0 {mb}px;">\n')


def b_greeting(ctx, b, mb):
    return p(b.get("text", LOC["greeting"]), mb=mb)


def b_paragraph(ctx, b, mb):
    return p(b["text"], mb=b.get("margin_bottom", mb))


def b_heading(ctx, b, mb):
    return p(b["text"], style="section", mb=mb)


def b_pill(ctx, b, mb):
    bg, fg = PILLS[b.get("variant", "warning")]
    k = K["pill"]
    return (f'    <p style="margin:0 0 {mb}px;text-align:{START};"><span style="display:inline-block;background:{bg};color:{fg};'
            f'font-family:{FONT};{fs("body")}padding:{k["pad"]};border-radius:{k["radius"]}px;">{b["text"]}</span></p>\n')


def card(inner, mb, pad=None, bg=None, radius=None, extra=""):
    pad = pad or K["card"]["pad"]
    bg = bg or C["card"]
    radius = K["card"]["radius"] if radius is None else radius
    return "    " + table(f'\n      <tr><td bgcolor="{bg}" style="background:{bg};border-radius:{radius}px;padding:{pad};{extra}">\n'
                          f'{inner}      </td></tr>\n    ', style=f"margin:0 0 {mb}px;") + "\n"


def b_list_card(ctx, b, mb):
    k = K["list_card"]
    items = b["items"]
    rows = ""
    cell = f"font-family:{FONT};{fs('body')}color:{C['text']};text-align:{START};"
    for i, it in enumerate(items):
        pb = "0" if i == len(items) - 1 else f"{k['item_gap']}px"
        rows += (f'          <tr><td valign="top" width="{k["bullet_width"]}" style="width:{k["bullet_width"]}px;padding:0 0 {pb};{cell}">&bull;</td>'
                 f'<td valign="top" style="padding:0 0 {pb};{cell}">{links(it)}</td></tr>\n')
    pad = k["pad_rtl"] if START == "right" else k["pad"]
    return "    <!-- Card de lista -->\n" + card(f"        {table(chr(10) + rows + '        ')}\n", mb, pad=pad)


def detail_rows(rows):
    k = K["card"]
    out = ""
    cell = f"font-family:{FONT};{fs('body')}color:{C['text']};"
    for i, row in enumerate(rows):
        key, v = row[0], row[1]
        pb = "0" if i == len(rows) - 1 else f"{k['row_gap']}px"
        val = f"{v}{K['code']['copy_gap']}{{COPY}}" if len(row) > 2 and row[2] == "copy" else v
        out += (f'          <tr><td valign="top" style="padding:0 0 {pb};padding-{END}:{k["label_gap"]}px;{cell}text-align:{START};">{key}</td>'
                f'<td valign="top" align="{END}" style="padding:0 0 {pb};{cell}font-weight:{TY["body_bold"]["weight"]};text-align:{END};">{val}</td></tr>\n')
    return out


def copy_icon(ctx, doc):
    if "{COPY}" not in doc:
        return doc
    s = K["copy_icon"]["size"]
    return doc.replace("{COPY}", img(ctx, "ui-copy", s, s, "", display="inline-block", style=f"height:{s}px;vertical-align:middle;"))


def b_details_card(ctx, b, mb):
    k = K["card"]
    out = b_heading(ctx, {"text": b["title"]}, g) if b.get("title") else ""
    if b.get("sections"):
        inner = ""
        for j, s in enumerate(b["sections"]):
            if s.get("title"):
                inner += (f'        <p style="margin:{0 if j == 0 else k["section_gap"]}px 0 {k["section_title_gap"]}px;{TXT}{fs("body_bold")}'
                          f'font-weight:{TY["body_bold"]["weight"]};text-align:{START};">{s["title"]}</p>\n')
            inner += f"        {table(chr(10) + detail_rows(s['rows']) + '        ')}\n"
    else:
        inner = f"        {table(chr(10) + detail_rows(b['rows']) + '        ')}\n"
    return out + "    <!-- Card de detalles -->\n" + copy_icon(ctx, card(inner, mb))


def b_code(ctx, b, mb):
    k = K["code"]
    out = b_heading(ctx, {"text": b["label"]}, k["label_gap"]) if b.get("label") else ""
    inner = (f'        <p style="margin:0;{TXT}{fs("body_bold")}font-weight:{TY["body_bold"]["weight"]};letter-spacing:{k["letter_spacing"]}px;'
             f'text-align:{START};">{b["code"]}{k["copy_gap"]}{{COPY}}</p>\n')
    return out + "    <!-- Código de un solo uso -->\n" + copy_icon(ctx, card(inner, mb))


def b_alert(ctx, b, mb):
    k = K["alert"]
    inner = "        " + table(
        f'<tr><td valign="top" width="{k["icon"]}" style="width:{k["icon"]}px;padding-top:1px;padding-{END}:{k["icon_gap"]}px;">'
        f'{img(ctx, "ui-info", k["icon"], k["icon"], "", style="height:%spx;" % k["icon"])}</td>'
        f'<td valign="top" style="font-family:{FONT};{fs("alert")}color:{C["text"]};text-align:{START};">'
        f'{links(b["text"])}</td></tr>') + "\n"
    return "    <!-- Aviso -->\n" + card(inner, mb, pad=k["pad"], bg=C["surface"], radius=k["radius"],
                                        extra=f"border:{k['border']} solid {C['border_accent']};")


def b_note(ctx, b, mb):
    k = K["note"]
    ic = ""
    if b.get("icon"):
        n = K["icon"]["note_icon"]
        asset, w, h = {"apple": ("brand-apple", 15, 18)}.get(b["icon"], ("icon-" + b["icon"], n, n))
        ic = f'<td valign="middle" style="padding-{END}:{k["icon_gap"]}px;">{img(ctx, asset, w, h, "", style=f"height:{h}px;")}</td>'
    inner = table(f'<tr>{ic}<td valign="middle" style="font-family:{FONT};{fs("body")}color:{C["text"]};'
                  f'text-align:{START};">{links(b["text"], C["link_note"])}</td></tr>', width="")
    return ("    <!-- Nota -->\n    " + table(f'<tr><td style="border:{k["border"]} solid {C["border_accent"]};border-radius:{k["radius"]}px;padding:{k["pad"]}px;">{inner}</td></tr>',
                                             width="", style=f"margin:0 0 {mb}px;") + "\n")


def downloads(ctx, items):
    k = K["steps"]
    inner_w = CW - 2 * k["pad"]
    w = inner_w // len(items)
    cells = []
    for d in items:
        asset, aw, ah, label = PLATFORMS[d["platform"]]
        logo = img(ctx, asset, aw, ah, label, style=f"height:{ah}px;margin:0 auto;")
        btn = outline_btn(ctx, d.get("label", label), d.get("href", "#"), icon="ui-download")
        cells.append((w, table(f'<tr><td align="center" valign="bottom" height="{k["logo_row"]}" style="height:{k["logo_row"]}px;">{logo}</td></tr>'
                             f'<tr><td align="center" style="padding:{k["button_gap"]}px 0 0;">{btn}</td></tr>', style="margin:0 auto;")))
    if len(cells) == 4:  # pares con 2 columnas fluidas: 1×4 en desktop, 2×2 en mobile
        half = inner_w // 2
        pair = lambda a, b: table(f'<tr><td width="50%" valign="bottom" style="width:50%;">{a[1]}</td>'
                                  f'<td width="50%" valign="bottom" style="width:50%;">{b[1]}</td></tr>')
        return columns([(half, pair(cells[0], cells[1])), (half, pair(cells[2], cells[3]))], inner_w, k["column_gap"])
    return columns(cells, inner_w, k["column_gap"])


def b_steps(ctx, b, mb):
    k = K["steps"]
    out = "    <!-- Pasos -->\n"
    items = b["items"]
    for i, s in enumerate(items, 1):
        head = "        " + table(
            f'<tr><td valign="middle" style="padding-{END}:{k["icon_gap"]}px;">{status_icon(ctx, s["icon"], "", size=K["icon"]["step"])}</td>'
            f'<td valign="middle" style="font-family:{FONT};{fs("section")}font-weight:{TY["section"]["weight"]};color:{C["text"]};'
            f'text-align:{START};">{i}. {s["title"]}</td></tr>', width="") + "\n"
        body = (f'        <p style="margin:{k["text_gap"]}px 0 0;{TXT}{fs("body")}text-align:{START};">{links(s["text"])}</p>\n'
                if s.get("text") else "")
        dg = k["downloads_gap"]
        dl = (f'        <div style="height:{dg}px;line-height:{dg}px;font-size:0;">&nbsp;</div>\n{downloads(ctx, s["downloads"])}'
              if s.get("downloads") else "")
        foot = (f'        <p style="margin:{k["footnote_gap"]}px 0 0;{TXT}{fs("legal")}font-style:italic;text-align:{START};">'
                f'{s["footnote"]}</p>\n' if s.get("footnote") else "")
        out += card(head + body + dl + foot, mb if i == len(items) else g, pad=f'{k["pad"]}px', bg=C["surface"], radius=k["radius"])
    return out


def b_cta(ctx, b, mb):
    k = K["cta"]
    t = TY["cta"]
    label, href = b["label"], b.get("href", "[cabinet_url]")
    w = max(k["min_width"], int(len(label) * 10 + 48))
    return f'''    <!-- CTA (bulletproof) -->
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-collapse:separate;margin:0 0 {mb}px;">
      <tr><td align="center" bgcolor="{C["cta"]}" style="background:{C["cta"]};border-radius:{k["radius"]}px;mso-padding-alt:{k["pad"]};">
        <!--[if mso]><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="{href}" style="height:{k["height"]}px;v-text-anchor:middle;width:{w}px;" arcsize="50%" stroke="f" fillcolor="{C["cta"]}"><w:anchorlock/><center style="color:{C["cta_label"]};font-family:{TY["cta_outlook_font"]};font-size:{t["size"]}px;font-weight:{t["weight"]};">{label}</center></v:roundrect><![endif]-->
        <!--[if !mso]><!--><a href="{href}" target="_blank" style="display:inline-block;padding:{k["pad"]};font-family:{FONT};{fs("cta")}font-weight:{t["weight"]};color:{C["cta_label"]};text-decoration:none;border-radius:{k["radius"]}px;">{label}</a><!--<![endif]-->
      </td></tr>
    </table>
'''


def validate(blocks):
    stage = lambda t: "content" if t in CONTENT else t
    ordered = [b["type"] for b in blocks if b["type"] != "cta"]
    idx = [BODY_ORDER.index(stage(t)) for t in ordered]
    if idx != sorted(idx):
        print(f"  ⚠ Orden de bloques fuera del estándar (hero/icono → título → subtítulo → imagen → saludo → contenido → CTA): "
              f"{[b['type'] for b in blocks]}")
    ctas = {(b["label"], b.get("href", "[cabinet_url]")) for b in blocks if b["type"] == "cta"}
    if len(ctas) > 1:
        print("  ⚠ CTAs distintos en el mismo correo: solo se permite repetir el MISMO CTA (misma etiqueta y URL).")
    if any(b["type"] == "hero" for b in blocks) and any(b["type"] in ("icon", "title") for b in blocks):
        print("  ⚠ El hero ya incluye icono y título: quita los bloques icon/title.")
    if any(b["type"] == "hero" for b in blocks[1:]):
        sys.exit("El bloque hero tiene que ser el primero del spec.")


def gap(cur, nxt):
    if nxt is None:
        return G
    return g if (cur, nxt) in TIGHT or (cur, "*") in TIGHT else G


def render_body(ctx, blocks):
    out = ""
    for i, b in enumerate(blocks):
        fn = globals().get("b_" + b["type"])
        if not fn:
            sys.exit(f"Tipo de bloque desconocido: {b['type']}")
        out += fn(ctx, b, gap(b["type"], blocks[i + 1]["type"] if i + 1 < len(blocks) else None))
    return out


# ---------------------------------------------------------------- header, more, footer (según base/variants.json)
def render_header(ctx, name):
    logos = variant("header", name)["logos"]
    tags = [logo(ctx, l, style="margin:0 auto;") for l in logos]
    if len(tags) == 1:
        return tags[0]
    return table("<tr>" + "".join(f'<td style="padding:0 12px;">{t}</td>' for t in tags) + "</tr>", width="", attrs='align="center" ')


def render_more(ctx, more):
    if not more:
        return ""
    more = more if isinstance(more, dict) else {}
    k = K["promo"]
    cw = (CW - k["gap"]) // 2
    cells = []
    for c in VARIANTS["more_from_tradeview"]["cards"]:
        asset, w, h = c["asset"], c["width"], c["height"]
        title, text, btn = LOC[c["text"]]
        href = more.get(c["link"], f"[{c['link']}]")
        head = table(f'<tr><td valign="middle" style="padding-{END}:{k["logo_gap"]}px;">{img(ctx, asset, w, h, title, style=f"height:{h}px;")}</td>'
                     f'<td valign="middle" style="font-family:{FONT};{fs("card_title")}font-weight:{TY["card_title"]["weight"]};color:{C["text"]};'
                     f'text-align:{START};">{title}</td></tr>', width="")
        body = (f'<p style="margin:{k["text_gap"]}px 0;{TXT}{fs("body")}text-align:{START};">{text}</p>'
                f'{outline_btn(ctx, btn, href, full=True)}')
        cells.append((cw, table(f'<tr><td style="border:1px solid {C["border_promo"]};border-radius:{k["radius"]}px;padding:{k["card_pad"]}px;">{head}{body}</td></tr>')))
    return f'''
  <!-- ===== MORE FROM TRADEVIEW ===== -->
  <tr><td bgcolor="{C["surface"]}" style="background:{C["surface"]};padding:{LY["promo_pad_y"]}px {PAD}px;">
    <p style="margin:0 0 {k["title_gap"]}px;{TXT}{fs("section")}font-weight:{TY["section"]["weight"]};text-align:{START};">{LOC["more_title"]}</p>
{columns(cells, CW, k["gap"])}  </td></tr>
'''


def render_signature(show_help=True):
    email = LOC["support_email"]
    help_ = p(LOC["help"].format(email=f'<a href="mailto:{email}">{email}</a>'), mb=G, color=C["link_support"]) if show_help else ""
    return (f'{help_}{p(LOC["signature"], mb=g, weight=TY["body_bold"]["weight"])}'
            f'    <p style="margin:0;font-family:{FONT};{fs("body")}text-align:{START};"><a href="https://www.tradeviewmarkets.com" target="_blank" '
            f'style="color:{C["link"]};text-decoration:underline;">www.tradeviewmarkets.com</a></p>\n')


def render_footer(ctx, entity, name):
    k = K["footer"]
    v = variant("footer", name)
    left = f'<p style="margin:0 0 {k["title_gap"]}px;{TXT}{fs("card_title")}font-weight:{TY["card_title"]["weight"]};text-align:{START};">{LOC["footer_title"]}</p>'
    if v.get("socials"):
        socials = v["socials"]
        cells = ""
        for i, s in enumerate(socials):
            pad = "" if i == len(socials) - 1 else f"padding-{END}:{k['social_gap']}px;"
            cells += (f'<td valign="middle" style="{pad}"><a href="{s["href"]}" target="_blank" style="text-decoration:none;">'
                      f'{img(ctx, s["asset"], k["social"], k["social"], s["alt"], fluid=True, url=s.get("url"))}</a></td>')
        left += table(f"<tr>{cells}</tr>", width=str(k["left_width"]), style=f"width:100%;max-width:{k['left_width']}px;")
    spacer = f'<div style="height:{k["logo_gap"]}px;line-height:{k["logo_gap"]}px;font-size:0;">&nbsp;</div>'
    logos = spacer.join(logo(ctx, l, display="inline-block") for l in v["logos"])
    right = table(f'<tr><td align="{END}" style="text-align:{END};padding-top:{k["logo_pad_top"]}px;">{logos}</td></tr>')
    ldir = LOC.get("legal_dir", LOC["dir"])  # el legal en árabe viene en inglés en Figma
    L = f"font-family:{FONT};{fs('legal')}color:{C['text']};text-align:{'right' if ldir == 'rtl' else 'left'};"
    legal = LOC["legal"][entity]
    legal_html = "".join(f'    <p dir="{ldir}" style="margin:{str(k["legal_top"]) + "px" if i == 0 else "0"} 0 '
                         f'{"0" if i == len(legal) - 1 else str(k["legal_gap"]) + "px"};{L}">{t}</p>\n'
                         for i, t in enumerate(legal))
    return columns([(k["left_width"], left), (k["right_width"], right)], CW, k["column_gap"]) + legal_html


def fill_skeleton(values, slots):
    """Rellena base.html: primero los @@estilos/valores@@, después los <!-- SLOT:... --> con el contenido."""
    def token(m):
        key = m.group(1)
        if key in values:
            return str(values[key])
        node = TOKENS
        for part in key.split("."):
            node = node[part]
        return str(node["value"] if isinstance(node, dict) else node)
    doc = re.sub(r"@@([\w.]+)@@", token, SKELETON)
    for name, content in slots.items():
        doc = doc.replace(f"<!-- SLOT:{name} -->", content)
    return doc


def render(spec, spec_dir):
    lang, entity = spec.get("lang", "en"), spec.get("entity", "ltd")
    set_locale(lang)
    if entity not in LOC["legal"]:
        sys.exit(f"Entidad '{entity}' no existe. Usa: {sorted(LOC['legal'])}")
    ctx = Ctx(spec_dir)
    blocks = spec["blocks"]
    validate(blocks)
    hero = b_hero(ctx, blocks[0]) if blocks and blocks[0]["type"] == "hero" else ""
    body_blocks = blocks[1:] if hero else blocks
    values = {"lang": lang, "dir": LOC["dir"], "subject": html.escape(spec["subject"]), "gfont": LOC["gfont"],
              "preheader": html.escape(spec.get("preheader", "")), "font": FONT, "start": START, "entity": entity.upper()}
    slots = {"header": render_header(ctx, spec.get("header", "standard")), "hero": hero,
             "body": render_body(ctx, body_blocks), "signature": render_signature(spec.get("help", True)),
             "more": render_more(ctx, spec.get("more_from_tradeview")),
             "footer": render_footer(ctx, entity, spec.get("footer", "standard"))}
    doc = fill_skeleton(values, slots)
    doc = doc.replace("{{year}}", YEAR)
    for k, url in DELIVERY["links"].items():
        doc = doc.replace(k, url.format(lang=lang))
    return doc, ctx


def copy_status(spec):
    """Aprobado solo si el texto del spec y los textos fijos del idioma están aprobados."""
    lang = spec.get("lang", "en")
    loc = json.loads((LOCALES / f"{lang}.json").read_text())
    issues = []
    if spec.get("copy", "approved" if lang == "en" else "draft") != "approved":
        issues.append("el texto de este correo")
    if loc.get("status") != "approved":
        issues.append(f"los textos fijos de locales/{lang}.json")
    return issues


def draft_banner(issues):
    return ('<div style="background:#FFE8C2;color:#6B3A00;font-family:Arial,sans-serif;font-size:14px;line-height:20px;'
            'padding:12px 16px;text-align:center;"><b>BORRADOR · traducción por revisar</b> — falta aprobar '
            + " y ".join(issues) + '. Este correo no se entrega a desarrollo.</div>\n')


def out_name(spec):
    return f'{spec["slug"]}-{spec.get("lang", "en")}-{spec.get("entity", "ltd")}'


# ---------------------------------------------------------------- variantes
def svg_inline(name, tag):
    svg = (SVG_DIR / f"{name}.svg").read_text()
    svg = re.sub(r"<\?xml[^>]*>", "", svg).strip()
    open_tag = svg.split(">", 1)[0]
    if "viewBox" not in open_tag:
        w = re.search(r'width="([\d.]+)"', open_tag).group(1)
        h = re.search(r'height="([\d.]+)"', open_tag).group(1)
        svg = svg.replace("<svg", f'<svg viewBox="0 0 {w} {h}"', 1)
    svg = re.sub(r'^(<svg[^>]*?)\s(?:width|height)="[^"]*"', r"\1", svg)
    svg = re.sub(r'^(<svg[^>]*?)\s(?:width|height)="[^"]*"', r"\1", svg)
    get = lambda a: (re.search(a + r'="([^"]*)"', tag) or [None, ""])[1]
    return svg.replace("<svg", f'<svg width="{get("width")}" height="{get("height")}" role="img" '
                               f'aria-label="{get("alt")}" style="{get("style")}"', 1)


def to_production(doc):
    """Imágenes a su URL de S3 y variables a Jinja. Devuelve (html, variables sin mapear, imágenes sin URL)."""
    doc = re.sub(r'\sdata-(?:svg|remote)="[^"]*"', "", doc)
    registered = DELIVERY.get("images", {})
    missing = sorted(set(f for f in re.findall(r"\{ASSET\}([\w.\-]+)", doc) if f not in registered))
    doc = re.sub(r"\{ASSET\}([\w.\-]+)", lambda m: registered.get(m.group(1), f"[S3:{m.group(1)}]"), doc)
    for k, v in DELIVERY["variables"].items():
        doc = doc.replace(k, v)
    visible = re.sub(r"<!--.*?-->|<[^>]+>", " ", doc, flags=re.S)
    left = sorted(set(re.findall(r"\[[A-Z][^\]]*\]|\([a-z][\w ]*\)", visible)) |
                  set(re.findall(r'href="(\[[^\]]+\])"', doc)))
    return doc, left, missing


REMOTE = {}


def remote_data_uri(url):
    """Descarga una imagen de S3 una vez por corrida y la devuelve como data URI (None si no hay conexión)."""
    if url not in REMOTE:
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                REMOTE[url] = "data:image/png;base64," + base64.b64encode(r.read()).decode()
        except Exception:
            REMOTE[url] = None
            print(f"  ⚠ no se pudo descargar {url}: el preview usa la copia local")
    return REMOTE[url]


def embed_remote(m):
    tag = m.group(0)
    uri = remote_data_uri(re.search(r'src="([^"]+)"', tag).group(1))
    if not uri:
        return tag.replace(' data-remote="1"', "")  # sigue con data-svg: se reemplaza por la copia local
    return re.sub(r'\sdata-(?:svg|remote)="[^"]*"', "", re.sub(r'src="[^"]+"', f'src="{uri}"', tag, count=1))


def to_preview(doc, ctx):
    doc = re.sub(r'<img[^>]*data-remote="1"[^>]*>', embed_remote, doc)
    doc = re.sub(r'<img[^>]*data-svg="([^"]+)"[^>]*>', lambda m: svg_inline(m.group(1), m.group(0)), doc)
    for name, path in ctx.images.items():
        mime = "image/" + ("jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else path.suffix.lower().lstrip("."))
        data = base64.b64encode(path.read_bytes()).decode()
        doc = doc.replace("{ASSET}" + name, f"data:{mime};base64,{data}")
    return doc


# ---------------------------------------------------------------- entrega
def write_index(out, specs):
    tag = lambda s: (f'<small>({s.get("lang", "en")} · {s.get("entity", "ltd").upper()})</small>'
                     + (' <small style="color:#FFE8C2">· BORRADOR</small>' if s["_draft"] else ""))
    li = lambda folder, ext: "\n".join(f'<li><a href="{folder}/{s["_name"]}.{ext}">{html.escape(s["subject"])}</a> {tag(s)}</li>'
                                       for s in specs if folder != "produccion" or not s["_draft"])
    (out / "ABRIR-AQUI.html").write_text(f'''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Tradeview Markets · Correos</title></head>
<body style="margin:0;background:#272336;color:#fff;font-family:'Plus Jakarta Sans',Inter,Arial,sans-serif">
<main style="max-width:640px;margin:48px auto;padding:40px;background:#080B18">
<h1 style="font-size:26px;margin:0 0 8px">Correos transaccionales · Tradeview Markets</h1>
<p style="background:#FFE8C2;color:#6B3A00;padding:12px 16px;border-radius:16px;font-size:14px">Los logos y redes ya están en S3. Las demás imágenes de estos correos están en <b>produccion/subir-a-s3/</b>: hay que pedirle a desarrollo que las suba y registrar sus URLs; mientras tanto, en "Producción" se ven como <b>[S3:archivo]</b>. Para revisar el diseño usa Preview o PDF.</p>
<h2 style="font-size:17px;margin:32px 0 12px">Preview (archivo único, se ve en cualquier lugar)</h2><ul>{li("preview", "html")}</ul>
<h2 style="font-size:17px;margin:32px 0 12px">PDF (para aprobación)</h2><ul>{li("pdf", "pdf")}</ul>
<h2 style="font-size:17px;margin:32px 0 12px">Producción (para desarrollo)</h2><ul>{li("produccion", "html")}</ul>
</main></body></html>''', encoding="utf-8")
    (out / "LEEME.txt").write_text(f'''TRADEVIEW MARKETS - CORREOS TRANSACCIONALES

CARPETAS
- pdf/                    Para compartir y aprobar el diseño. Se abre en cualquier lugar.
- preview/                HTML de archivo único (imágenes incrustadas). Se ve en cualquier navegador.
                          NO sirve para enviar.
- produccion/             HTML finales para desarrollo: un solo archivo por correo, tablas, CSS inline,
                          imágenes desde S3 y variables Jinja {{{{ data['...'] }}}}.
- produccion/subir-a-s3/  Imágenes de estos correos que todavía no están en S3 (se le piden a desarrollo).
                          Los logos del header/footer y las redes ya están en S3 y no aparecen aquí.

NOMBRES DE ARCHIVO
<correo>-<idioma>-<entidad>.html  ·  ej. deposit-confirmed-es-sac.html

PARA DESARROLLO
1. Subir produccion/subir-a-s3/*.png a S3 y pasar la URL de cada una. Donde el HTML diga
   [S3:nombre-del-archivo.png] va esa URL (o se registra y se regeneran los correos).
2. Usar produccion/<correo>-<idioma>-<entidad>.html como plantilla. Las variables ya vienen en Jinja;
   si quedó alguna entre corchetes [ ], falta definir su key en el backend.
3. Probar en Gmail (web/app), Outlook y Apple Mail, a 390 y 750 px. El árabe se revisa en RTL.
''', encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--screenshots", action="store_true")
    a = ap.parse_args()

    out = Path(a.out)
    prod, prev, pdfd, s3 = out / "produccion", out / "preview", out / "pdf", out / "produccion" / "subir-a-s3"
    for d in (s3, prev):
        d.mkdir(parents=True, exist_ok=True)

    jobs = []
    for sp in a.specs:
        sp = Path(sp)
        base_spec = json.loads(sp.read_text())
        base_spec.setdefault("slug", sp.stem.split(".")[0])
        ents = base_spec.get("entity", "ltd")
        for ent in ents if isinstance(ents, list) else [ents]:  # "entity": ["ltd", "sac"] genera ambas
            jobs.append((sp, {**base_spec, "entity": ent}))

    specs = []
    for sp, spec in jobs:
        spec["_name"] = name = out_name(spec)
        print(f"• {name}")
        doc, ctx = render(spec, sp.parent)
        issues = spec["_draft"] = copy_status(spec)
        p_, left, missing = to_production(doc)
        if "<style" in p_ or re.search(r"display:\s*(inline-)?flex", p_):
            sys.exit("  ✖ El HTML de producción rompe el estándar de dev (<style> o flexbox).")
        preview = to_preview(doc, ctx)
        if issues:
            preview = preview.replace("</div>\n<table", "</div>\n" + draft_banner(issues) + "<table", 1)
            print(f"  ⚠ BORRADOR: falta aprobar {' y '.join(issues)} → no se genera producción")
        else:
            (prod / f"{name}.html").write_text(p_, encoding="utf-8")
        (prev / f"{name}.html").write_text(preview, encoding="utf-8")
        for f in missing:
            shutil.copy(PNG_DIR / f if (PNG_DIR / f).exists() else ctx.images[f], s3 / f)
        kb = len(p_.encode()) / 1024
        print(f"  produccion {kb:.1f} KB" + ("  ⚠ supera 100 KB (Gmail recorta)" if kb > 100 else ""))
        jinja = sorted(set(re.findall(r"\{\{ data\['(\w+)'\] \}\}", p_)))
        if jinja:
            print(f"  variables Jinja: {', '.join(jinja)}")
        if left:
            print(f"  ⚠ sin key de backend (pedir a dev y agregar en delivery.json): {', '.join(left)}")
        if missing:
            print(f"  ⚠ imágenes sin URL de S3 (pedir a desarrollo y registrar en delivery.json → images): {', '.join(missing)}")
        specs.append(spec)

    write_index(out, specs)

    if not a.no_pdf or a.screenshots:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("⚠ playwright no disponible: se omiten PDF/screenshots")
            return
        pdfd.mkdir(exist_ok=True)
        shots = out / "screenshots"
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            for s in specs:
                f = (prev / f"{s['_name']}.html").resolve()
                pg = br.new_page(viewport={"width": 850, "height": 800})
                pg.goto(f.as_uri()); pg.wait_for_timeout(600)
                if not a.no_pdf:
                    h = pg.evaluate("document.documentElement.scrollHeight")
                    pg.emulate_media(media="screen")
                    pg.pdf(path=str(pdfd / f"{s['_name']}.pdf"), width="850px", height=f"{h+2}px",
                           print_background=True, margin={k: "0" for k in ("top", "bottom", "left", "right")})
                if a.screenshots:
                    shots.mkdir(exist_ok=True)
                    for w in (750, 390):
                        pg.set_viewport_size({"width": w, "height": 800})
                        pg.screenshot(path=str(shots / f"{s['_name']}_{w}.png"), full_page=True)
                pg.close()
            br.close()
    print(f"Listo → {out}")


if __name__ == "__main__":
    main()
