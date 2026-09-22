# Instalar · tradeview-email-notifications

Genera correos transaccionales/de notificación de Tradeview (HTML responsive + preview + PDF)
a partir de una maqueta o una descripción. Elige tu plataforma:

## Claude.ai (chat web)

1. Descarga `tradeview-email-notifications.skill` (está en esta misma carpeta).
2. En Claude.ai: **Settings → Capabilities → Skills → Upload skill** y selecciona ese archivo.
3. Listo — cuando pidas un correo de Tradeview (verificación de documentos, retiro, depósito,
   avisos del Cabinet, etc.) Claude la activa solo.

## Claude Code (CLI / VS Code / editor)

1. Copia la carpeta `tradeview-email-notifications/` (esta carpeta, sin `cursor/` ni `openai/`
   si quieres dejarla más limpia, aunque no estorban) a:
   - `~/.claude/skills/tradeview-email-notifications/` para tenerla en todos tus proyectos, o
   - `.claude/skills/tradeview-email-notifications/` dentro de un proyecto puntual.
2. Reinicia Claude Code. La skill se activa sola cuando el pedido calza con su descripción.

## Cursor

1. Copia toda la carpeta `GmailTemplatesSkills/tradeview-email-notifications/` dentro del
   proyecto donde la vas a usar (necesita `scripts/`, `assets/`, `references/`, `examples/`
   junto al `.mdc`, no solo el `.mdc` solo).
2. Copia (o symlink) `cursor/tradeview-email-notifications.mdc` a la carpeta `.cursor/rules/`
   de ese proyecto.
3. Abre el Agent de Cursor y pide un correo de Tradeview — la regla se activa por descripción
   (Agent Requested). Si no se activa sola, menciónala explícitamente o pégala en el contexto.

## ChatGPT / OpenAI

OpenAI no tiene un instalador de skills como Claude. La alternativa es crear un **Custom GPT**
(o un Project) con Code Interpreter activado:

1. Sigue las instrucciones en `openai/CUSTOM_GPT_INSTRUCTIONS.md` (qué pegar en "Instructions"
   y qué archivos subir como Knowledge).
2. Guarda el GPT como privado para tu equipo o compártelo por link interno.

---

Todas las variantes comparten la misma fuente de verdad: `scripts/`, `assets/`, `examples/` y
`references/`. Si corriges algo del diseño o de las reglas, actualízalo ahí y repite el paso de
empaquetado/subida en cada plataforma donde ya esté instalada.
