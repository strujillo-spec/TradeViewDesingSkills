# TradeViewDesingSkills

Repositorio de skills de diseño para el equipo de TradeView. Cada carpeta de primer nivel agrupa
las skills de un frente de trabajo; dentro de cada una puede haber una o varias skills, cada una
con su propio `SKILL.md`, su `INSTALL.md` y los adaptadores para instalarla en distintas
plataformas de IA (Claude, Cursor, ChatGPT/OpenAI).

```
TradeViewDesingSkills/
├── GmailTemplatesSkills/       ← skills para correos/plantillas de Tradeview
│   └── tradeview-email-notifications/
├── TradeViewLanging/           ← skills para landing pages de TradeView (próximamente)
└── HubTradeSkill/              ← skills para el Hub Trade (próximamente)
```

## Cómo usar una skill de este repo

1. Clona o descarga este repositorio.
2. Entra a la carpeta de la skill que quieras (ej. `GmailTemplatesSkills/tradeview-email-notifications/`).
3. Abre su `INSTALL.md` y sigue los pasos de tu plataforma:
   - **Claude.ai** → subir el archivo `.skill` desde Settings → Capabilities → Skills.
   - **Claude Code** → copiar la carpeta a `.claude/skills/` o `~/.claude/skills/`.
   - **Cursor** → copiar la carpeta al proyecto + la regla `.mdc` a `.cursor/rules/`.
   - **ChatGPT/OpenAI** → crear un Custom GPT con las instrucciones y archivos indicados.

No hace falta instalar todas las plataformas: cada quien instala solo la que usa.

## Skills disponibles

| Carpeta | Skill | Qué hace |
|---|---|---|
| `GmailTemplatesSkills/` | `tradeview-email-notifications` | Genera correos transaccionales/de notificación de Tradeview (HTML responsive + preview + PDF) a partir de una maqueta o descripción. |
| `TradeViewLanging/` | — | Pendiente. |
| `HubTradeSkill/` | — | Pendiente. |

## Estructura de una skill

Cada skill sigue esta convención:

```
<nombre-skill>/
├── SKILL.md              ← definición original (formato nativo de Claude)
├── INSTALL.md             ← cómo instalarla en cada plataforma
├── <skill>.skill           ← paquete listo para subir a Claude.ai
├── references/             ← reglas, formatos, guías de entrega
├── scripts/                 ← lógica que hace el trabajo pesado
├── examples/                ← casos ya aprobados, como punto de partida
├── assets/                  ← recursos visuales (logos, iconos)
├── cursor/                  ← adaptación como Cursor Project Rule (.mdc)
└── openai/                  ← instrucciones para armar un Custom GPT
```

`SKILL.md` es la fuente de verdad. Los adaptadores de `cursor/` y `openai/` son traducciones de
ese mismo flujo a las capacidades de cada plataforma (ninguna de las dos tiene un formato de
"skill instalable" equivalente al de Claude, así que se resuelven con Project Rules y Custom GPT
respectivamente).

## Agregar una skill nueva

1. Crea o usa la carpeta del frente correspondiente (`GmailTemplatesSkills/`, `TradeViewLanging/`,
   `HubTradeSkill/`, o una nueva si aplica).
2. Dentro, crea la carpeta de la skill siguiendo la estructura de arriba.
3. Escribe `SKILL.md` primero (es la fuente de verdad); de ahí derivas `cursor/*.mdc` y
   `openai/CUSTOM_GPT_INSTRUCTIONS.md`.
4. Actualiza la tabla de "Skills disponibles" en este README.
