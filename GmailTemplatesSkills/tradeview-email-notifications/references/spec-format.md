# Formato del spec JSON

Cada correo se describe con un JSON **por idioma**. `build_email.py` se encarga del header, contenedor,
bloque de ayuda/firma, More from Tradeview y footer — el spec solo describe el **Body**.

```json
{
  "slug": "proof-of-address-rejected",
  "lang": "es",
  "entity": "ltd",
  "subject": "Tu comprobante de domicilio fue rechazado",
  "preheader": "Sube un nuevo comprobante que cumpla los requisitos.",
  "blocks": [ ... ]
}
```

- `slug` (opcional): nombre base del archivo, en kebab-case e **inglés**, igual en todos los idiomas.
  Si falta, se usa el nombre del JSON (sin el `.es`/`.ar`…). Salida, con la convención de dev:
  `<slug>-<lang>-<entity>.html`, ej. `deposit-confirmed-es-sac.html`.
- `lang` (opcional, default `en`): `en` · `es` · `pt` · `ja` · `zh` · `ko` · `ar`. Tiene que existir
  `locales/<lang>.json`. `ar` se construye en RTL.
- `entity` (opcional, default `ltd`): `"ltd"` (Tradeview Ltd.), `"sac"` (Tradeview Financial Markets S.A.C.)
  o `["ltd", "sac"]` para generar un archivo por entidad desde el mismo spec. Solo cambia el footer
  legal. Siempre la indica el usuario.
- `copy` (opcional): `"approved"` o `"draft"`. Default: `approved` en inglés (viene de Figma), `draft` en los
  demás idiomas. Si el texto lo redactaste tú a partir de una tarea (y no viene de Figma ni de un
  documento con el texto final), ponlo en `draft` aunque sea inglés. Pásalo a `approved` solo cuando alguien del equipo aprobó ese texto. Un correo es
  **borrador** si su `copy` o el `status` de `locales/<lang>.json` no están aprobados: el preview y el PDF
  muestran el aviso "BORRADOR" y **no se genera producción**.
- La traducción **no tiene que ser literal**: cada idioma puede cambiar palabras, tono, orden y largo de
  las frases. Lo que no cambia son los nombres de las variables (`[First Name]`…), el footer legal y,
  salvo excepción aprobada, los bloques.
- `subject`: asunto del correo (también va en `<title>`).
- `preheader`: texto de vista previa en la bandeja (≈ 40–90 caracteres). Siempre definirlo.
- `help` (opcional, default `true`): `false` quita la línea "Need help?" (p. ej. el OTP, que ya trae su
  propia línea de soporte).
- `more_from_tradeview` (opcional): `true` agrega la banda "More from Tradeview" antes del footer. Para
  fijar otros links: `{"academy_url": "https://…", "blog_url": "https://…"}` (default: los de `delivery.json`).
- `blocks`: lista ordenada de bloques del Body.

## Orden obligatorio

hero **o** (icono → título) → subtítulo → imagen → saludo → contenido (párrafos, pills, cards, headings, código, aviso, nota, pasos) → CTA

El script avisa si el orden se rompe, si hay CTAs **distintos** (repetir el mismo CTA está permitido) o
si hay `hero` junto con `icon`/`title`. Los bloques opcionales simplemente se omiten.

## Tipos de bloque

| type | Campos | Notas |
|---|---|---|
| `hero` | `title`, `icon` (opcional), `alt` | Banner con degradado, siempre el primer bloque. **Solo** correos transaccionales (depósito, retiro, transferencia, formularios). Reemplaza a `icon` + `title`. |
| `icon` | `name`, `alt` | Estado: check-circle (verde, éxito) · ban · alert-circle · document · clock · clipboard-clock · password · deposit · withdrawal · transfer · call · download (lila). Para uno nuevo ver SKILL.md → "Agregar un icono". |
| `title` | `text` | H1. Admite HTML. Para forzar el corte de línea de la maqueta usa `<br>` (aplica también en celular). |
| `subtitle` | `text` | Debajo del H1. |
| `image` | `src`, `alt` | Banner 650px de ancho, fluido. `src` = ruta local relativa al spec (se sube a S3 con las demás imágenes) o URL `https://`. |
| `greeting` | `text` (opcional) | Default según idioma (`Hi [First Name],`, `Hola [First Name],`…). |
| `paragraph` | `text`, `margin_bottom` (opcional) | Admite `<strong>`, `<a>`, `&rsquo;`. El espaciado es automático (20px dentro de un grupo, 36px entre grupos, como en Figma); `margin_bottom` solo si la maqueta lo pide. |
| `pill` | `text`, `variant` (opcional) | `warning` (amarillo, default) · `success` (verde) · `error` (rojo). |
| `heading` | `text` | Título de sección 18px/600 (ej. "Withdrawal details"). |
| `list_card` | `items` (lista de strings) | Card con viñetas. Requisitos, pasos, motivos de rechazo. |
| `details_card` | `title` (opcional), `rows` **o** `sections` | Filas `[label, valor]` o `[label, valor, "copy"]` (agrega icono de copiar). `sections`: `[{"title": "Employment details:", "rows": [...]}, …]` para agrupar dentro de una sola card. |
| `code` | `label` (opcional), `code` | Código de un solo uso en card, con icono de copiar. Ej.: `{"type":"code","label":"One-time code:","code":"[OTP Code]"}`. |
| `alert` | `text` | Aviso informativo: fondo `#0F0631`, borde lila, icono info, 12px. |
| `note` | `text`, `icon` (opcional) | Nota con borde lila, 14px, links en `#EFF4FF`. `icon`: `apple` o el nombre de un icono de estado. |
| `steps` | `items` | Tarjetas numeradas. Cada ítem: `icon`, `title`, `text` (opcional), `downloads` (opcional), `footnote` (opcional). `downloads`: `[{"platform": "windows"\|"macos"\|"ios"\|"android"\|"web", "href": "…", "label": "…"(opcional)}]`. |
| `cta` | `label`, `href` | Botón pill `#EB0052`, bulletproof + VML para Outlook. Sentence case ("Go to Cabinet"). |

## Texto y variables

- **Todo el texto se inyecta**: el texto del cuerpo va en el spec de cada idioma y los textos fijos
  (saludo por defecto, ayuda, firma, footer) salen de `locales/<lang>.json`. Nunca se escribe texto
  en la plantilla.
- **Los datos de la persona y de la cuenta nunca van escritos**: siempre como variable — `[First Name]`,
  `[Account]`, `[Amount]`, `[OTP Code]`, `[Account number]`, etc. Se escriben **igual en todos los
  idiomas** (en inglés, entre corchetes). En el spec, en preview y en PDF se ven así, legibles.
- **En producción se convierten a Jinja** con el mapa de `delivery.json` → `variables`
  (`[First Name]` → `{{ data['firstName'] }}`, `[Account number]` → `{{ data['login'] }}`…). Las que no
  estén en el mapa quedan entre corchetes y el script avisa "sin key de backend": pide a dev el nombre
  del campo y agrégalo. No inventes keys.
- **Links fijos** (`[cabinet_url]`, `[academy_url]`, `[blog_url]`) se reemplazan por las URLs reales de
  `delivery.json` → `links` en todas las salidas. `[cabinet_url]` usa el idioma del correo.
- `{{year}}` se reemplaza por el año actual al construir (así lo hace dev).
- Copiar el texto de la maqueta **exacto** (incluidas comas y mayúsculas).
- Usar entidades HTML para apóstrofes tipográficos: `&rsquo;`.
- Variables del design system: `[First Name]`, `(amount) (currency)`, `[Account]`, `[Amount]`,
  `[Platform]`, `[Trading platform]`, `[Trading instrument]`, `[Withdrawal method]`, `[Request ID]`,
  `[Transaction ID]`, `[Transaction type]`, `[Associated email]`, `[Date]`, `[Status]`, `[Description]`,
  `[OTP Code]`, `[Account number]`, `[Trading password]`, `[Investor password]`. Montos y plataforma
  dentro de párrafos van en `<strong>`.
- No inventes variables nuevas sin mencionarlo al usuario.

## Ejemplos

Ver `examples/`:
- Verificación: proof-of-address-resubmitted, proof-of-address-rejected, submit-new-proof-of-address, id-expired.
- Cuenta nueva: one-time-code (OTP, `help: false`), trading-account-ready-mt4 (credenciales, aviso, nota, pasos, More from Tradeview).
- Movimientos: deposit-confirmed (+ `.es` y `.ar` para ver idiomas y RTL), withdrawal-declined, withdrawal-in-progress.
- Transaccional con hero: deposit-form-employed (formulario de +25.000 USD, card con secciones).
