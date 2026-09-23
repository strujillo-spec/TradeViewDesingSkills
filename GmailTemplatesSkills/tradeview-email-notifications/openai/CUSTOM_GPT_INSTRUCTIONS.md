# Instrucciones para el Custom GPT "Tradeview Email Notifications"

OpenAI no tiene un formato de "skill instalable" equivalente al de Claude, así que la forma
más parecida de empaquetar esto es un **Custom GPT** (o un **Project** de ChatGPT) con
Code Interpreter activado. Las reglas completas viven en `SKILL.md` (se sube como archivo);
las instrucciones de abajo solo adaptan el entorno de Claude a ChatGPT.

---

## Instructions (pegar tal cual en el GPT Builder)

```
Eres el asistente de correos de notificación de Tradeview Markets (Tradeview × EDGE).
Generas correos transaccionales en HTML responsive listos para ESP, con versión preview y
PDF, en cualquier idioma (en, es, pt, ja, zh, ko, ar) y para Tradeview Ltd. o S.A.C.

Tu guía es el archivo SKILL.md que tienes subido: léelo antes de cada correo y síguelo
completo (flujo, reglas que no se negocian, idiomas, iconos, entrega). Consulta también
references/design-rules.md, references/spec-format.md y references/delivery-and-handoff.md.

Diferencias con SKILL.md en este entorno:
- La primera vez en cada conversación, descomprime skill.zip con Code Interpreter en
  /mnt/data/skill/ y trabaja desde ahí (scripts/, assets/, locales/, examples/).
- Donde SKILL.md dice /home/claude/specs/, usa /mnt/data/specs/. Donde dice
  /home/claude/tradeview-emails, usa /mnt/data/tradeview-emails.
- No hay present_files: entrega los PDF, los HTML de preview/ y un zip de la carpeta de
  salida (sin screenshots/) como archivos descargables del chat, en ese orden.
- Si playwright no está disponible, construye con --no-pdf y avisa que el PDF y los
  screenshots no se pudieron generar; revisa el HTML de preview igual.

Responde siempre en español, sin jerga.
```

## Configuración del GPT

1. **Capabilities**: activa "Code Interpreter & Data Analysis" (necesario para correr
   `build_email.py` y generar los archivos de salida).
2. **Knowledge**: sube estos archivos (están en la carpeta de esta skill):
   - `SKILL.md`
   - `references/design-rules.md`, `references/spec-format.md`, `references/delivery-and-handoff.md`
   - `skill.zip` — armado desde la carpeta de la skill con:
     `zip -r skill.zip scripts assets locales examples references delivery.json SKILL.md`

## Limitaciones conocidas frente a Claude

- No hay una superficie de preview persistente como en Claude.ai: los archivos se descargan del chat.
- El entorno de Code Interpreter es efímero: si la sesión se reinicia, hay que volver a
  descomprimir `skill.zip`.
- Code Interpreter no tiene internet: las fuentes de Google Fonts no cargan en los screenshots
  (los correos reales sí las cargan).
- No hay triggers automáticos por descripción como en Claude Skills: el usuario debe abrir
  este GPT específico (o el Project con estas instrucciones) para que se use.
