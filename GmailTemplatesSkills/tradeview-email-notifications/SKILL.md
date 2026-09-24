---
name: tradeview-email-notifications
description: Crea correos transaccionales y de notificación de Tradeview Markets (Tradeview × EDGE) en HTML listo para el backend de Tradeview (tablas, CSS inline, imágenes en S3, variables Jinja), con su versión preview y PDF. Úsala siempre que el usuario pida un correo, email, notificación, plantilla de correo o "mail" de Tradeview — verificación de documentos (ID, proof of address), retiros, depósitos, cuentas nuevas, códigos OTP, credenciales de cuenta, avisos del Cabinet — en cualquier idioma (inglés, español, portugués, japonés, chino, coreano, árabe) y para Tradeview Ltd. o S.A.C., ya sea desde el diseño (maqueta/imagen o link de Figma) o desde la tarea (una descripción en el chat o un documento Word/PDF con la información del correo, p. ej. "correo de retiro rechazado", "email de documento vencido"). También cuando pida cambiar, corregir o agregar correos existentes de Tradeview, preparar la entrega a devs, o pregunte por qué no se ven las imágenes de un correo.
---

# Correos de notificación · Tradeview Markets

Genera correos que cumplen el design system de Tradeview (header negro con logo a color, body `#080B18`, footer negro con redes y legales, 750px fluido sobre fondo `#272336`) **y el estándar del equipo de desarrollo**: un solo HTML por correo, maquetado con tablas, CSS 100% inline (sin `<style>` ni flexbox), imágenes desde el bucket S3 y variables Jinja `{{ data['...'] }}`. La estructura y los estilos salen de la **base** (`base/`), y el trabajo pesado (idiomas, RTL, S3, Jinja, PDF) lo hace `scripts/build_email.py`; tu trabajo es traducir la maqueta o el pedido a un **spec JSON por idioma** correcto y entregar bien.

La fuente de verdad visual es el archivo de Figma **Emails** (`https://www.figma.com/design/yAI1PcA8Zkv9RFUua3RVz4/Emails?node-id=9178-473`), secciones New user / Live account, Active user y Footer — la sección Research no se usa. Si tienes acceso al MCP de Figma y el usuario comparte un nodo, léelo con `get_screenshot` / `get_design_context`; `references/design-rules.md` ya resume ese archivo.

## Lo fundamental — en TODOS los correos

1. **Idioma.** Cada correo se genera en los idiomas que pida el usuario (`en`, `es`, `pt`, `ja`, `zh`, `ko`, `ar`), con **un spec por idioma**. El árabe sale espejado (RTL). Los textos fijos (saludo, ayuda, footer) salen de `locales/<idioma>.json`; la traducción del cuerpo puede ser una adaptación, no literal. Si el usuario no dijo los idiomas, pregúntalo.
2. **Footer por entidad.** Cada correo lleva el footer legal de su entidad: `ltd` (Tradeview Ltd., Islas Caimán) o `sac` (Tradeview Financial Markets S.A.C., Perú), en el idioma del correo. Se pide con `"entity"` (`["ltd", "sac"]` genera las dos). **Nunca asumas la entidad**: si el usuario no la dijo, pregúntala.
3. **Imágenes.** Puedes usar cualquier icono o logo que ya exista en `assets/` (y agregar iconos nuevos de Google Fonts). En **preview y PDF** siempre se ven, con la copia local. En **producción** los logos y redes de la base ya tienen URL; el resto queda `[S3:archivo]` hasta que el usuario te pase la URL que dio desarrollo — la registras en `delivery.json` → `images` y regeneras. Nunca inventes URLs.

Antes de entregar, confirma en tu mensaje qué idiomas y qué entidades generaste.

## La base

Todos los correos se construyen sobre la misma base, en `base/`:
- `base/base.html` — **la estructura**: el esqueleto fijo (fondo, contenedor de 750px, header, body, footer) con marcadores `<!-- SLOT:... -->` donde entra el contenido y `@@...@@` donde entran los estilos.
- `base/tokens.json` — **los estilos**: colores, tipografías, medidas y espaciados, con el nombre de la variable de Figma cuando existe.
- `base/variants.json` — **las variantes** de header y footer. Hoy solo existe `standard` en ambos. Los logos del header y footer y los iconos de redes ya están en el S3 de Tradeview (`url`), con los tamaños de Figma; el correo los usa directo. El texto legal del footer no va aquí: sale de `locales/` según la entidad.

Cómo se cambia:
- **Cambio para todos los correos** (un color, el logo, el espaciado) → se edita la base. Después hay que regenerar los correos que ya se entregaron y volver a pasárselos a desarrollo: no se actualizan solos.
- **Cambio para algunos correos** (p. ej. un co-branding) → se agrega una variante en `base/variants.json` (+ sus imágenes en `assets/`) y el spec la elige con `"header"` / `"footer"`.
- **Nunca** se edita a mano el HTML de un correo ni se escriben estilos en el spec.

## Flujo

1. **Entender el correo.** El pedido llega de una de dos formas:
   - **A. Desde el diseño** — un nodo de Figma o una imagen de la maqueta. Léelo con atención: icono, título (y dónde corta la línea), párrafos exactos, card, CTA. El texto se copia **exacto**.
   - **B. Desde la tarea** — la información del correo en texto (en el chat) o en un documento (Word, PDF, Google Doc exportado, Excel…). Lee el documento completo y arma el correo con los bloques y el tono de `examples/` (directo, cordial). Si el documento trae el texto final, cópialo exacto; si solo trae la idea, redáctalo tú y márcalo `"copy": "draft"` (también en inglés) hasta que el usuario lo apruebe.

   En los dos casos, antes de escribir el spec extrae y confirma: **tipo de correo** (qué evento lo dispara), **asunto** y **preheader**, **título** y textos, **datos de la persona o la cuenta** que lleva (serán variables), **CTA** y a dónde va, **estilo** (estándar o `hero` si es transaccional de depósito/retiro/transferencia/formulario), **idiomas** y **entidades**. Las entidades las indica el usuario (`ltd`, `sac` o ambas); si no las dijo, pregúntalo — no asumas. Si falta algo más que cambia el resultado, haz una sola pregunta, lo más concreta posible, con todo lo que falte.
2. **Leer las reglas** cuando haya duda de diseño: `references/design-rules.md`. Si el proyecto tiene un `design-system.md`, léelo también.
3. **Escribir el spec** en `/home/claude/specs/<slug>[.<lang>].json` siguiendo `references/spec-format.md` — **un spec por idioma**, mismo `slug` y mismos bloques, cambiando solo `lang` y los textos. Las entidades van en `"entity"`: `"ltd"`, `"sac"` o `["ltd", "sac"]` para generar las dos desde el mismo spec. Parte de un ejemplo parecido en `examples/` en lugar de empezar de cero. Si traduces tú el copy, dilo en la entrega para que alguien del equipo lo revise.
4. **Construir:**
   ```bash
   cd <ruta-de-esta-skill>
   pip install cairosvg --break-system-packages -q   # solo si vas a regenerar assets (en macOS: playwright)
   python scripts/build_email.py /home/claude/specs/*.json --out /home/claude/tradeview-emails --screenshots
   ```
5. **Verificar visualmente** los screenshots a 750 y 390 px (`view`) contra la maqueta: textos, cortes de línea, espaciados, icono correcto; en árabe, que todo esté espejado. Corrige el spec y reconstruye si algo no coincide. Revisa los avisos del script: orden de bloques, CTAs distintos, peso y, sobre todo, **"sin key de backend"** (variables que dev todavía no definió).
6. **Entregar** (ver abajo).

## Entrega

Copia la carpeta de salida a `/mnt/user-data/outputs/tradeview-emails/` (sin `screenshots/`), crea un zip de ella y presenta con `present_files`, en este orden: los PDF, los HTML de `preview/`, y el zip. Estos correos son archivos para el backend: no los publiques como artifact.

En el mensaje, en español y sin jerga, explica brevemente:
- **PDF** → para compartir y aprobar; se abre en cualquier lado.
- **Preview** → el correo en el navegador, con las variables legibles; no sirve para enviar.
- **Producción** (dentro del zip) → lo que se pasa a desarrollo: `<correo>-<idioma>-<entidad>.html` con variables Jinja e imágenes en S3. Los logos y redes de la base ya tienen URL. Las demás imágenes del correo (iconos, botones…) que aún no tengan URL quedan como `[S3:archivo]` y están en `produccion/subir-a-s3/`: hay que **pedirle a desarrollo que las suba** y, cuando pasen las URLs, registrarlas en `delivery.json` → `images` y regenerar.
- **Qué idiomas y qué entidades** generaste (ej. "en, es y ar · LTD y SAC").
- Qué imágenes quedaron **sin URL de S3** (están en `produccion/subir-a-s3/`; hay que pedirlas a desarrollo).
- Qué variables quedaron **sin key de backend** (hay que pedírselas a dev).
- Cualquier diferencia entre la maqueta y el design system que hayas resuelto siguiendo la maqueta.
- Qué textos traduciste tú (y los de `locales/` marcados como propuesta) para que el equipo los revise.

Para dudas del tipo "no se ven las imágenes", "cómo lo mando", "qué hago con esto", "se lo paso a los devs" → `references/delivery-and-handoff.md` (estándar de dev completo y plantilla de nota de entrega).

## Reglas que no se negocian

- **Estándar de dev:** un solo archivo HTML, tablas, CSS 100% inline, **sin `<style>`, sin clases, sin flexbox**, imágenes por URL de S3. El script lo cumple y se detiene si algo lo rompe: nunca lo "arregles" a mano en el HTML.
- Estructura, colores y footer vienen de la **base** — no escribas HTML de correo a mano ni cambies la base por un correo puntual (para eso están las variantes). Si el usuario pide un cambio **global**, edita `base/` (no el script) y reconstruye todos los correos afectados.
- Un solo CTA por correo, color `#EB0052` — se puede repetir el **mismo** CTA en correos largos, nunca dos acciones distintas. Links en `#A898FB`; el email de soporte en `#D1E0FF`.
- **Todo el texto se inyecta**: el cuerpo va en el spec de cada idioma y los textos fijos en `locales/<lang>.json`. Los datos de la persona o la cuenta (nombre, montos, IDs, códigos, credenciales) siempre como variable (`[First Name]`, `[Amount]`…), nunca escritos. Las variables se escriben igual en todos los idiomas; en producción el script las pasa a Jinja con `delivery.json`.
- **Nada sin aprobar llega a desarrollo.** Los idiomas distintos al inglés arrancan como borrador (`"copy": "draft"` en el spec y `"status": "draft"` en `locales/`). Solo cambia a `approved` cuando el usuario confirme que alguien del equipo revisó ese texto; nunca lo apruebes tú. Las traducciones pueden ser adaptaciones, no literales: copia exacto el texto aprobado que te den.
- **No inventes URLs de imágenes.** Solo se usan las de `base/variants.json` (logos y redes) y las registradas en `delivery.json` → `images` con la URL que pasó desarrollo. Lo demás queda `[S3:archivo]`.
- **No inventes keys de backend.** Si una variable no está en `delivery.json` → `variables`, déjala así y pide a dev el nombre del campo.
- El footer legal sale de `locales/` según `lang` y `entity`. No lo edites a mano ni lo traduzcas: viene de Figma.
- El `hero` con degradado es solo para correos transaccionales (depósito, retiro, transferencia, formularios); nunca para notificaciones o confirmaciones simples.
- Icono de éxito en verde `#3ED47A`; todos los demás iconos de estado en lila `#A898FB`.
- Producción usa PNG @2x con `alt`, nunca SVG. Preview usa SVG incrustado. Ambos salen del script.
- El texto de la maqueta se copia exacto. No inventes variables ni datos legales.
- Si la maqueta contradice el design system, sigue la maqueta y avisa. No edites el `design-system.md` salvo que el usuario lo pida.
- Los iconos siempre salen de [Google Fonts Icons](https://fonts.google.com/icons) (Material Symbols), configurados en Weight 300 y estilo Rounded — nunca se dibujan a mano ni se buscan en otro banco de iconos.

## Agregar un icono de estado

1. Busca el icono en [Google Fonts Icons](https://fonts.google.com/icons) (Material Symbols, Weight 300, estilo Rounded) y descarga su SVG (o `https://fonts.gstatic.com/s/i/short-term/release/materialsymbolsrounded/<nombre>/wght300/24px.svg`). Guárdalo como `assets/svg/icon-<nombre>.svg` agregando `fill="#A898FB"` al `<svg>` (verde `#3ED47A` solo si significa éxito).
2. Copia la skill a un directorio escribible si está en solo lectura, y corre `python scripts/build_assets.py icon-<nombre>` para generar el PNG @2x.
3. Úsalo en el spec con `{"type":"icon","name":"<nombre>"}`. Avisa al usuario que el PNG nuevo también hay que subirlo a S3.

Excepción: los logos de marca (plataformas de descarga, TradeGATEHub, Up!, redes) no existen en Google Fonts; son los `brand-*.svg` y `social-*.svg` exportados de Figma.

Si el usuario entrega un logo nuevo: reemplaza el SVG en `assets/svg/` con el mismo nombre (`tradeview-color.svg`, `tradeview-white.svg`, `edge-white.svg`) y regenera. Antes de reemplazar, compara con el existente: si es idéntico, díselo al usuario en vez de "cambiarlo".

## Agregar un idioma

Copia `locales/en.json` a `locales/<código>.json` y traduce `footer_title`, `greeting`, `help`, `more_title`, `academy`, `insights`. El `legal` se copia **tal cual** de Figma → sección Footer (una versión por entidad). Si el idioma se escribe de derecha a izquierda, pon `"dir": "rtl"`. Agrega la fuente del alfabeto a `font` y `gfont`.

## Contenido de la skill

- `scripts/build_email.py` — spec JSON → produccion/ (+ subir-a-s3/) + preview/ + pdf/ + ABRIR-AQUI.html + LEEME.txt
- `scripts/build_assets.py` — regenera `assets/png/` desde `assets/svg/` (`python scripts/build_assets.py icon-x` para uno solo)
- `base/` — la base de todos los correos: `base.html` (estructura), `tokens.json` (estilos), `variants.json` (variantes de header y footer)
- `delivery.json` — integración con el backend: carpeta de S3 para los iconos, links reales, mapa de variables → Jinja
- `assets/svg/` — logos oficiales, iconos de estado (`icon-*`), iconos de interfaz (`ui-*`), logos de plataformas y productos (`brand-*`), redes (fuente)
- `assets/png/` — versiones @2x (las que se suben a S3)
- `locales/` — un JSON por idioma: fuente, dirección (RTL), textos fijos y footer legal por entidad (LTD / SAC)
- `examples/` — specs de los correos de Figma: verificación de documentos, OTP, cuenta lista (MT4), depósito (en/es/ar), retiros, formulario de +25k con hero
- `references/spec-format.md` — todos los tipos de bloque y cómo funcionan las variables
- `references/design-rules.md` — tokens, medidas y decisiones de diseño
- `references/delivery-and-handoff.md` — estándar de dev, entregables, problemas frecuentes, plantilla de handoff
