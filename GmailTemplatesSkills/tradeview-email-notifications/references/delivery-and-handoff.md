# Entrega, dudas frecuentes y handoff a devs

El usuario típico **no es desarrollador** (es diseñador o de marketing). Todo lo de abajo nace de confusiones reales; explica en lenguaje simple y sin jerga.

## Estándar del equipo de desarrollo

Así trabaja dev en Tradeview, y así sale `produccion/`. El script lo cumple solo y falla si algo lo rompe:

- **Un solo archivo HTML** por correo.
- **Maquetado con tablas**, **CSS 100% inline**: sin bloque `<style>`, sin clases, **sin flexbox** (no todos los clientes de correo lo reconocen). Los comentarios `<!--[if mso]>` para Outlook no son CSS y sí se usan.
- **Imágenes por URL del bucket S3** (`delivery.json` → `asset_base`, hoy
  `https://documents-tvmarkets.s3.us-west-1.amazonaws.com/emails/`). Las sube **Dani Peña**.
- **Variables en Jinja** del backend: `{{ data['firstName'] }}`, `{{ data['login'] }}`… El mapa
  `[Variable] → {{ data['key'] }}` vive en `delivery.json`.
- **Ancho 750px fluido** (`max-width:750px; width:100%`).
- **Nombre de archivo** `<correo>-<idioma>-<entidad>.html`, ej. `deposit-confirmed-es-sac.html`.
- Año del copyright **fijo**, escrito al construir.

Referencia de dev: su plantilla `1st-live-account-otherp-en-ltd.html`.

## Los tres entregables — qué decirle al usuario

| Carpeta | Qué es | Para qué sirve | Para qué NO sirve |
|---|---|---|---|
| `pdf/` | Una "foto" del correo | Compartir por WhatsApp/Slack/correo y aprobar diseño. Se abre en cualquier lugar. | No es un correo |
| `preview/` | HTML de archivo único con imágenes incrustadas y variables legibles (`[First Name]`) | Ver el correo en el navegador y probar cómo se ve en celular | No se puede enviar |
| `produccion/` | HTML final para dev (S3 + Jinja) y `subir-a-s3/` con las imágenes | Lo que se entrega a desarrollo | Abierto antes de que Dani suba las imágenes, se ve sin imágenes |

Recomendación por defecto: para revisión → PDF (y preview si quieren ver mobile). Para implementación → el zip completo a dev.

## "No se ven las imágenes" — causas

Las imágenes de `produccion/` apuntan a S3. No aparecen si:
- Dani todavía no subió `produccion/subir-a-s3/` a la carpeta de S3,
- se subieron con otro nombre o a otra carpeta,
- cambió la carpeta de S3 y no se actualizó `delivery.json` (reconstruye con `--asset-base https://…/`).

Para revisar el diseño mientras tanto: preview o PDF, que siempre se ven.

## Variables sin key de backend

El script avisa `⚠ sin key de backend` cuando un correo usa una variable que todavía no está en
`delivery.json` (ej. `[Amount]`). Esas quedan entre corchetes en producción para que se note. Pide
a dev el nombre exacto del campo en `data` y agrégalo al mapa; **no inventes nombres de keys**.

## Pasar a producción (lo que hacen dev y Dani)

1. **Dani Peña** sube `produccion/subir-a-s3/*.png` a la carpeta de S3 de `asset_base`, con los mismos nombres.
2. **Dev** usa `produccion/<correo>-<idioma>-<entidad>.html` como plantilla Jinja. El backend elige el
   archivo según el idioma del cliente y la entidad de su cuenta, y llena `data`.
3. Completar en el backend las variables que el script marcó como "sin key".
4. Conectar cada plantilla al evento que la dispara (ej. documento reenviado → "re-submission complete").
5. Probar en Gmail web/app, Outlook desktop/365 y Apple Mail, a 390 y 750 px. Revisar imágenes, links y
   que no quede ninguna variable entre corchetes. Los correos en árabe se revisan en RTL.

## Nota de entrega para dev (plantilla)

Ofrécela cuando el usuario vaya a pasar los correos a desarrollo. Crear como `.md` dentro de la carpeta de salida:

```markdown
# Handoff · Correos transaccionales Tradeview Markets

## Archivos
- produccion/*.html — plantillas Jinja (tablas, CSS inline, sin <style>, 750px fluido, CTA bulletproof con VML)
- produccion/subir-a-s3/*.png — imágenes @2x → subir a https://documents-tvmarkets.s3.us-west-1.amazonaws.com/emails/ (Dani Peña)
- pdf/ — referencia visual aprobada

## Correos y eventos
| Plantilla | Idioma · Entidad | Asunto | Evento que lo dispara | CTA → URL |
|---|---|---|---|---|
| <correo>-<lang>-<entity>.html | <lang> · <LTD/SAC> | <subject> | <evento — confirmar con producto> | <label> → <url> |

## Variables (data)
| Jinja | Dato |
|---|---|
| {{ data['firstName'] }} | Nombre del cliente |
| … | … |

## Pendientes
- [ ] Subir imágenes a S3
- [ ] Keys de backend para: <variables marcadas como "sin key">
- [ ] Pruebas en Gmail, Outlook, Apple Mail (390/750px)
```

Si dos correos tienen contenido casi igual (ej. "was rejected" vs "Submit a new proof of address"), señala que hay que definir qué evento dispara cada uno.
