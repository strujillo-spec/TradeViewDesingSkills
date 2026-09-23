# Instalar · tradeview-email-notifications

Genera los correos transaccionales de Tradeview (verificación de documentos, depósitos, retiros,
OTP, cuenta nueva…) a partir de una maqueta, un link de Figma o una descripción. Funciona en 7
idiomas (en, es, pt, ja, zh, ko, ar) y para las dos entidades (Tradeview Ltd. y S.A.C.). Entrega
tres cosas por correo: **PDF** para aprobar, **preview** para ver en el navegador y **producción**
con el estándar de desarrollo (tablas, CSS inline, imágenes en S3, variables Jinja).

La skill necesita la carpeta completa: `SKILL.md`, `scripts/`, `assets/`, `locales/`, `examples/`,
`references/` y `delivery.json`. Elige tu plataforma:

## Claude.ai (chat web)

No necesitas instalar nada en tu computadora: Claude corre los scripts en su propio entorno.

1. Descarga `tradeview-email-notifications.skill` (está en esta misma carpeta).
2. En Claude.ai: **Settings → Capabilities → Skills → Upload skill** y selecciona ese archivo.
3. Listo — cuando pidas un correo de Tradeview, Claude la activa solo.

Si ya la tenías instalada, borra la versión anterior y sube la nueva.

## Claude Code (CLI / VS Code / editor)

**Requisitos:** Python 3 y, para generar PDF, screenshots e imágenes:
```bash
pip install playwright && python -m playwright install chromium
```

1. Copia la carpeta `tradeview-email-notifications/` (esta carpeta; `cursor/` y `openai/` no hacen
   falta pero no estorban) a:
   - `~/.claude/skills/tradeview-email-notifications/` para tenerla en todos tus proyectos, o
   - `.claude/skills/tradeview-email-notifications/` dentro de un proyecto puntual.
2. Reinicia Claude Code. La skill se activa sola cuando el pedido calza con su descripción.

## Cursor

**Requisitos:** los mismos que Claude Code (Python 3 + playwright).

1. Copia toda la carpeta `GmailTemplatesSkills/tradeview-email-notifications/` dentro del proyecto
   donde la vas a usar. El `.mdc` solo no alcanza: necesita el resto de la carpeta al lado.
2. Copia (o symlink) `cursor/tradeview-email-notifications.mdc` a la carpeta `.cursor/rules/` de ese
   proyecto.
3. Abre el Agent de Cursor y pide un correo de Tradeview — la regla se activa por descripción
   (Agent Requested). Si no se activa sola, menciónala explícitamente o pégala en el contexto.

Los correos quedan en `GmailTemplatesSkills/tradeview-email-notifications/output/tradeview-emails/`.

## ChatGPT / OpenAI

OpenAI no tiene un instalador de skills como Claude. La alternativa es crear un **Custom GPT**
(o un Project) con Code Interpreter activado:

1. Sigue las instrucciones en `openai/CUSTOM_GPT_INSTRUCTIONS.md` (qué pegar en "Instructions",
   cómo armar `skill.zip` y qué archivos subir como Knowledge).
2. Guarda el GPT como privado para tu equipo o compártelo por link interno.

Si la skill cambia, vuelve a armar `skill.zip` y reemplaza los archivos del GPT.

---

## Mantener la skill actualizada

Todas las plataformas usan los mismos archivos. Si cambias algo (diseño, reglas, idiomas, variables
de backend), hazlo en esta carpeta y después actualiza cada plataforma donde esté instalada:

- **Claude.ai:** regenera el `.skill` desde `GmailTemplatesSkills/` y vuelve a subirlo:
  ```bash
  cd GmailTemplatesSkills
  rm -f tradeview-email-notifications/tradeview-email-notifications.skill
  zip -r /tmp/tv.skill tradeview-email-notifications \
    -x 'tradeview-email-notifications/cursor/*' 'tradeview-email-notifications/openai/*' \
       'tradeview-email-notifications/INSTALL.md' 'tradeview-email-notifications/output/*' '*.DS_Store'
  mv /tmp/tv.skill tradeview-email-notifications/tradeview-email-notifications.skill
  ```
- **Claude Code / Cursor:** vuelve a copiar la carpeta (o haz `git pull` si la usas desde el repo).
- **ChatGPT:** vuelve a armar `skill.zip` y reemplázalo en el GPT.
