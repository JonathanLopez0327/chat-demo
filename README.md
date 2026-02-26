# Chat Demo — Chatbot de Tickets vía WhatsApp

Chatbot conversacional para **agencias de lotería y apuestas** que permite al personal reportar incidentes, alertas y reclamos a través de WhatsApp. Usa **LangGraph** como motor de conversación, **GPT-4o-mini** para clasificación inteligente, y soporta multimedia (audio e imágenes).

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

1. **Meta Cloud API** envía un webhook POST al servidor.
2. **FastAPI** recibe el mensaje y responde 200 de inmediato (requisito de Meta: < 5s).
3. En un **background task**, el `GraphAdapter` procesa el mensaje:
   - Si es un comando (`/reset`, `/ayuda`, etc.) → responde directamente.
   - Si es texto/media → lo pasa al grafo de LangGraph.
4. El grafo ejecuta el nodo correspondiente, pausando con `interrupt()` cuando necesita input.
5. La respuesta se extrae del último `AIMessage` y se envía de vuelta por WhatsApp.

### Componentes principales

| Componente | Archivo | Función |
|---|---|---|
| **Webhook** | `src/whatsapp/webhook.py` | Endpoint FastAPI — `GET /webhook` (verificación Meta), `POST /webhook` (mensajes), `POST /reset/{phone}` |
| **Cliente WhatsApp** | `src/whatsapp/client.py` | `send_text_message()`, `download_media()`, `parse_webhook_message()` — Graph API v21.0 |
| **GraphAdapter** | `src/whatsapp/graph_adapter.py` | Puente WhatsApp ↔ LangGraph: manejo de threads por teléfono, comandos slash, multimedia |
| **Grafo (builder)** | `src/graph/builder.py` | `StateGraph` con 10 nodos y edges condicionales |
| **Nodos** | `src/graph/nodes.py` | Lógica de cada paso: greeting, registro, clasificación, recolección de campos, guardado |
| **Routing** | `src/graph/edges.py` | 7 funciones de routing condicional entre nodos |
| **Estado** | `src/graph/state.py` | `ConversationState` — TypedDict con todo el estado de la conversación |
| **Modelos** | `src/models.py` | `UserProfile`, `IncidentRecord`, `IncidentTemplate`, enums (`Severity`, `Category`, `IncidentStatus`) |
| **Repositorios** | `src/db/repositories.py` | CRUD: `UserRepository`, `IncidentRepository`, `AttachmentRepository`, `ConversationLogRepository` |
| **Catálogo** | `src/catalog/parser.py` | Parser del catálogo de incidentes (Excel `.xlsx`) → `IncidentTemplate` |
| **Prompts** | `src/prompts/templates/` | Templates Jinja2: `system.j2`, `classify.j2`, `collect_field.j2`, `confirm.j2` |
| **Media** | `src/media/processor.py` | Transcripción con Whisper, análisis de imagen con GPT-4o Vision, guardado de archivos |
| **User memory** | `src/memory/user_memory.py` | `load_user_context()` — carga perfil + incidentes recientes para personalizar saludo |

## Flujo conversacional (Grafo LangGraph)

El grafo usa `interrupt()` de LangGraph para pausar en cada punto donde se necesita input del usuario. El estado se persiste en SQLite via `SqliteSaver`, usando el número de teléfono como `thread_id`.

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
               classify  (LLM → top 3 candidatos del catálogo)
                    │
                    ▼
          confirm_classification  (usuario elige 1, 2, 3 o "ninguno")
                    │
                    ▼
            collect_fields  ◀──────┐ (loop: pide campos faltantes uno a uno)
                    │              │
                    ▼              │
              confirmation         │
                    │              │
                    ▼              │
         process_confirmation      │
              │    │    │          │
              ▼    ▼    ▼          │
           save  edit  cancel      │
            │      │               │
            ▼      └───────────────┘
           END
```

### Detalle de cada nodo

| Nodo | Interrupt | Descripción |
|---|---|---|
| `greeting` | No | Busca perfil en BD por teléfono. Usuario existente → saluda por nombre y muestra tickets recientes. Usuario nuevo → pide nombre. |
| `register_user` | Sí | Recoge nombre. El LLM extrae nombre, área, turno, línea y rol del texto libre. Guarda `UserProfile` en BD. |
| `collect_description` | Sí | Pide descripción del problema. Soporta texto, audio (transcrito con Whisper) e imágenes (analizadas con GPT-4o Vision). Acumula `media_attachments`. |
| `classify` | No | Envía descripción + catálogo completo a GPT-4o-mini. Retorna JSON con top 3 candidatos (`code`, `name`, `confidence`, `reason`). Si falla el parse, pide más detalles. |
| `confirm_classification` | Sí | Muestra los 3 candidatos. Al seleccionar uno, auto-completa campos del catálogo (categoría, severidad, subcategoría, acción inmediata). Calcula `missing_fields`. |
| `collect_fields` | Sí | Loop: pide un campo faltante por iteración. Cuando `missing_fields` está vacío → pasa a confirmación. |
| `confirmation` | No | Genera resumen formateado del ticket. Pregunta: confirmar (1), editar (2) o cancelar (3). |
| `process_confirmation` | Sí | Interpreta respuesta del usuario. Enruta a `save`, `edit` o `__end__` (cancelación). |
| `edit` | Sí | Pregunta qué campo editar. Mapea nombres en español a nombres canónicos. Regresa a `collect_fields` con ese campo. |
| `save` | No | Crea `IncidentRecord`, persiste en BD con `IncidentRepository`. Guarda adjuntos multimedia. Actualiza perfil si hay datos nuevos (línea, turno). Retorna confirmación con folio. |

### Routing condicional (edges.py)

| Función | Desde | Hacia | Condición |
|---|---|---|---|
| `route_after_greeting` | `greeting` | `register_user` / `collect_description` | ¿Usuario nuevo o existente? |
| `route_after_register` | `register_user` | `register_user` / `collect_description` | ¿Se registró correctamente? |
| `route_after_classify` | `classify` | `confirm_classification` / `collect_description` | ¿Hay candidatos o falló? |
| `route_after_confirm_classification` | `confirm_classification` | `collect_fields` / `collect_description` / `confirm_classification` | ¿Seleccionó, dijo "ninguno", o no se entendió? |
| `route_after_collect_fields` | `collect_fields` | `collect_fields` / `confirmation` | ¿Quedan campos pendientes? |
| `route_after_process_confirmation` | `process_confirmation` | `save` / `edit` / `__end__` | ¿Confirmar, editar o cancelar? |
| `route_after_edit` | `edit` | `collect_fields` / `edit` | ¿Campo válido o reintentar? |

### Estado de la conversación (`ConversationState`)

```python
class ConversationState(TypedDict):
    messages: list[AnyMessage]          # Historial de mensajes LangChain
    user_phone: str                      # Teléfono del usuario (= thread_id)
    user_profile: Optional[dict]         # UserProfile serializado
    current_incident: dict               # Campos del ticket en construcción
    classification_candidates: list[dict] # Top 3 del LLM
    selected_code: Optional[str]         # Código seleccionado
    missing_fields: list[str]            # Campos pendientes por pedir
    current_field: Optional[str]         # Campo que se está pidiendo
    confirmed: Optional[bool]            # Decisión en confirmación
    current_node: str                    # Nodo actual (para routing)
    awaiting_input: Optional[str]        # Etiqueta del input esperado
    error: Optional[str]                 # Mensaje de error si hubo
    user_description: str                # Descripción original del usuario
    media_attachments: list[dict]        # [{bytes, filename, type, description}]
```

## Catálogo de incidentes

El catálogo se carga desde `catalog/Incidentes.xlsx` y define todos los tipos de tickets disponibles para clasificación.

**Columnas del Excel:**

| Columna | Descripción |
|---|---|
| Categoría | Grupo principal del ticket |
| Subcategoría | Tipo específico dentro de la categoría |
| Tipo de Ticket | Incidente, Alerta o Reclamo |
| Descripción corta | Texto del catálogo para el ticket |
| Severidad | Nivel de severidad (Alta, Media, etc.) |
| SLA sugerido | Tiempo de respuesta sugerido (4h, 8h, 24h) |
| Lleva imagen o documento? | Si aplica adjunto multimedia |

**Categorías del catálogo:**

| Categoría | Ejemplos de subcategoría |
|---|---|
| **Terminales / POS** | No enciende, se reinicia solo, congelado/lento, sin conexión, error al vender |
| **Impresoras / Tickets** | No imprime, tickets en blanco, no reconoce impresora |
| **Internet / Conectividad** | Sin internet, conexión intermitente, router dañado |
| **Electricidad / Energía** | Sin energía, variaciones de voltaje, UPS no funciona |
| **Equipos de Cómputo** | PC no enciende, falla de sistema operativo |
| **Local / Infraestructura** | Cristal roto, puerta/cerradura dañada |
| **Materiales / Suministros** | Papel térmico agotado |
| **Operación de Ventas** | No permite vender un juego, sorteo no disponible, venta fuera de horario, error en cálculo |
| **Pagos y Premios** | No permite pagar premio, diferencia en monto, ticket marcado como pagado, ticket no existe |
| **Contabilidad / Cuadres** | Descuadre de cierre diario, reporte de ventas incorrecto, comisiones incorrectas |
| **Seguridad / Fraude** | Ticket alterado, intento de cobro duplicado, venta fuera del sistema, robo, amenazas |
| **Reclamos de Clientes** | Jugó pero no salió ticket |

El LLM recibe el catálogo completo como contexto para clasificar la descripción del usuario en los top 3 candidatos más probables.

## Procesamiento multimedia

| Tipo | API | Modelo | Uso |
|---|---|---|---|
| **Audio** | OpenAI Whisper | `whisper-1` | Transcribe notas de voz a texto (idioma: español). Se usa como descripción del incidente. |
| **Imagen** | OpenAI Vision | `gpt-4o` | Analiza fotos en contexto de la agencia (equipos, daños, evidencia). La descripción se adjunta al ticket. |

Formatos soportados: OGG/Opus (WhatsApp nativo), MP3, M4A para audio; JPEG, PNG, WebP para imágenes.

Los archivos se guardan en `data/media/{incident_id}/{filename}` al persistir el ticket.

## Base de datos

SQLite con dos archivos separados:

| BD | Ruta | Contenido |
|---|---|---|
| **Principal** | `data/chatbot.db` | `users`, `incidents`, `incident_attachments`, `conversation_log` |
| **Checkpoints** | `data/checkpoints/langgraph.db` | Estado del grafo por thread (`checkpoints`, `writes`) |

### Tablas

- **`users`** — Perfil del operador (`phone_number` PK, `name`, `area`, `shift`, `role`)
- **`incidents`** — Ticket completo (código, nombre, categoría, severidad, tipo de ticket, SLA, agencia, descripción, estado)
- **`incident_attachments`** — Archivos adjuntos vinculados a un incidente (`file_path`, `media_type`, `description`)
- **`conversation_log`** — Historial de mensajes por `thread_id` (`role`, `content`, `created_at`)

## Comandos de WhatsApp

Los usuarios pueden enviar comandos directamente en el chat:

| Comando | Descripción |
|---------|-------------|
| `/reset` | Reinicia la conversación actual (borra checkpoints y log). |
| `/borrar` | Elimina tu perfil de usuario y reinicia el chat por completo. |
| `/eliminar_usuario` | Elimina solo tu perfil de la base de datos, sin afectar la conversación. |
| `/ayuda` | Muestra la lista de comandos disponibles. |

Cualquier mensaje que no empiece con `/` se procesa normalmente por el flujo conversacional. Los comandos desconocidos muestran un mensaje de error con referencia a `/ayuda`.

## Prompts (Jinja2)

| Template | Uso |
|---|---|
| `system.j2` | System prompt: define personalidad del bot, contexto de la operación, personalización con nombre/área/turno del usuario, historial reciente |
| `classify.j2` | Clasificación: inyecta catálogo completo + descripción del usuario, pide JSON con top 3 candidatos |
| `collect_field.j2` | Genera pregunta dinámica para un campo específico con descripción y ejemplo |
| `confirm.j2` | Formatea resumen del ticket para revisión del usuario |

## Estructura del proyecto

```
chat_demo/
├── main.py                        # Entry point (uvicorn en puerto 8000)
├── .env.example                   # Variables de entorno requeridas
├── pyproject.toml                 # Dependencias (Python >=3.13)
├── catalog/
│   └── Incidentes.xlsx            # Catálogo de tickets (agencias de lotería)
├── data/                          # Datos en runtime (gitignored)
│   ├── chatbot.db                 # BD principal
│   ├── checkpoints/langgraph.db   # Checkpoints del grafo
│   └── media/                     # Adjuntos multimedia por incidente
├── src/
│   ├── config.py                  # Rutas, API keys, modelos LLM
│   ├── models.py                  # Pydantic: UserProfile, IncidentRecord, enums
│   ├── db/
│   │   ├── engine.py              # Conexión SQLite, DDL (4 tablas), init_db()
│   │   └── repositories.py        # UserRepo, IncidentRepo, AttachmentRepo, ConversationLogRepo
│   ├── graph/
│   │   ├── builder.py             # StateGraph: 10 nodos, 7 conditional edges, compile()
│   │   ├── state.py               # ConversationState TypedDict
│   │   ├── nodes.py               # Lógica de los 10 nodos (interrupt, LLM calls, DB)
│   │   └── edges.py               # Funciones de routing condicional
│   ├── memory/
│   │   └── user_memory.py         # load_user_context(phone) → (profile, recent_incidents)
│   ├── media/
│   │   └── processor.py           # transcribe_audio(), analyze_image(), save_media_file()
│   ├── catalog/
│   │   └── parser.py              # parse_catalog() y load_catalog_text() desde Excel
│   ├── prompts/
│   │   ├── loader.py              # Jinja2 environment (render())
│   │   └── templates/
│   │       ├── system.j2          # System prompt personalizado
│   │       ├── classify.j2        # Clasificación con catálogo completo
│   │       ├── collect_field.j2   # Pregunta por campo específico
│   │       └── confirm.j2         # Resumen para confirmación
│   └── whatsapp/
│       ├── client.py              # send_text_message(), download_media(), parse_webhook_message()
│       ├── webhook.py             # FastAPI: GET/POST /webhook, POST /reset/{phone}
│       └── graph_adapter.py       # GraphAdapter: commands, threading, multimedia, greeting detection
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

4. Configurar el webhook en **Meta Developer Portal** apuntando a `https://<tu-dominio>/webhook`.

## Dependencias principales

- **LangGraph** + **LangChain** — Motor de conversación con estado persistente
- **langchain-openai** — Integración con GPT-4o-mini, GPT-4o Vision, Whisper
- **FastAPI** + **uvicorn** — Servidor HTTP para webhook
- **httpx** — Cliente HTTP async para WhatsApp Cloud API y descarga de media
- **openpyxl** — Lectura del catálogo Excel
- **Pydantic** — Validación de modelos de datos
- **Jinja2** — Renderizado de prompts
- **python-dotenv** — Carga de variables de entorno
