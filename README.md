# Chat Demo — Chatbot de Incidentes vía WhatsApp

Chatbot conversacional para una planta productora de huevo que permite a operadores reportar incidentes de producción a través de WhatsApp. Usa **LangGraph** como motor de conversación, **GPT-4o-mini** para clasificación inteligente, y soporta multimedia (audio e imágenes).

## Arquitectura general

```
Usuario WhatsApp
       │
       ▼
Meta Cloud API  ──webhook POST──▶  FastAPI (webhook.py)
                                        │
                                        ▼
                                  GraphAdapter
                                   ├─ /comando → respuesta directa
                                   └─ texto normal ─▶ LangGraph (grafo)
                                                          │
                                                          ▼
                                                      SQLite DBs
                                                   ┌──────┴──────┐
                                              chatbot.db    langgraph.db
                                           (users, incidents,  (checkpoints)
                                            conversation_log,
                                            attachments)
```

### Componentes principales

| Componente | Archivo | Función |
|---|---|---|
| **Webhook** | `src/whatsapp/webhook.py` | Endpoint FastAPI que recibe mensajes de Meta y responde < 5s |
| **Cliente WhatsApp** | `src/whatsapp/client.py` | Envía mensajes y descarga media vía Graph API v21.0 |
| **GraphAdapter** | `src/whatsapp/graph_adapter.py` | Puente entre WhatsApp y LangGraph; maneja threads, comandos y multimedia |
| **Grafo** | `src/graph/` | Definición del flujo conversacional con LangGraph |
| **Nodos** | `src/graph/nodes.py` | Lógica de cada paso del flujo (10 nodos) |
| **Routing** | `src/graph/edges.py` | Funciones de enrutamiento condicional entre nodos |
| **Estado** | `src/graph/state.py` | `ConversationState` — TypedDict con todo el estado de la conversación |
| **Modelos** | `src/models.py` | `UserProfile`, `IncidentRecord`, `IncidentTemplate`, enums |
| **Repositorios** | `src/db/repositories.py` | CRUD para users, incidents, attachments, conversation_log |
| **Catálogo** | `src/catalog/parser.py` | Parser del catálogo de incidentes (markdown) |
| **Prompts** | `src/prompts/templates/` | Templates Jinja2 para system, classify, collect_field, confirm |
| **Media** | `src/media/processor.py` | Transcripción con Whisper, análisis de imagen con GPT-4o Vision |

## Flujo conversacional (Grafo LangGraph)

El grafo usa `interrupt()` para pausar en cada punto donde se necesita input del usuario. El estado se persiste en SQLite via `SqliteSaver`.

```
START
  │
  ▼
greeting ─────────────────────────────┐
  │                                   │
  ▼ (usuario nuevo)                   ▼ (usuario existente)
register_user                    collect_description
  │                                   │
  └──────────▶ collect_description ◀──┘
                    │
                    ▼
               classify  (LLM → top 3 candidatos)
                    │
                    ▼
          confirm_classification  (usuario elige 1, 2, 3 o "ninguno")
                    │
                    ▼
            collect_fields  ◀──────┐ (loop: planta, línea, celda, turno, descripción)
                    │              │
                    ▼              │
              confirmation         │
                    │              │
                    ▼              │
         process_confirmation      │
              │    │    │          │
              ▼    ▼    ▼          │
           save  edit  cancel      │
            │      │     │         │
            ▼      └─────┘─────────┘
           END
```

### Nodos del grafo

| Nodo | Descripción |
|---|---|
| `greeting` | Identifica al usuario por teléfono. Si existe, saluda por nombre y muestra incidentes recientes. Si es nuevo, pide nombre. |
| `register_user` | Recoge nombre del usuario nuevo. El LLM extrae nombre, área, turno, línea y rol del texto libre. Guarda perfil en BD. |
| `collect_description` | Pide descripción del incidente. Soporta texto, audio (transcrito con Whisper) e imágenes (analizadas con GPT-4o Vision). |
| `classify` | Envía la descripción + catálogo completo a GPT-4o-mini. Retorna JSON con top 3 candidatos (código, nombre, confianza, razón). |
| `confirm_classification` | Muestra los 3 candidatos al usuario. Al seleccionar uno, auto-completa campos del catálogo (categoría, severidad, acción inmediata). |
| `collect_fields` | Loop que pide campos faltantes uno por uno: planta, línea, celda, turno, descripción detallada. |
| `confirmation` | Genera resumen formateado del incidente completo. Pregunta: confirmar (1), editar (2) o cancelar (3). |
| `process_confirmation` | Enruta según respuesta del usuario hacia save, edit o cancelación. |
| `edit` | Permite modificar un campo específico. Mapea nombres en español a nombres canónicos. Regresa a `collect_fields`. |
| `save` | Persiste `IncidentRecord` en BD, guarda adjuntos multimedia, actualiza perfil del usuario. Retorna confirmación con ID. |

### Estado de la conversación

El `ConversationState` (definido en `src/graph/state.py`) mantiene:

- `messages` — Historial de mensajes (LangChain)
- `user_phone`, `user_profile` — Identificación del usuario
- `current_incident` — Campos del incidente en construcción
- `classification_candidates` — Top 3 del LLM
- `missing_fields`, `current_field` — Control del loop de campos
- `confirmed` — Decisión del usuario en confirmación
- `awaiting_input` — Etiqueta del input esperado
- `media_attachments` — Archivos multimedia acumulados

## Procesamiento multimedia

| Tipo | Herramienta | Modelo | Descripción |
|---|---|---|---|
| Audio | OpenAI Whisper | `whisper-1` | Transcribe notas de voz a texto (idioma: español) |
| Imagen | OpenAI Vision | `gpt-4o` | Analiza fotos en contexto industrial (daños, equipos, seguridad) |

Los archivos se guardan en `data/media/{incident_id}/{filename}` al persistir el incidente.

## Base de datos

SQLite con dos archivos separados:

| BD | Ruta | Contenido |
|---|---|---|
| **Principal** | `data/chatbot.db` | `users`, `incidents`, `incident_attachments`, `conversation_log` |
| **Checkpoints** | `data/checkpoints/langgraph.db` | Estado del grafo por thread (tabla `checkpoints`, `writes`) |

### Tablas principales

- **users** — Perfil del operador (`phone_number` PK, name, area, shift, role, line)
- **incidents** — Registro completo del incidente (código, categoría, severidad, campos de planta, acciones)
- **incident_attachments** — Archivos adjuntos vinculados a un incidente
- **conversation_log** — Historial de mensajes por thread_id

## Catálogo de incidentes

El catálogo define los tipos de incidentes disponibles, parseados desde markdown. Cada template incluye:

- **Código** (ej. `MEC-001`, `PRO-003`)
- **Categoría**: MEC (Mecánico), PRO (Producción), CAL (Calidad), SEG (Seguridad), LOG (Logística), OPS (Operaciones)
- **Severidad**: LOW, MEDIUM, HIGH, CRITICAL
- **Nombre, descripción, impacto, acción inmediata, área responsable**

El LLM usa el catálogo completo como contexto para clasificar el incidente descrito por el usuario.

## Comandos de WhatsApp

Los usuarios pueden enviar comandos directamente en el chat:

| Comando | Descripción |
|---------|-------------|
| `/reset` | Reinicia la conversación actual (borra checkpoints y log). |
| `/borrar` | Elimina tu perfil de usuario y reinicia el chat por completo. |
| `/eliminar_usuario` | Elimina solo tu perfil de la base de datos, sin afectar la conversación. |
| `/ayuda` | Muestra la lista de comandos disponibles. |

Cualquier mensaje que no empiece con `/` se procesa normalmente por el flujo conversacional.

## Estructura del proyecto

```
chat_demo/
├── main.py                        # Entry point (uvicorn)
├── .env.example                   # Variables de entorno requeridas
├── pyproject.toml                 # Dependencias y metadata
├── catalog/
│   └── Incidentes.xlsx            # Catálogo de incidentes
├── data/                          # Datos en runtime (gitignored)
│   ├── chatbot.db
│   ├── checkpoints/langgraph.db
│   └── media/
├── src/
│   ├── config.py                  # Rutas, API keys, modelos
│   ├── models.py                  # Pydantic: UserProfile, IncidentRecord, enums
│   ├── db/
│   │   ├── engine.py              # Conexión SQLite, DDL, init_db()
│   │   └── repositories.py        # UserRepo, IncidentRepo, AttachmentRepo, ConversationLogRepo
│   ├── graph/
│   │   ├── builder.py             # StateGraph: nodos, edges, compilación
│   │   ├── state.py               # ConversationState TypedDict
│   │   ├── nodes.py               # 10 nodos del grafo
│   │   └── edges.py               # Funciones de routing condicional
│   ├── memory/
│   │   └── user_memory.py         # Carga perfil + historial de incidentes
│   ├── media/
│   │   └── processor.py           # Whisper (audio), GPT-4o Vision (imagen), save
│   ├── catalog/
│   │   └── parser.py              # Parser de catálogo markdown → IncidentTemplate
│   ├── prompts/
│   │   ├── loader.py              # Jinja2 environment
│   │   └── templates/
│   │       ├── system.j2          # System prompt (personalizado por usuario)
│   │       ├── classify.j2        # Prompt de clasificación con catálogo
│   │       ├── collect_field.j2   # Prompt para pedir un campo
│   │       └── confirm.j2         # Resumen para confirmación
│   └── whatsapp/
│       ├── client.py              # send_text_message, download_media, parse_webhook
│       ├── webhook.py             # FastAPI: GET /webhook, POST /webhook, POST /reset
│       └── graph_adapter.py       # GraphAdapter: commands, threading, multimedia
```

## Setup

1. Copiar `.env.example` a `.env` y configurar:
   ```
   OPENAI_API_KEY=sk-...
   MODEL_NAME=gpt-4o-mini
   MODEL_TEMPERATURE=0.1
   WHATSAPP_VERIFY_TOKEN=mi_token
   WHATSAPP_ACCESS_TOKEN=EAAxxxxx...
   WHATSAPP_PHONE_NUMBER_ID=123456789
   VISION_MODEL=gpt-4o
   WHISPER_MODEL=whisper-1
   ```

2. Instalar dependencias:
   ```bash
   uv sync
   ```

3. Iniciar el servidor:
   ```bash
   python main.py
   ```
   O directamente:
   ```bash
   uvicorn src.whatsapp.webhook:app --host 0.0.0.0 --port 8000 --reload
   ```

4. Configurar el webhook en Meta Developer Portal apuntando a `https://<tu-dominio>/webhook`.
