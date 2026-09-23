# Reglas de diseño de correos Tradeview Markets

Fuente de verdad: archivo de Figma **Emails** → página "New user and active user flows"
(`https://www.figma.com/design/yAI1PcA8Zkv9RFUua3RVz4/Emails?node-id=9178-473`), secciones
**New user / Live account**, **Active user** y **Footer**. La sección **Research** no se usa. La sección
**Active user - old** solo aporta el bloque `hero` (ver abajo).

Los correos se construyen a **750px fluido**, igual que Figma y que los correos que hoy tiene dev en
producción: las medidas de Figma se usan **1:1**. Las decisiones marcadas con ★ son del equipo y mandan
sobre Figma. El estándar técnico de dev (tablas, CSS inline, S3, Jinja) está en
`references/delivery-and-handoff.md`.

## Estructura

```
Fondo exterior #272336 (50px arriba/abajo)
└─ Contenedor 750px fluido (max-width 750, width 100%)
   ├─ HEADER  #000000 · padding 14px 0 · logo a color centrado 170×29
   ├─ HERO    opcional, solo correos transaccionales (ver "Hero") · 222px de alto
   ├─ BODY    #080B18 · padding 50px (contenido de 650px)
   │    icono → título → subtítulo → imagen → saludo → contenido → CTA → ayuda → firma
   ├─ MORE FROM TRADEVIEW  opcional · #0F0631 · padding 24px 50px
   └─ FOOTER  #000000 · padding 56px 50px
        título + 6 redes | logo Tradeview blanco + logo EDGE blanco
        3 párrafos legales 11px, según entidad (LTD / SAC) e idioma
```

**Espaciado vertical (Figma):** 20px entre elementos del mismo grupo (icono→título→subtítulo,
saludo→pill/párrafo, título de sección→su card, card→aviso, nota→pasos) y **36px** entre grupos.

## Colores

| Uso | Valor |
|---|---|
| Header / Footer | `#000000` |
| Body | `#080B18` |
| Fondo exterior | `#272336` |
| Cards de datos (lista, detalles, código) | `#272336`, radio 20px |
| Superficie secundaria (pasos, aviso, More from Tradeview) | `#0F0631` |
| Texto | `#FFFFFF` |
| Link del email de soporte | `#D1E0FF` subrayado |
| Link de la web y demás links | `#A898FB` subrayado |
| Link dentro de una nota | `#EFF4FF` subrayado |
| Bordes (aviso, nota) | `#A898FB` 1px |
| Bordes tarjetas More from Tradeview | `#3D326E` 1px (= `#A898FB` al 30% sobre `#0F0631`) |
| CTA | `#EB0052` (único color de acción) |
| Icono de éxito ★ | `#3ED47A` verde |
| Resto de iconos de estado | `#A898FB` lila |
| Pill aviso (`warning`) | fondo `#FFE8C2`, texto `#6B3A00` |
| Pill éxito (`success`) | fondo `#E6F5EA`, texto `#075C24` |
| Pill error (`error`) | fondo `#FFE5E5`, texto `#8D0000` |
| Círculos redes | fondo `#EEF1F8`, icono `#0A1A33` |

★ Icono de éxito en verde aunque algunos correos de Figma lo muestren lila. Decisión confirmada por el equipo.

## Tipografía

`'Plus Jakarta Sans','Inter',Arial,Helvetica,sans-serif` (Google Fonts cargado solo fuera de Outlook).
Por idioma se agregan fuentes de respaldo (ver `locales/*.json`): Noto Sans JP/SC/KR para japonés,
chino y coreano; **Tajawal** para árabe (así viene en Figma).

Sin media queries los tamaños son los mismos en desktop y mobile.

| Estilo | Tamaño/interlineado | Peso |
|---|---|---|
| H1 | 28/34 | 800 |
| Título del hero | 35/42 | 800 |
| Subtítulo | 14/20 | 400 |
| Título de sección (H3) ★ | 18/25 | 600 |
| Párrafo / saludo / pills | 14/20 | 400 |
| Valores en cards | 14/20 | 600 |
| Aviso | 12/17 | 400 |
| CTA | 17/24 | 600 |
| Botón outline | 12/17 | 700 |
| Firma | 14/20 | 600 |
| Título del footer | 17/24 | 600 |
| Legal | 11/15 | 400 |

★ Figma usa 16px o 18px para los títulos de sección según el correo; se normalizó a 18px.

## Componentes y medidas

- **Icono de estado:** 39×39 (36×36 dentro de las tarjetas de pasos). Material Symbols Rounded, weight 300 (ver SKILL.md).
- **Imagen:** 650px de ancho, fluida.
- **Card de lista:** `#272336`, radio 20px, padding 24px 32px 24px 40px, viñeta • + 12px entre ítems.
- **Card de detalles:** título de sección encima (16px), padding 24px 32px, 20px entre filas, valor
  semibold al lado opuesto; en celular los textos largos pasan a dos líneas. Puede llevar icono de copiar (20px, blanco)
  junto al valor y agruparse en secciones con subtítulo 14px/600.
- **Código (OTP):** misma card que detalles, código semibold con icono de copiar.
- **Aviso:** fondo `#0F0631`, borde 1px `#A898FB`, radio 8px, padding 16px, icono info 16px lila + 8px.
- **Nota:** sin fondo, borde 1px `#A898FB`, radio 8px, padding 12px, icono opcional + 10px, texto 14px.
- **Pasos:** tarjetas `#0F0631`, radio 12px, padding 24px, 20px entre tarjetas. Icono 36px + 16px +
  "N. Título" 18/600; 24px al texto. Descargas (32px debajo del título): logo de plataforma lila
  (24–28px de alto) + 12px + botón outline (borde blanco 1px, pill, padding 8px 12px, icono de descarga
  16px). 4 columnas en desktop, 2×2 en mobile.
- **CTA:** pill 100px, 56px de alto, padding 16px 24px, alineado al inicio.
  ★ Se puede repetir el **mismo** CTA (misma etiqueta y URL) en correos largos; nunca dos acciones distintas.
- **More from Tradeview:** banda `#0F0631` después de la firma, título 18/600, dos tarjetas de 313px
  (Academy y Blog) separadas 24px, borde `#3D326E`, radio 12px, padding 24px, logo + 16px + título
  17/600, texto 14px y botón outline a todo el ancho. Se apilan en mobile.
- **Redes:** círculos de 48px con 24px de separación; se achican solas en pantallas angostas.
- **Logos footer:** Tradeview 197×31, 21px de separación, EDGE 125×38, alineados al final.
- **Ayuda + firma:** "Need help?" en bold + email `#D1E0FF` · 36px · "Tradeview Markets" 600 · 20px · web lila.

## Hero (estilo "old") ★

Banner de 222px de alto entre header y body, con degradado `#0F0631 → #9589E1` (100°) más un brillo
magenta abajo a la derecha, y fallback de color sólido `#0F0631` (Outlook). Adentro: icono de estado
39px + 16px + título 35/42, blanco, weight 800, centrados. En celulares el título se ve grande (sin
media queries no se puede achicar solo en mobile): mantén los títulos del hero cortos.

**Solo** para correos transaccionales de depósito, retiro, transferencia o formularios (p. ej. el
formulario de depósitos de +25.000 USD). Las notificaciones y confirmaciones simples usan el
encabezado estándar (icono + título dentro del body).

## Idiomas y entidades

- Cada correo existe por **idioma** (`en`, `es`, `pt`, `ja`, `zh`, `ko`, `ar`) y por **entidad legal**
  (`ltd` = Tradeview Ltd., Islas Caimán; `sac` = Tradeview Financial Markets S.A.C., Perú). La
  entidad solo cambia el footer legal.
- El footer (título y legales) sale de Figma → sección Footer, copiado a `locales/<idioma>.json`.
  El resto de textos fijos de `locales/` (saludo, ayuda, More from Tradeview) son traducciones
  propuestas: revisarlas con el equipo antes de producción.
- **Árabe (RTL):** `dir="rtl"`, todo espejado (textos a la derecha, valores de cards a la izquierda,
  footer con logos a la izquierda y redes a la derecha, como en Figma). El legal en árabe viene en
  inglés en Figma, así que se renderiza LTR.
- **Japonés, chino, coreano:** mismo layout; solo cambia la fuente de respaldo.

## Reglas técnicas

El estándar de dev (un archivo, tablas, CSS inline, sin `<style>` ni flexbox, S3, Jinja) está en
`references/delivery-and-handoff.md`. Lo que eso implica para el diseño:

- **Mobile sin media queries:** el correo es fluido. Las filas de columnas (footer, More from Tradeview,
  descargas) son tablas flotantes que se apilan solas cuando no caben, envueltas en una celda para que
  el texto siguiente no se meta al costado. En Outlook desktop una tabla fantasma (`<!--[if mso]>`) las
  mantiene en fila.
- No hay estilos solo-mobile: nada de CTA a todo el ancho ni tamaños distintos en celular.
- Celdas con borde y radio llevan `border-collapse:separate` (con `collapse` el radio no se dibuja).
- `<meta name="color-scheme" content="dark">` + `supported-color-schemes`.
- CTA bulletproof: `<a>` con padding + botón VML para Outlook.
- Imágenes: PNG @2x mostrados a tamaño 1x, `alt` siempre, nunca SVG (Gmail/Outlook no lo renderizan).
- Peso < 100 KB (Gmail recorta a partir de 102 KB).
- Los iconos de copiar son decorativos (en un correo no se puede copiar al portapapeles).

## Discrepancias entre maqueta y design system

Sigue la **maqueta** (es lo que el usuario aprobó visualmente) y **avisa** al usuario de la diferencia en la respuesta. No modifiques el `design-system.md` a menos que el usuario lo pida explícitamente; si lo pide, registra el cambio ahí.
