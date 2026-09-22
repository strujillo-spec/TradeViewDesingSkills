# Formato del spec JSON

Cada correo se describe con un JSON. `build_email.py` se encarga del header, contenedor, bloque de ayuda/firma y footer — el spec solo describe el **Body**.

```json
{
  "slug": "proof-of-address-rejected",
  "subject": "Your proof of address document was rejected",
  "preheader": "Please upload a new proof of address that meets our requirements.",
  "blocks": [ ... ]
}
```

- `slug` (opcional): nombre de archivo. Si falta, se usa el nombre del JSON. Usar kebab-case en inglés.
- `subject`: asunto del correo (también va en `<title>`).
- `preheader`: texto de vista previa en la bandeja (≈ 40–90 caracteres). Siempre definirlo.
- `blocks`: lista ordenada de bloques del Body.

## Orden obligatorio

icono → título → subtítulo → imagen → saludo → contenido (párrafos, pill, cards, headings) → CTA

El script avisa si el orden se rompe o si hay más de un CTA. Los bloques opcionales simplemente se omiten.

## Tipos de bloque

| type | Campos | Notas |
|---|---|---|
| `icon` | `name`, `alt` | `name` ∈ check-circle (verde, éxito) · ban · clipboard-clock · clock · alert-circle · document (lila). Para uno nuevo ver SKILL.md → "Agregar un icono". |
| `title` | `text` | H1. Admite HTML. Para forzar el corte de línea de la maqueta solo en desktop: `<br class="hide-mobile">`. |
| `subtitle` | `text` | Debajo del H1 (queda a 4px). |
| `image` | `src`, `alt` | Banner 520px de ancho (~2.5:1). `src` = ruta local relativa al spec o URL `https://`. |
| `greeting` | `text` (opcional) | Default: `Hi [First Name],` |
| `paragraph` | `text`, `margin_bottom` (opcional) | Admite `<strong>`, `<a>`, `&rsquo;`. El margen se calcula solo: 0 antes de `list_card`, 32 si es el último bloque, 20 en otros casos. Forzar `32` antes de un `details_card`. |
| `pill` | `text` | Pill de estado amarillo (`#FFE8C2` / `#6B3A00`). |
| `heading` | `text` | H3 17px/600 (ej. "Withdrawal details"). |
| `list_card` | `items` (lista de strings) | Card `#272336` radio 20px con viñetas. Requisitos, pasos, motivos de rechazo. |
| `details_card` | `title` (opcional), `rows` ([[label, valor], …]) | Filas clave/valor; valor en bold a la derecha. En mobile se apilan filas con email o valores largos. |
| `cta` | `label`, `href` | Botón pill `#EB0052`, bulletproof + VML para Outlook. Sentence case ("Go to Cabinet"). Uno solo. |

## Texto y variables

- Copiar el texto de la maqueta **exacto** (incluidas comas y mayúsculas); el copy de los correos está en inglés.
- Usar entidades HTML para apóstrofes tipográficos: `&rsquo;`.
- Variables del design system: `[First Name]`, `[cabinet_url]`, `(Platform)`, `(Account type)`, `(amount) (currency)`, `[Account]`, `[Withdrawal method]`, `[Request ID]`, `[Associated email]`, `[Date]`, `[Status]`, `{{year}}`. Variables de montos/plataforma dentro de párrafos van en `<strong>`.
- No inventes variables nuevas sin mencionarlo al usuario; el script lista las que quedan para reemplazar en el ESP.

## Ejemplos

Ver `examples/`: proof-of-address-resubmitted, proof-of-address-rejected, submit-new-proof-of-address, withdrawal-in-progress, id-expired.
