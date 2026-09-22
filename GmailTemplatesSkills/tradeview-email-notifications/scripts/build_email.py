#!/usr/bin/env python3
"""Construye correos transaccionales de Tradeview Markets a partir de specs JSON.

Por cada spec genera tres entregables:
  produccion/<slug>.html  + produccion/assets/*.png   -> lo que se entrega a los devs / ESP
  preview/<slug>.html     (SVG incrustado, archivo único) -> para ver y aprobar en cualquier navegador
  pdf/<slug>.pdf          -> para compartir por chat/correo y aprobar diseño
Además: ABRIR-AQUI.html y LEEME.txt en la raíz de la carpeta de salida.

Uso:
  python scripts/build_email.py spec1.json [spec2.json ...] --out /home/claude/salida
  python scripts/build_email.py specs/*.json --out salida --asset-base https://cdn.tradeviewmarkets.com/email/
  Opciones: --no-pdf  --screenshots (PNG a 600 y 390 px para revisar)

Formato del spec: ver references/spec-format.md
"""
import argparse, base64, html, json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG_DIR = ROOT / "assets" / "svg"
PNG_DIR = ROOT / "assets" / "png"

FONT = "'Plus Jakarta Sans','Inter',Arial,Helvetica,sans-serif"
TXT = f"font-family:{FONT};color:#FFFFFF;"
ICONS = {p.stem[5:] for p in SVG_DIR.glob("icon-*.svg")}
SOCIALS = [("linkedin", "LinkedIn", "https://www.linkedin.com/company/tradeview-markets"),
           ("instagram", "Instagram", "#"), ("youtube", "YouTube", "#"),
           ("tiktok", "TikTok", "#"), ("facebook", "Facebook", "#"), ("x", "X", "#")]
BODY_ORDER = ["icon", "title", "subtitle", "image", "greeting", "content", "cta"]
CONTENT = {"paragraph", "pill", "list_card", "details_card", "heading"}


class Ctx:
    """Recolecta los assets usados por un correo."""
    def __init__(self, spec_dir):
        self.spec_dir = spec_dir
        self.pngs = set()      # nombres de assets/png usados
        self.images = {}       # nombre destino -> ruta local de imágenes propias (banners)


def img(ctx, name, w, h, alt, cls="", style="", display="block"):
    """<img> apuntando a assets/<name>@2x.png. En preview se reemplaza por SVG inline."""
    ctx.pngs.add(f"{name}@2x.png")
    c = f' class="{cls}"' if cls else ""
    return (f'<img{c} src="{{ASSET}}{name}@2x.png" data-svg="{name}" width="{w}" height="{h}" alt="{html.escape(alt)}" '
            f'style="display:{display};border:0;width:{w}px;height:auto;{style}">')


# ---------------------------------------------------------------- bloques del body
def b_icon(ctx, b):
    name = b["name"]
    if name not in ICONS:
        sys.exit(f"Icono '{name}' no existe. Disponibles: {sorted(ICONS)}. "
                 f"Crea assets/svg/icon-{name}.svg y corre build_assets.py")
    return f'    <!-- Icono de estado -->\n    {img(ctx, "icon-"+name, 36, 36, b.get("alt", ""), style="height:36px;margin:0 0 16px;")}\n'


def b_title(ctx, b):
    return (f'    <h1 class="h1" style="margin:0 0 16px;font-family:{FONT};font-size:30px;line-height:38px;'
            f'font-weight:700;color:#FFFFFF;">{b["text"]}</h1>\n')


def b_subtitle(ctx, b):
    return f'    <p style="margin:-12px 0 16px;{TXT}font-size:15px;line-height:21px;">{b["text"]}</p>\n'


def b_image(ctx, b):
    src = b["src"]
    if not re.match(r"https?://", src):
        local = (ctx.spec_dir / src).resolve()
        if not local.exists():
            sys.exit(f"Imagen no encontrada: {local}")
        ctx.images[local.name] = local
        src = "{ASSET}" + local.name
    return (f'    <img src="{src}" width="520" alt="{html.escape(b.get("alt", ""))}" '
            f'style="display:block;border:0;width:100%;max-width:520px;height:auto;margin:16px 0 32px;">\n')


def b_greeting(ctx, b):
    return f'    <p style="margin:0 0 20px;{TXT}font-size:15px;line-height:23px;">{b.get("text", "Hi [First Name],")}</p>\n'


def b_paragraph(ctx, b, mb):
    return f'    <p style="margin:0 0 {mb}px;{TXT}font-size:15px;line-height:23px;">{b["text"]}</p>\n'


def b_heading(ctx, b):
    return f'    <p style="margin:0 0 16px;{TXT}font-size:17px;line-height:24px;font-weight:600;">{b["text"]}</p>\n'


def b_pill(ctx, b):
    return (f'    <p style="margin:0 0 20px;"><span style="display:inline-block;background:#FFE8C2;color:#6B3A00;'
            f'font-family:{FONT};font-size:15px;line-height:22px;padding:6px 12px;border-radius:16px;">{b["text"]}</span></p>\n')


def b_list_card(ctx, b):
    items = b["items"]
    rows = ""
    for i, it in enumerate(items):
        pb = "0" if i == len(items) - 1 else "12px"
        cell = f"font-family:{FONT};font-size:15px;line-height:22px;color:#FFFFFF;"
        rows += (f'          <tr><td valign="top" width="18" style="width:18px;padding:0 0 {pb};{cell}">&bull;</td>'
                 f'<td valign="top" style="padding:0 0 {pb};{cell}">{it}</td></tr>\n')
    return f'''    <!-- Card de lista -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:12px 0 32px;">
      <tr><td class="card" bgcolor="#272336" style="background:#272336;border-radius:20px;padding:24px 32px 24px 40px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
{rows}        </table>
      </td></tr>
    </table>
'''


def b_details_card(ctx, b):
    out = ""
    if b.get("title"):
        out += b_heading(ctx, {"text": b["title"]})
    rows = ""
    n = len(b["rows"])
    for i, (k, v) in enumerate(b["rows"]):
        pb = "0" if i == n - 1 else "24px"
        long_ = len(re.sub(r"<[^>]+>", "", v)) > 22 or "@" in v or "email" in k.lower()
        cls = ' class="stack"' if long_ else ""
        cell = f"font-family:{FONT};font-size:15px;line-height:22px;color:#FFFFFF;"
        kpb = "4px" if long_ else pb  # apilado en mobile: etiqueta pegada a su valor
        rows += (f'          <tr><td{cls} valign="top" style="padding:0 12px {kpb} 0;{cell}">{k}</td>'
                 f'<td{cls} valign="top" align="right" style="padding:0 0 {pb};{cell}font-weight:700;text-align:right;">{v}</td></tr>\n')
    out += f'''    <!-- Card de detalles -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 32px;">
      <tr><td class="card" bgcolor="#272336" style="background:#272336;border-radius:20px;padding:24px 32px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
{rows}        </table>
      </td></tr>
    </table>
'''
    return out


def b_cta(ctx, b):
    label, href = b["label"], b.get("href", "[cabinet_url]")
    w = max(140, int(len(label) * 10 + 48))
    return f'''    <!-- CTA (bulletproof) -->
    <table role="presentation" class="btn" cellpadding="0" cellspacing="0" border="0" style="margin:12px 0 32px;">
      <tr><td align="center" bgcolor="#EB0052" style="background:#EB0052;border-radius:999px;mso-padding-alt:18px 24px;">
        <!--[if mso]><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="{href}" style="height:56px;v-text-anchor:middle;width:{w}px;" arcsize="50%" stroke="f" fillcolor="#EB0052"><w:anchorlock/><center style="color:#FFFFFF;font-family:Arial,sans-serif;font-size:18px;font-weight:500;">{label}</center></v:roundrect><![endif]-->
        <!--[if !mso]><!--><a href="{href}" target="_blank" style="display:inline-block;padding:18px 24px;font-family:{FONT};font-size:18px;line-height:20px;font-weight:500;color:#FFFFFF;text-decoration:none;border-radius:999px;">{label}</a><!--<![endif]-->
      </td></tr>
    </table>
'''


def render_body(ctx, blocks):
    stage = lambda t: "content" if t in CONTENT else t
    # validaciones de orden y CTA único
    idx = [BODY_ORDER.index(stage(b["type"])) for b in blocks]
    if idx != sorted(idx):
        print(f"  ⚠ Orden de bloques fuera del estándar (icono → título → subtítulo → imagen → saludo → contenido → CTA): "
              f"{[b['type'] for b in blocks]}")
    if sum(b["type"] == "cta" for b in blocks) > 1:
        print("  ⚠ Más de un CTA: el design system permite uno solo por correo.")
    out = ""
    for i, b in enumerate(blocks):
        t = b["type"]
        nxt = blocks[i + 1]["type"] if i + 1 < len(blocks) else None
        if t == "paragraph":
            mb = b.get("margin_bottom")
            if mb is None:
                mb = 0 if nxt == "list_card" else (32 if nxt is None else 20)
            out += b_paragraph(ctx, b, mb)
        else:
            fn = globals().get("b_" + t)
            if not fn:
                sys.exit(f"Tipo de bloque desconocido: {t}")
            out += fn(ctx, b)
    return out


# ---------------------------------------------------------------- plantilla
HEAD = '''<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="x-apple-disable-message-reformatting">
<meta name="format-detection" content="telephone=no,address=no,email=no,date=no,url=no">
<meta name="color-scheme" content="dark">
<meta name="supported-color-schemes" content="dark">
<title>%(subject)s</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
<!--[if !mso]><!--><link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet"><!--<![endif]-->
<style>
  :root { color-scheme: dark; supported-color-schemes: dark; }
  body { margin:0 !important; padding:0 !important; background:#272336; -webkit-text-size-adjust:100%%; -ms-text-size-adjust:100%%; }
  table, td { mso-table-lspace:0pt; mso-table-rspace:0pt; border-collapse:collapse; }
  img { -ms-interpolation-mode:bicubic; border:0; outline:none; text-decoration:none; }
  a { color:#A898FB; }
  a[x-apple-data-detectors] { color:inherit !important; text-decoration:none !important; }
  @media (max-width:480px) {
    .outer { padding:0 !important; }
    .container { width:100%% !important; max-width:100%% !important; }
    .px { padding-left:20px !important; padding-right:20px !important; }
    .py { padding-top:32px !important; padding-bottom:32px !important; }
    .footer { padding:24px 20px !important; }
    .h1 { font-size:24px !important; line-height:30px !important; }
    .hide-mobile { display:none !important; }
    .btn { width:100%% !important; }
    .btn a { display:block !important; width:auto !important; text-align:center !important; font-size:17px !important; }
    .stack { display:block !important; width:100%% !important; text-align:left !important; padding-right:0 !important; }
    .stack-gap { padding-top:24px !important; }
    .logo-header { width:140px !important; height:auto !important; }
    .social { width:40px !important; height:40px !important; }
    .social-gap { padding-right:12px !important; }
    .logo-tv { width:160px !important; height:auto !important; }
    .logo-edge { width:100px !important; height:auto !important; }
    .card { padding:20px !important; }
  }
</style>
</head>
<body id="body" style="margin:0;padding:0;background:#272336;">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">%(preheader)s&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;</div>
<!-- Contenedor exterior #272336 (ocupa todo el correo) -->
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" bgcolor="#272336" style="background:#272336;">
<tr><td class="outer" align="center" valign="top" style="padding:40px 0;">
<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center"><tr><td><![endif]-->
<table role="presentation" class="container" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;margin:0 auto;">

  <!-- ===== HEADER ===== -->
  <tr><td align="center" bgcolor="#000000" style="background:#000000;padding:14px 0;">
    %(logo)s
  </td></tr>

  <!-- ===== BODY ===== -->
  <tr><td class="px py" bgcolor="#080B18" style="background:#080B18;padding:48px 40px;font-family:%(font)s;color:#FFFFFF;">
'''


def render_tail(ctx):
    cells = ""
    for i, (n, alt, href) in enumerate(SOCIALS):
        last = i == len(SOCIALS) - 1
        cls = "" if last else ' class="social-gap"'
        pad = "" if last else "padding-right:12px;"
        cells += (f'              <td{cls} style="{pad}"><a href="{href}" target="_blank" style="text-decoration:none;">'
                  f'{img(ctx, "social-"+n, 44, 44, alt, cls="social", style="height:44px;")}</a></td>\n')
    L = f"font-family:{FONT};font-size:11px;line-height:16px;color:#FFFFFF;"
    return f'''    <!-- Ayuda + firma -->
    <p style="margin:0 0 32px;{TXT}font-size:15px;line-height:23px;"><strong>Need help?</strong> Contact us at <a href="mailto:support@tradeviewmarkets.com" style="color:#A898FB;text-decoration:underline;">support@tradeviewmarkets.com</a>.</p>
    <p style="margin:0 0 12px;{TXT}font-size:15px;line-height:21px;font-weight:600;">Tradeview Markets</p>
    <p style="margin:0;font-family:{FONT};font-size:15px;line-height:21px;"><a href="https://www.tradeviewmarkets.com" target="_blank" style="color:#A898FB;text-decoration:underline;">www.tradeviewmarkets.com</a></p>
  </td></tr>

  <!-- ===== FOOTER ===== -->
  <tr><td class="footer" bgcolor="#000000" style="background:#000000;padding:40px;font-family:{FONT};color:#FFFFFF;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td class="stack" valign="bottom" width="340" style="width:340px;">
          <p style="margin:0 0 12px;{TXT}font-size:18px;line-height:23px;font-weight:500;">Contact Us</p>
          <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
{cells}          </tr></table>
        </td>
        <td class="stack stack-gap" align="right" valign="top" style="text-align:right;">
          {img(ctx, "tradeview-white", 170, 27, "Tradeview Markets", cls="logo-tv", style="max-width:100%;", display="inline-block")}
          <div style="height:20px;line-height:20px;font-size:0;">&nbsp;</div>
          {img(ctx, "edge-white", 108, 33, "EDGE Instant Liquidity Connector", cls="logo-edge", display="inline-block")}
        </td>
      </tr>
    </table>
    <p style="margin:32px 0 16px;{L}">There is a risk of loss in trading foreign currencies and it is not suitable for everyone. We are compensated for our services through the bid-ask spread. Copyright&copy; {{{{year}}}}. All rights reserved.</p>
    <p style="margin:0 0 16px;{L}">The services and products offered by Tradeview Ltd. are not being offered within the United States (US) and not being offered to US Persons, as defined under US law. The information on this website is not directed to residents of any country where FX and/or CFDs trading is restricted or prohibited by local laws or regulations. Tradeview Ltd. is a fully licensed Broker/Dealer under the regulations of the Cayman Island Monetary Authority (CIMA) License #585163. By keeping the navigation, you agree to the terms and conditions.</p>
    <p style="margin:0;{L}">Tradeview Ltd. located in Grand Cayman, KY1&ndash;1002;<br>4th Floor Harbour Place, 103 South Church St, PO Box 1105<br>Main Office : +1 345 945 6271<br>Direct Phone: +1 345 946 4532</p>
  </td></tr>

</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr>
</table>
</body>
</html>
'''


def render(spec, spec_dir):
    ctx = Ctx(spec_dir)
    logo = img(ctx, "tradeview-color", 170, 29, "Tradeview Markets", cls="logo-header")
    doc = HEAD % {"subject": html.escape(spec["subject"]), "preheader": html.escape(spec.get("preheader", "")),
                  "logo": logo, "font": FONT}
    doc += render_body(ctx, spec["blocks"]) + render_tail(ctx)
    return doc, ctx


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
    cls = f' class="{get("class")}"' if get("class") else ""
    return svg.replace("<svg", f'<svg{cls} width="{get("width")}" height="{get("height")}" role="img" '
                               f'aria-label="{get("alt")}" style="{get("style")}"', 1)


def to_production(doc, base):
    doc = re.sub(r'\sdata-svg="[^"]*"', "", doc)
    return doc.replace("{ASSET}", base)


def to_preview(doc, ctx):
    doc = re.sub(r'<img[^>]*data-svg="([^"]+)"[^>]*>', lambda m: svg_inline(m.group(1), m.group(0)), doc)
    for name, path in ctx.images.items():
        mime = "image/" + ("jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else path.suffix.lower().lstrip("."))
        data = base64.b64encode(path.read_bytes()).decode()
        doc = doc.replace("{ASSET}" + name, f"data:{mime};base64,{data}")
    return doc


# ---------------------------------------------------------------- entrega
def write_index(out, specs):
    li = lambda folder: "\n".join(f'<li><a href="{folder}/{s["slug"]}.html">{html.escape(s["subject"])}</a></li>' for s in specs)
    pdfs = "\n".join(f'<li><a href="pdf/{s["slug"]}.pdf">{html.escape(s["subject"])}</a></li>' for s in specs)
    (out / "ABRIR-AQUI.html").write_text(f'''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Tradeview Markets · Correos</title>
<style>body{{margin:0;background:#272336;color:#fff;font-family:'Plus Jakarta Sans',Inter,Arial,sans-serif}}
main{{max-width:640px;margin:48px auto;padding:40px;background:#080B18}}h1{{font-size:26px;margin:0 0 8px}}
p{{color:#D9D9DE;line-height:1.55;font-size:15px}}h2{{font-size:17px;margin:32px 0 12px}}a{{color:#A898FB}}
li{{margin:0 0 10px;font-size:15px}}.warn{{background:#FFE8C2;color:#6B3A00;padding:12px 16px;border-radius:16px;font-size:14px}}</style>
</head><body><main><h1>Correos transaccionales · Tradeview Markets</h1>
<p class="warn">Si los logos de "Producción" no aparecen, descomprime el zip completo (clic derecho → "Extraer todo") y abre este archivo desde la carpeta extraída. La versión Preview y los PDF se ven siempre.</p>
<h2>Preview (archivo único, se ve en cualquier lugar)</h2><ul>{li("preview")}</ul>
<h2>PDF (para aprobación)</h2><ul>{pdfs}</ul>
<h2>Producción (HTML final + assets/ para los devs)</h2><ul>{li("produccion")}</ul>
</main></body></html>''')
    (out / "LEEME.txt").write_text('''TRADEVIEW MARKETS - CORREOS TRANSACCIONALES

CARPETAS
- pdf/         Para compartir y aprobar el diseño. Se abre en cualquier lugar.
- preview/     HTML de archivo único (logos incrustados en SVG). Se ve en cualquier navegador,
               aunque se descargue suelto. NO sirve para enviar (Gmail/Outlook no muestran SVG).
- produccion/  HTML finales + assets/ (PNG @2x). Es lo que se entrega a los devs.

CÓMO VER LOS DE PRODUCCIÓN
No los abras desde dentro del zip. Windows: clic derecho -> "Extraer todo". Mac: doble clic.
No muevas los HTML fuera de su carpeta ni borres assets/.

PARA ENVIARLOS COMO CORREO REAL (devs)
1. Subir produccion/assets/*.png a un servidor público (CDN, S3 o galería del ESP).
2. Reemplazar src="assets/ por la URL pública en los HTML.
3. Adaptar variables ([First Name], [cabinet_url], {{year}}...) a la sintaxis del ESP.
4. Crear la plantilla en el ESP y conectarla al evento que dispara el correo.
5. Probar en Gmail (web/app), Outlook y Apple Mail, a 390, 480 y 600 px.
''', encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--asset-base", default="assets/", help="URL base de imágenes en producción (default: assets/)")
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--screenshots", action="store_true")
    a = ap.parse_args()

    out = Path(a.out)
    prod, prev, pdfd = out / "produccion", out / "preview", out / "pdf"
    for d in (prod / "assets", prev):
        d.mkdir(parents=True, exist_ok=True)
    base = a.asset_base if a.asset_base.endswith("/") else a.asset_base + "/"

    specs = []
    for sp in a.specs:
        sp = Path(sp)
        spec = json.loads(sp.read_text())
        spec.setdefault("slug", sp.stem)
        print(f"• {spec['slug']}")
        doc, ctx = render(spec, sp.parent)
        p = to_production(doc, base)
        (prod / f"{spec['slug']}.html").write_text(p)
        (prev / f"{spec['slug']}.html").write_text(to_preview(doc, ctx))
        for f in ctx.pngs:
            shutil.copy(PNG_DIR / f, prod / "assets" / f)
        for name, path in ctx.images.items():
            shutil.copy(path, prod / "assets" / name)
        kb = len(p.encode()) / 1024
        print(f"  produccion {kb:.1f} KB" + ("  ⚠ supera 100 KB (Gmail recorta)" if kb > 100 else ""))
        visible = re.sub(r"<!--.*?-->|<style.*?</style>|<[^>]+>", " ", p, flags=re.S)
        left = sorted(set(re.findall(r"\[[A-Z][^\]]*\]|\([a-z][\w ]*\)|\{\{\w+\}\}", visible)))
        left += sorted(set(re.findall(r'href="(\[[^\]]+\])"', p)) - set(left))
        if left:
            print(f"  variables a reemplazar en el ESP: {', '.join(left)}")
        specs.append(spec)
    if base != "assets/":
        shutil.rmtree(prod / "assets")  # imágenes ya viven en el CDN

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
                f = (prev / f"{s['slug']}.html").resolve()
                pg = br.new_page(viewport={"width": 700, "height": 800})
                pg.goto(f.as_uri()); pg.wait_for_timeout(400)
                if not a.no_pdf:
                    h = pg.evaluate("document.documentElement.scrollHeight")
                    pg.emulate_media(media="screen")
                    pg.pdf(path=str(pdfd / f"{s['slug']}.pdf"), width="700px", height=f"{h+2}px",
                           print_background=True, margin={k: "0" for k in ("top", "bottom", "left", "right")})
                if a.screenshots:
                    shots.mkdir(exist_ok=True)
                    for w in (600, 390):
                        pg.set_viewport_size({"width": w, "height": 800})
                        pg.screenshot(path=str(shots / f"{s['slug']}_{w}.png"), full_page=True)
                pg.close()
            br.close()
    print(f"Listo → {out}")


if __name__ == "__main__":
    main()
