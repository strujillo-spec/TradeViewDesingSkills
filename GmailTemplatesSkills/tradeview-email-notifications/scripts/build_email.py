#!/usr/bin/env python3
"""Construye correos transaccionales de Tradeview Markets a partir de specs JSON.

Estándar del equipo de desarrollo: un solo archivo HTML por correo, maquetado con tablas, CSS 100% inline
(sin <style>, sin flexbox), imágenes por URL del bucket S3 y variables Jinja {{ data['...'] }}.

Por cada spec genera:
  produccion/<nombre>.html       -> lo que se entrega a dev (imágenes apuntando a S3, variables Jinja)
  produccion/subir-a-s3/*.png    -> imágenes que hay que subir al bucket (las sube Dani Peña)
  preview/<nombre>.html          -> archivo único con SVG incrustado, para ver y aprobar en cualquier navegador
  pdf/<nombre>.pdf               -> para compartir y aprobar diseño
Además: ABRIR-AQUI.html y LEEME.txt en la raíz de la carpeta de salida.

<nombre> = <slug>-<lang>-<entity>, ej. deposit-confirmed-es-sac.

Uso:
  python scripts/build_email.py spec1.json [spec2.json ...] --out salida
  Opciones: --no-pdf  --screenshots (PNG a 750 y 390 px)  --asset-base URL (reemplaza la de delivery.json)

Formato del spec: ver references/spec-format.md · Integración con backend: delivery.json
"""
import argparse, base64, datetime, html, json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG_DIR = ROOT / "assets" / "svg"
PNG_DIR = ROOT / "assets" / "png"
LOCALES = ROOT / "locales"
DELIVERY = json.loads((ROOT / "delivery.json").read_text())
YEAR = str(datetime.date.today().year)

W, PAD = 750, 50            # ancho del correo y padding lateral (Figma 1:1)
CW = W - 2 * PAD            # ancho de contenido: 650
ICONS = {p.stem[5:] for p in SVG_DIR.glob("icon-*.svg")}
PLATFORMS = {  # asset, ancho, alto, etiqueta por defecto
    "windows": ("brand-windows", 24, 24, "Windows"),
    "macos": ("brand-macos", 85, 20, "MacOS"),
    "ios": ("brand-appstore", 28, 28, "iPhone or iPad"),
    "android": ("brand-googleplay", 28, 28, "Android"),
    "web": ("brand-web", 24, 24, "Web version"),
}
PILLS = {"warning": ("#FFE8C2", "#6B3A00"), "success": ("#E6F5EA", "#075C24"), "error": ("#FFE5E5", "#8D0000")}
BODY_ORDER = ["hero", "icon", "title", "subtitle", "image", "greeting", "content", "cta"]
CONTENT = {"paragraph", "pill", "list_card", "details_card", "heading", "code", "alert", "note", "steps"}
TIGHT = {  # pares de bloques que van a 20px (mismo grupo en Figma); el resto va a 36px
    ("icon", "*"), ("title", "subtitle"), ("greeting", "*"), ("heading", "*"),
    ("paragraph", "paragraph"), ("paragraph", "pill"), ("paragraph", "list_card"), ("paragraph", "note"),
    ("pill", "paragraph"), ("pill", "pill"), ("details_card", "alert"), ("code", "alert"),
    ("note", "steps"), ("note", "note"),
}
G, g = 36, 20

# Se fijan por idioma en set_locale()
FONT = TXT = START = END = LANG = ""
LOC = {}


def set_locale(lang):
    global FONT, TXT, START, END, LOC, LANG
    path = LOCALES / f"{lang}.json"
    if not path.exists():
        sys.exit(f"Idioma '{lang}' sin locales/{lang}.json. Disponibles: {sorted(p.stem for p in LOCALES.glob('*.json'))}")
    LOC, LANG = json.loads(path.read_text()), lang
    FONT = LOC["font"]
    TXT = f"font-family:{FONT};color:#FFFFFF;"
    START, END = ("right", "left") if LOC["dir"] == "rtl" else ("left", "right")


class Ctx:
    """Recolecta los assets usados por un correo."""
    def __init__(self, spec_dir):
        self.spec_dir = spec_dir
        self.pngs = set()      # nombres de assets/png usados
        self.images = {}       # nombre destino -> ruta local de imágenes propias (banners)


def img(ctx, name, w, h, alt, style="", display="block", fluid=False):
    """<img> a {ASSET}<name>-2x.png. En preview se reemplaza por SVG inline. fluid: se encoge en pantallas angostas."""
    ctx.pngs.add(f"{name}-2x.png")
    size = f"width:100%;max-width:{w}px;" if fluid else f"width:{w}px;"
    return (f'<img src="{{ASSET}}{name}-2x.png" data-svg="{name}" width="{w}" height="{h}" alt="{html.escape(alt)}" '
            f'style="display:{display};border:0;outline:none;text-decoration:none;{size}height:auto;{style}">')


def links(text, color="#A898FB"):
    """Estilo inline para <a> que vengan sin style en el spec."""
    return re.sub(r"<a (?![^>]*style=)", f'<a style="color:{color};text-decoration:underline;" ', text)


def status_icon(ctx, name, alt, size=39, style=""):
    if name not in ICONS:
        sys.exit(f"Icono '{name}' no existe. Disponibles: {sorted(ICONS)}. "
                 f"Descárgalo de Google Fonts a assets/svg/icon-{name}.svg y corre build_assets.py")
    return img(ctx, "icon-" + name, size, size, alt, style=f"height:{size}px;" + style)


def p(text, size=14, lh=20, mb=g, weight=400, color="#A898FB"):
    return (f'    <p style="margin:0 0 {mb}px;{TXT}font-size:{size}px;line-height:{lh}px;font-weight:{weight};'
            f'text-align:{START};">{links(text, color)}</p>\n')


def table(inner, width="100%", style="", attrs=""):
    w = f'width="{width}" ' if width else ""
    return (f'<table role="presentation" {w}cellpadding="0" cellspacing="0" border="0" {attrs}'
            f'style="border-collapse:separate;{style}">{inner}</table>')


def outline_btn(ctx, label, href, icon=None, full=False):
    ic = (f'<td style="padding-{START}:4px;vertical-align:middle;">{img(ctx, icon, 16, 16, "", style="height:16px;")}</td>'
          if icon else "")
    inner = table(f'<tr><td style="font-family:{FONT};font-size:12px;line-height:17px;font-weight:700;color:#FFFFFF;'
                  f'white-space:nowrap;">{label}</td>{ic}</tr>', width="", style="margin:0 auto;")
    return table(f'<tr><td align="center" style="border:1px solid #FFFFFF;border-radius:100px;padding:8px 12px;">'
                 f'<a href="{href}" target="_blank" style="text-decoration:none;color:#FFFFFF;display:block;">{inner}</a></td></tr>',
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
    icon = (f'<td valign="middle" style="padding-{END}:16px;width:39px;">{status_icon(ctx, b["icon"], b.get("alt", ""))}</td>'
            if b.get("icon") else "")
    bg = ("background-color:#0F0631;background-image:radial-gradient(ellipse at 100% 100%,rgba(235,0,82,0.55) 0%,rgba(235,0,82,0) 60%),"
          "linear-gradient(100deg,#0F0631 37%,#9589E1 123%);")
    title = (f'<td valign="middle"><h1 style="margin:0;font-family:{FONT};font-size:35px;line-height:42px;font-weight:800;'
             f'color:#FFFFFF;text-align:{START};">{b["title"]}</h1></td>')
    return f'''  <!-- ===== HERO (degradado) ===== -->
  <tr><td bgcolor="#0F0631" height="222" valign="middle" style="{bg}height:222px;padding:0 {PAD}px;">
    {table(f"<tr>{icon}{title}</tr>", width="", attrs='align="center" ')}
  </td></tr>
'''


def b_icon(ctx, b, mb):
    return f'    <!-- Icono de estado -->\n    {status_icon(ctx, b["name"], b.get("alt", ""), style=f"margin:0 0 {mb}px;")}\n'


def b_title(ctx, b, mb):
    return (f'    <h1 style="margin:0 0 {mb}px;font-family:{FONT};font-size:28px;line-height:34px;'
            f'font-weight:800;color:#FFFFFF;text-align:{START};">{b["text"]}</h1>\n')


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
    return p(b["text"], size=18, lh=25, mb=mb, weight=600)


def b_pill(ctx, b, mb):
    bg, fg = PILLS[b.get("variant", "warning")]
    return (f'    <p style="margin:0 0 {mb}px;text-align:{START};"><span style="display:inline-block;background:{bg};color:{fg};'
            f'font-family:{FONT};font-size:14px;line-height:20px;padding:8px 12px;border-radius:100px;">{b["text"]}</span></p>\n')


def card(inner, mb, pad="24px 32px", bg="#272336", radius=20, extra=""):
    return "    " + table(f'\n      <tr><td bgcolor="{bg}" style="background:{bg};border-radius:{radius}px;padding:{pad};{extra}">\n'
                          f'{inner}      </td></tr>\n    ', style=f"margin:0 0 {mb}px;") + "\n"


def b_list_card(ctx, b, mb):
    items = b["items"]
    rows = ""
    cell = f"font-family:{FONT};font-size:14px;line-height:20px;color:#FFFFFF;text-align:{START};"
    for i, it in enumerate(items):
        pb = "0" if i == len(items) - 1 else "12px"
        rows += (f'          <tr><td valign="top" width="18" style="width:18px;padding:0 0 {pb};{cell}">&bull;</td>'
                 f'<td valign="top" style="padding:0 0 {pb};{cell}">{links(it)}</td></tr>\n')
    pad = "24px 40px 24px 32px" if START == "right" else "24px 32px 24px 40px"
    return "    <!-- Card de lista -->\n" + card(f"        {table(chr(10) + rows + '        ')}\n", mb, pad=pad)


def detail_rows(rows):
    out = ""
    cell = f"font-family:{FONT};font-size:14px;line-height:20px;color:#FFFFFF;"
    for i, row in enumerate(rows):
        k, v = row[0], row[1]
        pb = "0" if i == len(rows) - 1 else "20px"
        val = f"{v}&nbsp;&nbsp;{{COPY}}" if len(row) > 2 and row[2] == "copy" else v
        out += (f'          <tr><td valign="top" style="padding:0 0 {pb};padding-{END}:12px;{cell}text-align:{START};">{k}</td>'
                f'<td valign="top" align="{END}" style="padding:0 0 {pb};{cell}font-weight:600;text-align:{END};">{val}</td></tr>\n')
    return out


def copy_icon(ctx, doc):
    if "{COPY}" not in doc:
        return doc
    return doc.replace("{COPY}", img(ctx, "ui-copy", 20, 20, "", display="inline-block", style="height:20px;vertical-align:middle;"))


def b_details_card(ctx, b, mb):
    out = b_heading(ctx, {"text": b["title"]}, g) if b.get("title") else ""
    if b.get("sections"):
        inner = ""
        for j, s in enumerate(b["sections"]):
            if s.get("title"):
                inner += (f'        <p style="margin:{0 if j == 0 else 24}px 0 16px;{TXT}font-size:14px;line-height:20px;'
                          f'font-weight:600;text-align:{START};">{s["title"]}</p>\n')
            inner += f"        {table(chr(10) + detail_rows(s['rows']) + '        ')}\n"
    else:
        inner = f"        {table(chr(10) + detail_rows(b['rows']) + '        ')}\n"
    return out + "    <!-- Card de detalles -->\n" + copy_icon(ctx, card(inner, mb))


def b_code(ctx, b, mb):
    out = b_heading(ctx, {"text": b["label"]}, 16) if b.get("label") else ""
    inner = (f'        <p style="margin:0;{TXT}font-size:14px;line-height:20px;font-weight:600;letter-spacing:1px;'
             f'text-align:{START};">{b["code"]}&nbsp;&nbsp;{{COPY}}</p>\n')
    return out + "    <!-- Código de un solo uso -->\n" + copy_icon(ctx, card(inner, mb))


def b_alert(ctx, b, mb):
    inner = "        " + table(
        f'<tr><td valign="top" width="16" style="width:16px;padding-top:1px;padding-{END}:8px;">'
        f'{img(ctx, "ui-info", 16, 16, "", style="height:16px;")}</td>'
        f'<td valign="top" style="font-family:{FONT};font-size:12px;line-height:17px;color:#FFFFFF;text-align:{START};">'
        f'{links(b["text"])}</td></tr>') + "\n"
    return "    <!-- Aviso -->\n" + card(inner, mb, pad="16px", bg="#0F0631", radius=8, extra="border:1px solid #A898FB;")


def b_note(ctx, b, mb):
    ic = ""
    if b.get("icon"):
        asset, w, h = {"apple": ("brand-apple", 15, 18)}.get(b["icon"], ("icon-" + b["icon"], 18, 18))
        ic = f'<td valign="middle" style="padding-{END}:10px;">{img(ctx, asset, w, h, "", style=f"height:{h}px;")}</td>'
    inner = table(f'<tr>{ic}<td valign="middle" style="font-family:{FONT};font-size:14px;line-height:20px;color:#FFFFFF;'
                  f'text-align:{START};">{links(b["text"], "#EFF4FF")}</td></tr>', width="")
    return ("    <!-- Nota -->\n    " + table(f'<tr><td style="border:1px solid #A898FB;border-radius:8px;padding:12px;">{inner}</td></tr>',
                                             width="", style=f"margin:0 0 {mb}px;") + "\n")


def downloads(ctx, items):
    inner_w = CW - 48
    w = inner_w // len(items)
    cells = []
    for d in items:
        asset, aw, ah, label = PLATFORMS[d["platform"]]
        logo = img(ctx, asset, aw, ah, label, style=f"height:{ah}px;margin:0 auto;")
        btn = outline_btn(ctx, d.get("label", label), d.get("href", "#"), icon="ui-download")
        cells.append((w, table(f'<tr><td align="center" valign="bottom" height="28" style="height:28px;">{logo}</td></tr>'
                             f'<tr><td align="center" style="padding:12px 0 0;">{btn}</td></tr>', style="margin:0 auto;")))
    if len(cells) == 4:  # pares con 2 columnas fluidas: 1×4 en desktop, 2×2 en mobile
        half = inner_w // 2
        pair = lambda a, b: table(f'<tr><td width="50%" valign="bottom" style="width:50%;">{a[1]}</td>'
                                  f'<td width="50%" valign="bottom" style="width:50%;">{b[1]}</td></tr>')
        return columns([(half, pair(cells[0], cells[1])), (half, pair(cells[2], cells[3]))], inner_w, 16)
    return columns(cells, inner_w, 16)


def b_steps(ctx, b, mb):
    out = "    <!-- Pasos -->\n"
    items = b["items"]
    for i, s in enumerate(items, 1):
        head = "        " + table(
            f'<tr><td valign="middle" style="padding-{END}:16px;">{status_icon(ctx, s["icon"], "", size=36)}</td>'
            f'<td valign="middle" style="font-family:{FONT};font-size:18px;line-height:25px;font-weight:600;color:#FFFFFF;'
            f'text-align:{START};">{i}. {s["title"]}</td></tr>', width="") + "\n"
        body = (f'        <p style="margin:24px 0 0;{TXT}font-size:14px;line-height:20px;text-align:{START};">{links(s["text"])}</p>\n'
                if s.get("text") else "")
        dl = (f'        <div style="height:32px;line-height:32px;font-size:0;">&nbsp;</div>\n{downloads(ctx, s["downloads"])}'
              if s.get("downloads") else "")
        foot = (f'        <p style="margin:20px 0 0;{TXT}font-size:11px;line-height:15px;font-style:italic;text-align:{START};">'
                f'{s["footnote"]}</p>\n' if s.get("footnote") else "")
        out += card(head + body + dl + foot, mb if i == len(items) else g, pad="24px", bg="#0F0631", radius=12)
    return out


def b_cta(ctx, b, mb):
    label, href = b["label"], b.get("href", "[cabinet_url]")
    w = max(140, int(len(label) * 10 + 48))
    return f'''    <!-- CTA (bulletproof) -->
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-collapse:separate;margin:0 0 {mb}px;">
      <tr><td align="center" bgcolor="#EB0052" style="background:#EB0052;border-radius:100px;mso-padding-alt:16px 24px;">
        <!--[if mso]><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="{href}" style="height:56px;v-text-anchor:middle;width:{w}px;" arcsize="50%" stroke="f" fillcolor="#EB0052"><w:anchorlock/><center style="color:#FFFFFF;font-family:Arial,sans-serif;font-size:17px;font-weight:600;">{label}</center></v:roundrect><![endif]-->
        <!--[if !mso]><!--><a href="{href}" target="_blank" style="display:inline-block;padding:16px 24px;font-family:{FONT};font-size:17px;line-height:24px;font-weight:600;color:#FFFFFF;text-decoration:none;border-radius:100px;">{label}</a><!--<![endif]-->
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


# ---------------------------------------------------------------- plantilla
HEAD = '''<!DOCTYPE html>
<html lang="%(lang)s" dir="%(dir)s" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="x-apple-disable-message-reformatting">
<meta name="format-detection" content="telephone=no,address=no,email=no,date=no,url=no">
<meta name="color-scheme" content="dark">
<meta name="supported-color-schemes" content="dark">
<title>%(subject)s</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
<!--[if !mso]><!--><link href="https://fonts.googleapis.com/css2?family=%(gfont)s&display=swap" rel="stylesheet"><!--<![endif]-->
</head>
<body dir="%(dir)s" style="margin:0;padding:0;background:#272336;-webkit-text-size-adjust:100%%;-ms-text-size-adjust:100%%;">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">%(preheader)s&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;</div>
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" bgcolor="#272336" style="background:#272336;border-collapse:collapse;">
<tr><td align="center" valign="top" style="padding:50px 0;">
<!--[if mso]><table role="presentation" width="%(w)s" cellpadding="0" cellspacing="0" border="0" align="center"><tr><td><![endif]-->
<table role="presentation" dir="%(dir)s" width="%(w)s" cellpadding="0" cellspacing="0" border="0" style="width:100%%;max-width:%(w)spx;margin:0 auto;border-collapse:collapse;">

  <!-- ===== HEADER ===== -->
  <tr><td align="center" bgcolor="#000000" style="background:#000000;padding:14px 0;">
    %(logo)s
  </td></tr>

%(hero)s  <!-- ===== BODY ===== -->
  <tr><td bgcolor="#080B18" style="background:#080B18;padding:%(pad)spx;font-family:%(font)s;color:#FFFFFF;text-align:%(start)s;">
'''


def render_more(ctx, more):
    if not more:
        return ""
    more = more if isinstance(more, dict) else {}
    cw = (CW - 24) // 2
    specs = [("brand-tradegatehub", 32, 40, LOC["academy"], more.get("academy_url", "[academy_url]")),
             ("brand-up", 42, 32, LOC["insights"], more.get("blog_url", "[blog_url]"))]
    cells = []
    for asset, w, h, (title, text, btn), href in specs:
        head = table(f'<tr><td valign="middle" style="padding-{END}:16px;">{img(ctx, asset, w, h, title, style=f"height:{h}px;")}</td>'
                     f'<td valign="middle" style="font-family:{FONT};font-size:17px;line-height:24px;font-weight:600;color:#FFFFFF;'
                     f'text-align:{START};">{title}</td></tr>', width="")
        body = (f'<p style="margin:20px 0;{TXT}font-size:14px;line-height:20px;text-align:{START};">{text}</p>'
                f'{outline_btn(ctx, btn, href, full=True)}')
        cells.append((cw, table(f'<tr><td style="border:1px solid #3D326E;border-radius:12px;padding:24px;">{head}{body}</td></tr>')))
    return f'''
  <!-- ===== MORE FROM TRADEVIEW ===== -->
  <tr><td bgcolor="#0F0631" style="background:#0F0631;padding:24px {PAD}px;">
    <p style="margin:0 0 20px;{TXT}font-size:18px;line-height:25px;font-weight:600;text-align:{START};">{LOC["more_title"]}</p>
{columns(cells, CW, 24)}  </td></tr>
'''


def render_tail(ctx, entity, more, show_help=True):
    socials = DELIVERY["socials"]
    cells = ""
    for i, (n, alt, href) in enumerate(socials):
        pad = "" if i == len(socials) - 1 else f"padding-{END}:24px;"
        cells += (f'<td valign="middle" style="{pad}"><a href="{href}" target="_blank" style="text-decoration:none;">'
                  f'{img(ctx, "social-" + n, 48, 48, alt, fluid=True)}</a></td>')
    left = (f'<p style="margin:0 0 16px;{TXT}font-size:17px;line-height:24px;font-weight:600;text-align:{START};">{LOC["footer_title"]}</p>'
            + table(f"<tr>{cells}</tr>", width="408", style="width:100%;max-width:408px;"))
    right = table(f'<tr><td align="{END}" style="text-align:{END};padding-top:4px;">'
                  f'{img(ctx, "tradeview-white", 197, 31, "Tradeview Markets", display="inline-block")}'
                  f'<div style="height:21px;line-height:21px;font-size:0;">&nbsp;</div>'
                  f'{img(ctx, "edge-white", 125, 38, "EDGE Instant Liquidity Connector", display="inline-block")}</td></tr>')
    ldir = LOC.get("legal_dir", LOC["dir"])  # el legal en árabe viene en inglés en Figma
    L = f"font-family:{FONT};font-size:11px;line-height:15px;color:#FFFFFF;text-align:{'right' if ldir == 'rtl' else 'left'};"
    legal = LOC["legal"][entity]
    legal_html = "".join(f'    <p dir="{ldir}" style="margin:{"32px" if i == 0 else "0"} 0 {"0" if i == len(legal) - 1 else "15px"};{L}">{t}</p>\n'
                         for i, t in enumerate(legal))
    email = LOC["support_email"]
    help_ = p(LOC["help"].format(email=f'<a href="mailto:{email}">{email}</a>'), mb=G, color="#D1E0FF") if show_help else ""
    return f'''    <!-- Ayuda + firma -->
{help_}{p(LOC["signature"], mb=g, weight=600)}    <p style="margin:0;font-family:{FONT};font-size:14px;line-height:20px;text-align:{START};"><a href="https://www.tradeviewmarkets.com" target="_blank" style="color:#A898FB;text-decoration:underline;">www.tradeviewmarkets.com</a></p>
  </td></tr>
{render_more(ctx, more)}
  <!-- ===== FOOTER ({entity.upper()}) ===== -->
  <tr><td bgcolor="#000000" style="background:#000000;padding:56px {PAD}px;font-family:{FONT};color:#FFFFFF;">
{columns([(408, left), (197, right)], CW, 24)}{legal_html}  </td></tr>

</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr>
</table>
</body>
</html>
'''


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
    logo = img(ctx, "tradeview-color", 170, 29, "Tradeview Markets", style="margin:0 auto;")
    doc = HEAD % {"subject": html.escape(spec["subject"]), "preheader": html.escape(spec.get("preheader", "")),
                  "logo": logo, "font": FONT, "lang": lang, "dir": LOC["dir"], "gfont": LOC["gfont"],
                  "start": START, "hero": hero, "w": W, "pad": PAD}
    doc += render_body(ctx, body_blocks) + render_tail(ctx, entity, spec.get("more_from_tradeview"), spec.get("help", True))
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


def to_production(doc, base):
    """Imágenes a S3 y variables a Jinja. Devuelve (html, variables sin mapear)."""
    doc = re.sub(r'\sdata-svg="[^"]*"', "", doc).replace("{ASSET}", base)
    for k, v in DELIVERY["variables"].items():
        doc = doc.replace(k, v)
    visible = re.sub(r"<!--.*?-->|<[^>]+>", " ", doc, flags=re.S)
    left = sorted(set(re.findall(r"\[[A-Z][^\]]*\]|\([a-z][\w ]*\)", visible)) |
                  set(re.findall(r'href="(\[[^\]]+\])"', doc)))
    return doc, left


def to_preview(doc, ctx):
    doc = re.sub(r'<img[^>]*data-svg="([^"]+)"[^>]*>', lambda m: svg_inline(m.group(1), m.group(0)), doc)
    for name, path in ctx.images.items():
        mime = "image/" + ("jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else path.suffix.lower().lstrip("."))
        data = base64.b64encode(path.read_bytes()).decode()
        doc = doc.replace("{ASSET}" + name, f"data:{mime};base64,{data}")
    return doc


# ---------------------------------------------------------------- entrega
def write_index(out, specs, base):
    tag = lambda s: (f'<small>({s.get("lang", "en")} · {s.get("entity", "ltd").upper()})</small>'
                     + (' <small style="color:#FFE8C2">· BORRADOR</small>' if s["_draft"] else ""))
    li = lambda folder, ext: "\n".join(f'<li><a href="{folder}/{s["_name"]}.{ext}">{html.escape(s["subject"])}</a> {tag(s)}</li>'
                                       for s in specs if folder != "produccion" or not s["_draft"])
    (out / "ABRIR-AQUI.html").write_text(f'''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Tradeview Markets · Correos</title></head>
<body style="margin:0;background:#272336;color:#fff;font-family:'Plus Jakarta Sans',Inter,Arial,sans-serif">
<main style="max-width:640px;margin:48px auto;padding:40px;background:#080B18">
<h1 style="font-size:26px;margin:0 0 8px">Correos transaccionales · Tradeview Markets</h1>
<p style="background:#FFE8C2;color:#6B3A00;padding:12px 16px;border-radius:16px;font-size:14px">Los HTML de "Producción" cargan las imágenes desde S3 ({base}). Hasta que Dani Peña suba la carpeta <b>produccion/subir-a-s3/</b>, se verán sin imágenes: para revisar usa Preview o PDF.</p>
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
- produccion/subir-a-s3/  Imágenes que Dani Peña tiene que subir a:
                          {base}

NOMBRES DE ARCHIVO
<correo>-<idioma>-<entidad>.html  ·  ej. deposit-confirmed-es-sac.html

PARA DESARROLLO
1. Subir produccion/subir-a-s3/*.png a la carpeta de S3 indicada (mismos nombres).
2. Usar produccion/<correo>-<idioma>-<entidad>.html como plantilla. Las variables ya vienen en Jinja;
   si quedó alguna entre corchetes [ ], falta definir su key en el backend.
3. Probar en Gmail (web/app), Outlook y Apple Mail, a 390 y 750 px. El árabe se revisa en RTL.
''', encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--asset-base", default=DELIVERY["asset_base"], help="URL base de imágenes en producción")
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--screenshots", action="store_true")
    a = ap.parse_args()

    out = Path(a.out)
    prod, prev, pdfd, s3 = out / "produccion", out / "preview", out / "pdf", out / "produccion" / "subir-a-s3"
    for d in (s3, prev):
        d.mkdir(parents=True, exist_ok=True)
    base = a.asset_base if a.asset_base.endswith("/") else a.asset_base + "/"

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
        p_, left = to_production(doc, base)
        if "<style" in p_ or re.search(r"display:\s*(inline-)?flex", p_):
            sys.exit("  ✖ El HTML de producción rompe el estándar de dev (<style> o flexbox).")
        preview = to_preview(doc, ctx)
        if issues:
            preview = preview.replace("</div>\n<table", "</div>\n" + draft_banner(issues) + "<table", 1)
            print(f"  ⚠ BORRADOR: falta aprobar {' y '.join(issues)} → no se genera producción")
        else:
            (prod / f"{name}.html").write_text(p_, encoding="utf-8")
        (prev / f"{name}.html").write_text(preview, encoding="utf-8")
        for f in ctx.pngs:
            shutil.copy(PNG_DIR / f, s3 / f)
        for iname, path in ctx.images.items():
            shutil.copy(path, s3 / iname)
        kb = len(p_.encode()) / 1024
        print(f"  produccion {kb:.1f} KB" + ("  ⚠ supera 100 KB (Gmail recorta)" if kb > 100 else ""))
        jinja = sorted(set(re.findall(r"\{\{ data\['(\w+)'\] \}\}", p_)))
        if jinja:
            print(f"  variables Jinja: {', '.join(jinja)}")
        if left:
            print(f"  ⚠ sin key de backend (pedir a dev y agregar en delivery.json): {', '.join(left)}")
        specs.append(spec)

    write_index(out, specs, base)

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
