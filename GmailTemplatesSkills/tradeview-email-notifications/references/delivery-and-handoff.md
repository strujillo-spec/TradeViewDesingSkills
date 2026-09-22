# Entrega, dudas frecuentes y handoff a devs

El usuario típico **no es desarrollador** (es diseñador o de marketing). Todo lo de abajo nace de confusiones reales; explica en lenguaje simple y sin jerga.

## Los tres entregables — qué decirle al usuario

| Carpeta | Qué es | Para qué sirve | Para qué NO sirve |
|---|---|---|---|
| `pdf/` | Una "foto" del correo | Compartir por WhatsApp/Slack/correo y aprobar diseño. Se abre en cualquier lugar. | No es un correo |
| `preview/` | HTML de archivo único con logos incrustados en SVG | Ver el correo real en el navegador y probar el responsive, aunque se descargue suelto | No se puede enviar: Gmail/Outlook no muestran SVG |
| `produccion/` | HTML final + `assets/` (PNG @2x) | Lo que se entrega a los devs para cargar en el ESP | Abierto suelto (sin `assets/`) se ven las imágenes rotas |

Recomendación por defecto: para revisión → enviar PDF (y preview si quieren ver el responsive). Para implementación → enviar el zip completo a los devs.

## "No se ven los logos" — causas

Las imágenes de `produccion/` usan rutas relativas (`src="assets/…png"`). Se rompen si:
- abren el HTML desde dentro del zip sin descomprimir (Windows extrae solo ese archivo),
- descargan el HTML suelto sin la carpeta `assets/`,
- mueven el HTML de carpeta.

Un zip **no se puede descomprimir solo**. Si el usuario necesita que "se vea al abrirlo", la respuesta es PDF o preview, no el zip. Si el usuario quiere que producción funcione suelto, la única solución real es alojar las imágenes con URL pública y reconstruir con `--asset-base https://…/`.

Un correo real **nunca** puede cargar imágenes de una carpeta local, y Gmail bloquea imágenes base64. Por eso producción necesita CDN.

## Pasar a producción (lo que hacen los devs)

1. Subir `produccion/assets/*.png` a un servidor público (CDN de la empresa, S3, galería del ESP) y reemplazar `src="assets/` por la URL. Si el usuario da la URL, reconstruye tú con `--asset-base`.
2. Adaptar variables a la sintaxis del ESP: SendGrid `{{first_name}}`, Mailchimp `*|FNAME|*`, Salesforce MC `%%FirstName%%`, Brevo `{{ contact.FIRSTNAME }}`.
3. Crear la plantilla transaccional en el ESP (pegar HTML en modo código), definir asunto y remitente.
4. Conectar cada plantilla al evento del sistema que la dispara (ej. documento reenviado → correo de "re-submission complete").
5. Probar: Gmail web/app, Outlook desktop/365, Apple Mail; a 390, 480 y 600 px. Revisar imágenes, link del CTA y que no quede ninguna variable sin reemplazar.

## Nota de entrega para devs (plantilla)

Ofrécela cuando el usuario vaya a pasar los correos a desarrollo. Crear como `.md` dentro de la carpeta de salida:

```markdown
# Handoff · Correos transaccionales Tradeview Markets

## Archivos
- produccion/*.html — plantillas finales (tablas + inline CSS, bulletproof CTA, VML Outlook)
- produccion/assets/*.png — imágenes @2x (mostrar a tamaño 1x ya definido en el HTML)
- pdf/ — referencia visual aprobada

## Correos y eventos
| Plantilla | Asunto | Evento que lo dispara | CTA → URL |
|---|---|---|---|
| <slug>.html | <subject> | <evento — confirmar con producto> | <label> → [cabinet_url] |

## Variables
| Variable en HTML | Dato |
|---|---|
| [First Name] | Nombre del cliente |
| {{year}} | Año actual |
| … | … |

## Pendientes
- [ ] Subir assets a CDN y reemplazar `src="assets/`
- [ ] Adaptar variables a la sintaxis del ESP
- [ ] Preheader configurado (ya está en el HTML)
- [ ] Pruebas en Gmail, Outlook, Apple Mail (390/480/600px)
- [ ] Peso < 100 KB
```

Si dos correos tienen contenido casi igual (ej. "was rejected" vs "Submit a new proof of address"), señala que hay que definir qué evento dispara cada uno.
