# Reglas de diseño de correos Tradeview Markets

Resumen de la sección 8 del `design-system.md` del proyecto **más las decisiones tomadas al construir los correos reales**. Si el usuario tiene un `design-system.md` en el proyecto, léelo también: manda sobre lo genérico, pero las decisiones marcadas como ★ son posteriores y lo actualizan.

## Estructura

```
Fondo exterior #272336 ★ (40px arriba/abajo desktop, 0 mobile)
└─ Contenedor 600px (100% en ≤480px)
   ├─ HEADER  #000000 · padding 14px 0 · logo a color centrado 170×29 (140 mobile)
   ├─ BODY    #080B18 · padding 48px 40px (32px 20px mobile)
   │    icono → título → subtítulo → imagen → saludo → contenido → CTA → ayuda → firma
   └─ FOOTER  #000000 · padding 40px (24px 20px mobile)
        Contact Us + 6 redes | logo Tradeview blanco + logo EDGE blanco
        3 párrafos legales 11px
```

★ El fondo exterior era `#080B18` en el design system original; el usuario lo cambió a `#272336` para que el correo se vea como una tarjeta.

## Colores

| Uso | Valor |
|---|---|
| Header / Footer | `#000000` |
| Body | `#080B18` |
| Fondo exterior ★ | `#272336` |
| Cards | `#272336`, radio 20px |
| Texto | `#FFFFFF` |
| Links (subrayados) | `#A898FB` |
| CTA | `#EB0052` (único color de acción) |
| Icono de éxito ★ | `#3ED47A` verde |
| Resto de iconos de estado | `#A898FB` lila |
| Pill aviso | fondo `#FFE8C2`, texto `#6B3A00` |
| Círculos redes | fondo `#EEF1F8`, icono `#0A1A33` |

★ Iconos: éxito en verde (así viene en la maqueta aprobada), todos los demás en lila. Decisión confirmada por el usuario.

## Tipografía

`'Plus Jakarta Sans','Inter',Arial,Helvetica,sans-serif` (Google Fonts cargado solo fuera de Outlook).

| Estilo | Desktop | Mobile | Peso |
|---|---|---|---|
| H1 | 30/38 | 24/30 | 700 |
| Subtítulo | 15/21 | — | 400 |
| H3 | 17/24 | — | 600 |
| Párrafo | 15/23 | 15 | 400 |
| CTA | 18 | 17 | 500 |
| Firma | 15 | 15 | 600 |
| Contact Us | 18 | — | 500 |
| Legal | 11/16 | 11 | 400 |

## Componentes y medidas

- **Icono de estado:** 36×36, 16px abajo.
- **Párrafos:** 20px entre ellos; 32px antes del bloque de ayuda.
- **Card de lista ★:** `#272336`, radio 20px, padding 24px 32px 24px 40px (20px mobile), viñeta • + 12px entre ítems. 12px arriba, 32px abajo.
- **Card de detalles:** H3 encima (16px), padding 24px 32px, 24px entre filas, valor bold a la derecha; filas largas se apilan en mobile.
- **CTA:** pill 999px, padding 18px 24px, alineado a la izquierda; 100% ancho en mobile. 12px arriba, 32px abajo.
- **Redes ★:** 44px con 12px de separación en desktop (40px en mobile). El design system dice 48px/24px, pero no cabe junto a los logos en 600px.
- **Logos footer ★:** 170px / 108px desktop, 160px / 100px mobile.
- **Ayuda + firma:** "Need help?" en bold + email lila · 32px · "Tradeview Markets" 600 · 12px · web lila.

## Reglas técnicas

- Tablas `role="presentation"`, estilos inline, media queries solo como mejora (Gmail app sin media queries igual se ve bien).
- `<meta name="color-scheme" content="dark">` + `supported-color-schemes`.
- Condicionales `<!--[if mso]>` para ancho 600 fijo y botón VML.
- Imágenes de producción: PNG @2x mostrados a tamaño 1x, `alt` siempre, nunca SVG (Gmail/Outlook no lo renderizan).
- Peso < 100 KB (Gmail recorta a partir de 102 KB).
- Copyright con `{{year}}`.

## Discrepancias entre maqueta y design system

Sigue la **maqueta** (es lo que el usuario aprobó visualmente) y **avisa** al usuario de la diferencia en la respuesta. No modifiques el `design-system.md` a menos que el usuario lo pida explícitamente; si lo pide, registra el cambio ahí.
