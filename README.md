<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/D3.js-7.9-F9A03C?style=for-the-badge&logo=d3dotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/Tailwind-3.4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" />
</p>

<h1 align="center">🎬 CineMatch AI</h1>

<p align="center">
  <strong>Motor de Recomendación Cinematográfica Conversacional impulsado por IA</strong>
</p>

<p align="center">
  <em>Describe lo que quieres ver en lenguaje natural. CineMatch AI entiende tu intención,<br/>
  consulta TMDB en tiempo real, y devuelve recomendaciones justificadas y personalizadas.</em>
</p>

---

<br/>

## 📖 Tabla de Contenidos

- [🌟 Visión General](#-visión-general)
- [🏗️ Arquitectura](#️-arquitectura)
- [🧠 Pipeline de IA — Las 7 Fases](#-pipeline-de-ia--las-7-fases)
- [🤖 Agentes Inteligentes](#-agentes-inteligentes)
- [🖥️ Frontend — React + D3.js](#️-frontend--react--d3js)
- [📡 API Reference](#-api-reference)
- [🚀 Quick Start](#-quick-start)
- [🐳 Docker (Producción)](#-docker-producción)
- [⚙️ Configuración](#️-configuración)
- [📁 Estructura del Proyecto](#-estructura-del-proyecto)
- [🧪 Testing](#-testing)
- [🔧 Detalles Técnicos](#-detalles-técnicos)
- [🗺️ Roadmap](#️-roadmap)

<br/>

---

<br/>

## 🌟 Visión General

**CineMatch AI** es un motor de recomendación cinematográfica que opera enteramente mediante **lenguaje natural**. No necesitas navegar por filtros, categorías o listas — simplemente describe lo que buscas:

> *"Quiero una película de ciencia ficción que haga pensar, tipo Arrival o Interstellar, pero europea"*

El sistema:

1. **Entiende** tu intención semántica con un LLM on-premise (Qwen3-30B)
2. **Busca** películas relevantes en TMDB en tiempo real
3. **Enriquece** cada candidata con datos detallados (keywords, reviews, runtime)
4. **Puntúa** y re-rankea con razonamiento del LLM
5. **Analiza** tu sentimiento e intención emocional
6. **Personaliza** las recomendaciones según tu perfil acumulado
7. **Narra** una respuesta conversacional justificada, streaming en tiempo real

### ✨ Características Principales

| Característica | Descripción |
|---|---|
| 🗣️ **Lenguaje Natural** | Habla como lo harías con un cinéfilo experto — en español o inglés |
| 🔄 **Conversación Multi-turno** | Refina tus preferencias: *"esa pero más oscura"*, *"algo más reciente"* |
| 📊 **Grafo Conceptual D3.js** | Visualización interactiva force-directed de películas, géneros, moods y keywords |
| 🧬 **Perfil Dinámico** | El sistema aprende tus gustos: géneros, estados de ánimo, arquetipos cinéfilos |
| ⚡ **Streaming SSE** | Las respuestas se muestran token a token en tiempo real |
| 🎯 **7 Agentes Especializados** | Pipeline modular con agentes de NLP, sentimiento, enriquecimiento, reranking, calidad de texto y perfil |
| 🎨 **Glassmorphism UI** | Frontend oscuro, translúcido y moderno con animaciones suaves |
| 🐳 **Docker Ready** | Un solo `docker compose up` levanta backend + frontend |

<br/>

---

<br/>

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        USUARIO (Browser)                         │
│                    http://localhost:3000                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Chat UI    │  │ Movie Cards  │  │  D3.js Force Graph     │  │
│  │  (React 18) │  │ (Glassmorphm)│  │  (Concept Map)         │  │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬────────────┘  │
│         │                │                       │               │
│         └────────────────┴───────────────────────┘               │
│                          │ SSE / REST                            │
└──────────────────────────┼───────────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────────┐
│                     BACKEND (FastAPI)                             │
│                   http://localhost:8000                           │
│                          │                                       │
│  ┌───────────────────────┴────────────────────────────────────┐  │
│  │                    Pipeline Orchestrator                    │  │
│  │                      (pipeline.py)                         │  │
│  │                                                            │  │
│  │  Phase 0 ──→ Sentiment Analysis                            │  │
│  │  Phase 1 ──→ NLP Entity Extraction ──→ Genre/Keyword IDs   │  │
│  │  Phase 1.5 → Profile Enrichment                            │  │
│  │  Phase 2 ──→ TMDB Query Builder ──→ Candidate Films        │  │
│  │  Phase 3 ──→ Data Enrichment (details + keywords + reviews)│  │
│  │  Phase 4 ──→ LLM Re-ranking (score + reason)              │  │
│  │  Phase 5 ──→ Top-N Selection                               │  │
│  │  Phase 6 ──→ Narrative Generation (streaming)              │  │
│  │  Phase 7 ──→ Text Quality Assurance                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                     │                    │                        │
│              ┌──────┴──────┐     ┌───────┴───────┐               │
│              │   vLLM      │     │     TMDB      │               │
│              │  (Qwen3-30B)│     │   (v3 API)    │               │
│              │  OpenAI API │     │  rate-limited  │               │
│              └─────────────┘     └───────────────┘               │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Sessions   │  │  Profiler   │  │  Text Post-Processor    │  │
│  │ (in-memory) │  │ (per-user)  │  │  (fix split/concat)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Stack Tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| **LLM** | Qwen3-30B-A3B-Instruct via vLLM | OpenAI-compatible API |
| **Backend** | Python / FastAPI / uvicorn | 3.11+ / 0.100+ |
| **HTTP Client** | httpx (async, SSL bypass) | 0.24+ |
| **Validación** | Pydantic v2 + pydantic-settings | 2.0+ |
| **Streaming** | sse-starlette (Server-Sent Events) | 1.6+ |
| **Datos de Cine** | TMDB API v3, OMDb, YouTube, Wikipedia | Rate-limited, cached, free |
| **Frontend** | Next.js / React / TypeScript | 14.2 / 18.3 / 5.5 |
| **Visualización** | D3.js (force-directed graph) | 7.9 |
| **Markdown** | react-markdown | 9.0 |
| **Estilos** | TailwindCSS + glassmorphism | 3.4 |
| **Contenedores** | Docker + Docker Compose | Multi-stage builds |

<br/>

---

<br/>

## 🧠 Pipeline de IA — Las 7 Fases

Cada consulta del usuario pasa por un pipeline de 7+ fases orquestado por `pipeline.py`. Todo es async y se ejecuta en segundos.

### Fase 0 — Análisis de Sentimiento

```
"¡Increíble, me encantó la recomendación! ¿Tienes algo más oscuro?"
                              ↓
         sentiment_score: 0.55 (very_positive)
         intents: ["gratitude", "explore"]
         emotional_signals: ["excitement"]
         detail_preference: "normal"
```

El agente de sentimiento (`sentiment.py`) analiza el mensaje usando un **léxico regex bilingüe** (español + inglés) con 4 niveles de intensidad. Detecta:

- **Sentimiento**: -1.0 (muy negativo) → +1.0 (muy positivo)
- **Intenciones**: refine, explore, specific, broad, gratitude
- **Señales emocionales**: excitement, curiosity, nostalgia, urgency, frustration
- **Preferencia de detalle**: brief, normal, verbose

Para mensajes ambiguos, puede escalar a un **análisis profundo vía LLM**.

### Fase 1 — Extracción NLP

```
"Quiero ciencia ficción cerebral de los 80s, tipo Blade Runner"
                              ↓
         genres: ["ciencia ficción"]
         keywords: ["cerebral", "distopía", "androides"]
         mood: "intelectual, oscuro"
         era: "80s"
         region: null
         exclude: []
```

El agente NLP (`nlp_extractor.py`) envía el mensaje al Qwen3-30B con un prompt estructurado que extrae entidades cinematográficas en formato JSON. Luego:

- Resuelve nombres de género (español/inglés) a **TMDB genre IDs** usando un mapa bidireccional
- Busca **keyword IDs** en TMDB con `search/keyword`
- Fusiona con el contexto previo si es una conversación multi-turno

### Fase 1.5 — Enriquecimiento con Perfil

```
         Profile: { tags: ["Explorador Cósmico"], top_genres: ["Sci-Fi", "Drama"] }
                              ↓
         entities enriquecidas + profile_hints para la narrativa
```

El agente de perfil (`profile_recommender.py`) cruza las entidades extraídas con el perfil acumulado del usuario para:

- Sugerir géneros favoritos si no se especificaron
- Aplicar el mood preferido por defecto
- Preparar contexto narrativo personalizado

### Fase 2 — Construcción de Query TMDB

El query builder (`query_builder.py`) traduce las entidades a parámetros del endpoint `/discover/movie` de TMDB:

- Mapea **eras** a rangos de fecha (`"80s"` → `1980-01-01 / 1989-12-31`)
- Resuelve **regiones** a códigos ISO (`"España"` → `ES`)
- Construye filtros: `with_genres`, `with_keywords`, `vote_average.gte`, `primary_release_date.gte/lte`
- Si discover no retorna resultados, hace fallback a `/search/movie`

### Fase 3 — Enriquecimiento de Datos

Para cada película candidata (top 10), el agente de enriquecimiento (`enrichment.py`) ejecuta **3 llamadas paralelas** a TMDB:

| Endpoint | Datos |
|----------|-------|
| `/movie/{id}` | Runtime, países de origen, géneros completos, sinopsis |
| `/movie/{id}/keywords` | Keywords temáticas |
| `/movie/{id}/reviews` | Mejor review (seleccionada por rating del reviewer) |

Resultado: un `EnrichedFilm` con todos los datos necesarios para el re-ranking inteligente.

### Fase 4 — Re-ranking con LLM

El re-ranker (`reranker.py`) envía **todas** las películas enriquecidas al LLM con la petición original del usuario y le pide:

```json
[
  {"id": 603, "score": 9.2, "reason": "Matrix es la quintaesencia del sci-fi cerebral..."},
  {"id": 78, "score": 8.7, "reason": "Blade Runner captura la atmósfera noir..."},
  ...
]
```

Cada película recibe una **puntuación de 0-10** y una **justificación** de por qué encaja (o no) con lo que el usuario pidió.

### Fase 5 — Selección Top-N

Se aplica la personalización de perfil: se **penalizan** películas ya recomendadas y se **boost**ean géneros favoritos. Se seleccionan las top-N películas (por defecto 3).

### Fase 6 — Generación Narrativa

El LLM genera una respuesta **conversacional en español** que:

- Presenta cada película con entusiasmo contextual
- Justifica por qué encaja con lo que el usuario pidió
- Usa markdown (negritas, cursivas) para estructura
- Se adapta al perfil del usuario si existe
- Se transmite **token a token** vía SSE

### Fase 7 — Aseguramiento de Calidad de Texto

El agente de calidad de texto (`text_quality.py`) actúa como **safety net** post-generación:

1. **Detección heurística**: Mide longitud media de palabras, transiciones mayúscula/minúscula, puntuación concatenada
2. **Corrección algorítmica**: Inserta espacios con regex en boundaries detectados + diccionario de palabras españolas comunes
3. **Reescritura LLM**: Si la corrección algorítmica no basta, envía el texto garbled al LLM para reescritura completa
4. **Verificación**: Compara antes/después para asegurar que el fix es una mejora

Además, el `text_processor.py` ejecuta un pipeline de 5 pasadas en cada respuesta:

```
raw text → fix split words → fix missing spaces → fix punctuation → fix markdown → cleanup
```

<br/>

---

<br/>

## 🤖 Agentes Inteligentes

El backend opera con un sistema de **7 agentes especializados**, cada uno con una responsabilidad única:

| Agente | Archivo | Tipo | Descripción |
|--------|---------|------|-------------|
| 🧠 **NLP Extractor** | `nlp_extractor.py` | LLM | Extrae géneros, keywords, mood, era, región del texto libre |
| 🔍 **Query Builder** | `query_builder.py` | Algorítmico | Traduce entidades a queries TMDB (discover + search fallback) |
| 📊 **Enrichment** | `enrichment.py` | API | Enriquece candidatas con details + keywords + reviews (parallel) |
| 🏆 **Re-ranker** | `reranker.py` | LLM | Puntúa películas y genera la narrativa conversacional |
| 💬 **Sentiment** | `sentiment.py` | Regex + LLM | Analiza sentimiento, intención y señales emocionales |
| 🧬 **Profile Recommender** | `profile_recommender.py` | Algorítmico | Personaliza query y ranking usando el perfil del usuario |
| 🎥 **OMDb/YouTube/Wikipedia** | `clients/omdb.py`, `clients/youtube.py`, `clients/wikipedia.py` | API | Ratings, trailers, trivia, Wikipedia |
| 🔧 **Text Quality** | `text_quality.py` | Regex + LLM | Detecta y corrige texto garbled (espacios faltantes/extra) |

### Flujo de Datos entre Agentes

```
User Query
    │
    ├──→ Sentiment Agent ──→ sentiment_label, intents, emotions
    │
    ├──→ NLP Extractor ──→ ExtractedEntities (genres, keywords, mood, era)
    │         │
    │         └──→ Profile Recommender ──→ enriched entities + hints
    │
    ├──→ Query Builder ──→ TMDB params ──→ raw movies
    │
    ├──→ Enrichment Agent ──→ EnrichedFilm[] (parallel API calls)
    │
    ├──→ Re-ranker Agent ──→ RankedFilm[] (scores + reasons)
    │         │
    │         └──→ Profile Recommender ──→ personalized ranking
    │
    ├──→ Re-ranker (Narrative) ──→ streaming narrative text
    │
    └──→ Text Quality Agent ──→ cleaned final text
```

<br/>

---

<br/>

## 🖥️ Frontend — React + D3.js

El frontend es una aplicación **Next.js 14** (App Router) con un diseño **glassmorphism** oscuro, optimizado para la experiencia conversacional.

### Componentes Principales

| Componente | Archivo | Descripción |
|-----------|---------|-------------|
| 🏠 **Chat Page** | `page.tsx` | Página principal con input, mensajes, sugerencias y controles |
| 🎬 **MovieCard** | `MovieCard.tsx` | Tarjeta de película con poster, score badge (gradiente por nota), hover shine, ratings, trailer, trivia, watchlist, compartir |
| 🗺️ **ForceGraph** | `ForceGraph.tsx` | Grafo D3.js force-directed con zoom, drag, tooltips, glow nodes |
| 🧬 **ProfileSidebar** | `ProfileSidebar.tsx` | Panel lateral con arquetipos, stats, barras de afinidad con gradiente |
| ⏳ **PhaseIndicator** | `PhaseIndicator.tsx` | Barra de progreso de las fases del pipeline con dots pulsantes |

### Diseño Visual

- **Glassmorphism**: Paneles translúcidos con `backdrop-filter: blur()` y bordes sutiles
- **Paleta oscura**: Background `#06080f`, surfaces `#0d1117`, cards `#161b22`
- **Accent gold**: Color principal `#f59e0b` (amber-500) con glow effects
- **Tipografía**: Inter / system-ui, con weights variables
- **Animaciones**: Fade-in, slide-up, slide-right, glow pulse, skeleton shimmer, card shine sweep
- **Responsive**: Adaptado para desktop, tablet y móvil

### Grafo Conceptual (D3.js)

El grafo force-directed muestra las **relaciones** entre:

| Tipo de Nodo | Color | Descripción |
|-------------|-------|-------------|
| 👤 User | `#f59e0b` | Nodo central del usuario con archetype tags |
| 🎬 Movie | `#60a5fa` | Películas recomendadas (hover para tooltip con detalle) |
| 🏷 Genre | `#34d399` | Géneros cinematográficos |
| 🔑 Keyword | `#a78bfa` | Keywords temáticas |
| 💫 Mood | `#f472b6` | Estados de ánimo |
| ⭐ Archetype | `#fb923c` | Arquetipos del perfil del usuario |

Features del grafo:
- **Zoom** (scroll wheel) + **Pan** (click & drag background)
- **Drag** de nodos individuales
- **Hover highlighting**: Resalta el nodo y sus conexiones, desvanece el resto
- **Hover link coloring**: Los links se colorean con el color del nodo activo
- **Outer rings**: Cada nodo tiene un anillo exterior sutil
- **Glow filters**: SVG filters por tipo de nodo para efecto luminoso
- **Legend**: Leyenda de colores en la esquina inferior

### Score Badge System

Las tarjetas de película muestran un badge de puntuación con **color dinámico** y ahora también:

- **Ratings multi-plataforma**: IMDb, Rotten Tomatoes, Metacritic
- **Botón de trailer**: Abre modal o YouTube
- **Trivia y Wikipedia**: Datos curiosos y enlace
- **Premios**: Badge si la película tiene premios
- **Botón Watchlist**: Guardar/quitar película
- **Botón Compartir**: Copia o comparte la recomendación

| Rango | Color | Significado |
|-------|-------|-------------|
| ≥ 8.0 | 🟢 Verde (emerald gradient) | Excelente match |
| ≥ 6.0 | 🟡 Ámbar (amber gradient) | Buen match |
| < 6.0 | 🔴 Rojo (red gradient) | Match parcial |

<br/>

---

<br/>

## 📡 API Reference

### Base URL

```
http://localhost:8000
```

### Endpoints

#### `POST /api/recommend` — Recomendación Principal

Acepta una consulta en lenguaje natural y devuelve recomendaciones justificadas.

**Request:**
```json
{
  "query": "Quiero una película de ciencia ficción que haga pensar",
  "session_id": "optional-uuid",
  "max_results": 3,
  "language": "es",
  "filters": {
    "min_year": 2000,
    "min_rating": 7.0
  }
}
```

**Response:**
```json
{
  "session_id": "a1b2c3d4-...",
  "narrative": "¡Gran elección! Aquí tienes tres joyas del sci-fi cerebral...",
  "recommendations": [
    {
      "tmdb_id": 603,
      "title": "Matrix",
      "year": 1999,
      "score": 9.2,
      "poster_url": "https://image.tmdb.org/t/p/w500/...",
      "reason": "Matrix es la quintaesencia del sci-fi cerebral...",
      "genres": ["Ciencia ficción", "Acción"],
      "keywords": ["realidad virtual", "distopía", "inteligencia artificial"]
    }
  ],
  "processing_time_ms": 4523
}
```

---

#### `POST /api/recommend/stream` — Streaming SSE

Mismo request que `/api/recommend`, pero devuelve **Server-Sent Events** con fases de progreso en tiempo real.

**Eventos SSE:**

| Evento | Data | Descripción |
|--------|------|-------------|
| `status` | `{"phase": "extracting"}` | Fase actual del pipeline |
| `recommendations` | `[{...}, ...]` | Array de películas recomendadas |
| `token` | `"texto "` | Token individual del narrative (streaming) |
| `narrative_replace` | `"texto corregido..."` | Reemplazo completo si el texto era garbled |
| `done` | `{"session_id": "..."}` | Pipeline completado |

Fases de status: `extracting` → `searching` → `enriching` → `ranking` → `narrating`

---

#### `GET /api/health` — Health Check

```json
{
  "status": "ok",
  "vllm": "ok",
  "tmdb": "ok",
  "vllm_models": ["Qwen3-30B-A3B-Instruct"],
  "tmdb_genres": 19
}
```

---

#### `POST /api/analyze/sentiment` — Análisis de Sentimiento

**Request:**
```json
{
  "text": "¡Me encantó la recomendación! ¿Algo más oscuro?"
}
```

**Response:**
```json
{
  "sentiment_score": 0.55,
  "sentiment_label": "very_positive",
  "intensity": "high",
  "intents": ["gratitude", "explore"],
  "detail_preference": "normal",
  "emotional_signals": ["excitement", "curiosity"]
}
```

---

#### `GET /api/profile/{session_id}` — Perfil de Usuario

```json
{
  "session_id": "a1b2c3d4-...",
  "profile": {
    "genre_affinity": {"Ciencia ficción": 8, "Drama": 5},
    "mood_affinity": {"intelectual": 6, "oscuro": 3},
    "archetype_tags": ["Explorador Cósmico", "Alma Sensible"],
    "interaction_count": 7,
    "avg_preferred_rating": 7.8,
    "liked_movies": [603, 78, 27205]
  }
}
```

---

#### `GET /api/graph/{session_id}` — Datos del Grafo D3.js

```json
{
  "nodes": [
    {"id": "user", "label": "Tú", "type": "user", "tags": ["Explorador Cósmico"]},
    {"id": "movie-603", "label": "Matrix", "type": "movie", "score": 9.2, "year": 1999},
    {"id": "genre-sci-fi", "label": "Ciencia ficción", "type": "genre"}
  ],
  "links": [
    {"source": "user", "target": "movie-603", "relation": "recomendada", "weight": 1.0},
    {"source": "movie-603", "target": "genre-sci-fi", "relation": "es_de", "weight": 0.8}
  ],
  "stats": {"total_nodes": 12, "total_links": 18, "movie_count": 3}
}
```

---

#### `GET /api/trailer/{tmdb_id}` — Trailer de la película

Devuelve la URL del trailer (YouTube/TMDB) y datos de embed.

#### `GET /api/watchlist/{session_id}` — Obtener watchlist
#### `POST /api/watchlist/{session_id}` — Añadir película a watchlist
#### `DELETE /api/watchlist/{session_id}/{tmdb_id}` — Quitar película de watchlist

#### `GET /api/export/{session_id}?format=json|markdown` — Exportar conversación y recomendaciones

<br/>

---

#### Otros Endpoints

| Method | Path | Descripción |
|--------|------|-------------|
| `GET` | `/api/session/{id}` | Obtener historial de sesión |
| `DELETE` | `/api/session/{id}` | Eliminar sesión |
| `POST` | `/api/sessions/cleanup` | Limpiar sesiones expiradas (TTL: 2h) |
| `POST` | `/api/graph/{session_id}` | Generar grafo con datos enriquecidos |
| `GET` | `/` | Redirect a frontend / info de API |
| `GET` | `/docs` | Documentación interactiva OpenAPI (Swagger) |

<br/>

---

<br/>

## 🚀 Quick Start

### Prerrequisitos

- **Python 3.11+**
- **Node.js 20+** (para el frontend)
- **Acceso a un servidor vLLM** con Qwen3-30B (o modelo compatible OpenAI API)
- **TMDB API Read Token** — [Obtener aquí](https://www.themoviedb.org/settings/api)

### Instalación Manual

```bash
# 1. Clonar el repositorio
git clone https://github.com/JLashN/CineMatch-AI.git
cd CineMatch-AI

# 2. Crear y activar entorno virtual
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 3. Instalar dependencias del backend
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus tokens:
#   VLLM_BASE_URL=http://tu-servidor-vllm:8000/v1
#   VLLM_MODEL=Qwen3-30B-A3B-Instruct
#   TMDB_API_READ_TOKEN=tu_token_aquí

# 5. Iniciar el backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# 6. En otra terminal — instalar y ejecutar el frontend
cd frontend
npm install
npm run dev
```

Abre **http://localhost:3000** para el chat, o **http://localhost:8000/docs** para la API interactiva.

<br/>

---

<br/>

## 🐳 Docker (Producción)

La forma más sencilla de ejecutar CineMatch AI en producción:

```bash
# 1. Configurar
cp .env.example .env
# Editar .env con VLLM_BASE_URL, VLLM_MODEL y TMDB_API_READ_TOKEN

# 2. Build + Run
docker compose up --build -d

# 3. Verificar
docker compose ps
curl http://localhost:8000/api/health
```

### Servicios Docker

| Servicio | Puerto | Imagen | Descripción |
|----------|--------|--------|-------------|
| `cinematch` | `:8000` | `python:3.11-slim` | Backend FastAPI (uvicorn) |
| `frontend` | `:3000` | `node:20-alpine` | Next.js (multi-stage build) |

### Docker Compose Features

- **Health checks**: Ambos servicios con healthcheck automático (30s interval)
- **Red interna**: `cinematch-net` bridge para comunicación frontend → backend
- **Restart policy**: `unless-stopped` para auto-recovery
- **Multi-stage builds**: El frontend usa 3 stages (deps → builder → runner) para imagen mínima
- **Environment injection**: El frontend recibe `NEXT_PUBLIC_API_URL=http://cinematch:8000` vía Docker networking

### Comandos Útiles

```bash
# Ver logs en tiempo real
docker compose logs -f

# Solo backend logs
docker compose logs -f cinematch

# Reconstruir un servicio
docker compose build frontend && docker compose up -d frontend

# Parar todo
docker compose down

# Parar y eliminar volúmenes
docker compose down -v
```

<br/>

---

<br/>

## ⚙️ Configuración

### Variables de Entorno

Todas las variables se cargan desde `.env` usando pydantic-settings:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `VLLM_BASE_URL` | `http://10.253.23.14:443/v1` | URL del servidor vLLM (OpenAI-compatible) |
| `VLLM_MODEL` | `Qwen3-30B-A3B-Instruct` | Nombre del modelo a usar |
| `TMDB_API_READ_TOKEN` | *(requerido)* | Bearer token de TMDB API v3 |
| `TMDB_BASE_URL` | `https://api.themoviedb.org/3` | URL base de TMDB |
| `TMDB_IMAGE_BASE` | `https://image.tmdb.org/t/p/w500` | URL base para posters |
| `APP_HOST` | `0.0.0.0` | Host del servidor |
| `APP_PORT` | `8000` | Puerto del servidor |
| `LOG_LEVEL` | `info` | Nivel de log (debug, info, warning, error) |
| `REDIS_URL` | `null` | URL de Redis (opcional, para cache distribuido) |
| `OMDB_API_KEY` | *(opcional)* | API key de OMDb para ratings (IMDb, Rotten, Metacritic) |
| `YOUTUBE_API_KEY` | *(opcional)* | API key de YouTube (solo si se desea usar búsqueda avanzada de trailers) |

### Ejemplo `.env`

```bash
VLLM_BASE_URL=http://mi-servidor-vllm:8000/v1
VLLM_MODEL=
TMDB_API_READ_TOKEN=
LOG_LEVEL=info
```

<br/>

---

<br/>

## 📁 Estructura del Proyecto

```
CineMatch-AI/
│
├── 📄 docker-compose.yml          # Orquestación de servicios
├── 📄 Dockerfile                   # Backend container (Python 3.11)
├── 📄 requirements.txt             # Dependencias Python
├── 📄 pyproject.toml               # Metadata del proyecto
├── 📄 .env.example                 # Plantilla de variables de entorno
├── 📄 .gitignore
│
├── 🐍 app/                         # ═══ BACKEND ═══
│   ├── __init__.py                 # Versión (1.0.0)
│   ├── __main__.py                 # Punto de entrada (python -m app)
│   ├── config.py                   # Settings (pydantic-settings, .env)
│   ├── models.py                   # Modelos Pydantic compartidos
│   ├── main.py                     # FastAPI app, endpoints, middleware
│   ├── pipeline.py                 # Orquestador del pipeline (7 fases)
│   ├── sessions.py                 # Gestor de sesiones in-memory (TTL 2h)
│   ├── profiler.py                 # Perfilado de usuario (regex + arquetipos)
│   ├── text_processor.py           # Post-procesamiento de texto (5 pasadas)
│   │
│   ├── 🔌 clients/                 # Clientes HTTP async
│   │   ├── __init__.py             # vLLM client (chat_completion, streaming)
│   │   ├── tmdb.py                 # TMDB client (cache, rate-limit, retry)
│   │   ├── omdb.py                 # OMDb client (ratings, trailers, trivia)
│   │   ├── youtube.py              # YouTube client (búsqueda de trailers)
│   │   └── wikipedia.py            # Wikipedia client (trivia, datos curiosos)
│   │
│   └── 🤖 agents/                  # Agentes del pipeline
│       ├── __init__.py
│       ├── nlp_extractor.py        # Fase 1: Extracción NLP (LLM → JSON)
│       ├── query_builder.py        # Fase 2: Constructor de queries TMDB
│       ├── enrichment.py           # Fase 3: Enriquecimiento paralelo
│       ├── reranker.py             # Fase 4+6: Re-ranking + Narrativa (LLM)
│       ├── sentiment.py            # Fase 0: Análisis de sentimiento (regex+LLM)
│       ├── profile_recommender.py  # Fase 1.5+5: Personalización por perfil
│       └── text_quality.py         # Fase 7: Aseguramiento de calidad (regex+LLM)
│
├── ⚛️  frontend/                    # ═══ FRONTEND ═══
│   ├── Dockerfile                  # Multi-stage build (deps→builder→runner)
│   ├── package.json                # Dependencias Node.js
│   ├── tsconfig.json               # TypeScript config (strict mode)
│   ├── tailwind.config.js          # Tailwind (dark palette, custom animations)
│   ├── postcss.config.js           # PostCSS pipeline
│   ├── next.config.js              # Next.js config (API rewrites)
│   ├── .env.local                  # Frontend env (API URL)
│   │
│   └── src/
│       ├── app/
│       │   ├── globals.css         # Glassmorphism, scrollbar, animations
│       │   ├── layout.tsx          # Root layout (metadata + fonts)
│       │   └── page.tsx            # Página principal del chat
│       │
│       ├── components/
│       │   ├── MovieCard.tsx       # Tarjeta de película (shine effect, score badge)
│       │   ├── ForceGraph.tsx      # Grafo D3.js (zoom, drag, glow, tooltips)
│       │   ├── ProfileSidebar.tsx  # Panel de perfil (slide-in, affinity bars)
│       │   └── PhaseIndicator.tsx  # Indicador de fases del pipeline
│       │
│       ├── lib/
│       │   └── api.ts             # Cliente API + SSE parser
│       │
│       └── types/
│           └── index.ts           # TypeScript interfaces
│
├── 🧪 tests/                       # ═══ TESTS ═══
│   ├── __init__.py
│   ├── test_nlp_extractor.py      # Tests del agente NLP
│   ├── test_query_builder.py      # Tests del query builder
│   ├── test_enrichment.py         # Tests del enriquecimiento
│   ├── test_reranker.py           # Tests del re-ranker
│   └── test_api.py                # Tests de la API (integration)
│
└── 📁 static/
    └── index.html                 # Legacy fallback HTML chat UI
```

<br/>

---

<br/>

## 🧪 Testing

```bash
# Activar el entorno virtual
source .venv/bin/activate

# Ejecutar todos los tests
pytest -v

# Ejecutar un test específico
pytest tests/test_nlp_extractor.py -v

# Con coverage
pytest --cov=app --cov-report=term-missing
```

### Estructura de Tests

| Test | Qué prueba |
|------|-----------|
| `test_nlp_extractor.py` | Extracción de entidades, resolución de genre IDs, parsing JSON |
| `test_query_builder.py` | Construcción de params TMDB, mapeo de eras, regiones |
| `test_enrichment.py` | Enriquecimiento paralelo, manejo de errores API |
| `test_reranker.py` | Re-ranking LLM, parsing de scores, fallback |
| `test_api.py` | Integration tests de los endpoints REST |

<br/>

---

<br/>

## 🔧 Detalles Técnicos

### vLLM Client

El cliente vLLM (`clients/__init__.py`) se conecta a cualquier servidor **OpenAI-compatible**:

- **Connection pooling**: Un solo `httpx.AsyncClient` compartido con reuse de conexiones
- **Timeouts**: Connect 10s, Read 120s (para generaciones largas), Write 10s
- **SSL bypass**: `verify=False` para servidores internos con certificados self-signed
- **Streaming**: `chat_completion_stream()` usa HTTP streaming con `async for line in response.aiter_lines()`
- **Token tracking**: Loguea `prompt_tokens` y `completion_tokens` de cada llamada

### TMDB Client

El cliente TMDB (`clients/tmdb.py`) implementa:

- **Cache in-memory**: Hash MD5 de (path + params) como key, TTL 1h para discover, 24h para genres
- **Rate limiting**: Respeta los headers de TMDB; retry automático en 429
- **Retry con backoff**: Hasta 3 reintentos con backoff exponencial
- **Endpoints**: `discover/movie`, `search/movie`, `search/keyword`, `movie/{id}`, `movie/{id}/keywords`, `movie/{id}/reviews`, `genre/movie/list`

### OMDb Client

El cliente OMDb (`clients/omdb.py`) permite obtener ratings y datos adicionales:

- **API Key**: Requiere una API key de OMDb (opcional)
- **Endpoints**: `http://www.omdbapi.com/?apikey=YOUR_API_KEY&t={title}`
- **Datos**: ratings de IMDb, Rotten Tomatoes, Metacritic, y información adicional de la película

### YouTube Client

El cliente YouTube (`clients/youtube.py`) permite buscar trailers:

- **API Key**: Requiere una API key de YouTube (opcional)
- **Búsqueda**: `youtube.search.list(q='{title} trailer', ...)`
- **Datos**: URL del trailer, título, descripción, canal

### Wikipedia Client

El cliente Wikipedia (`clients/wikipedia.py`) permite obtener trivia y datos curiosos:

- **Búsqueda**: `wikipedia.search('{title}')`
- **Resumen**: `wikipedia.summary('{title}', ...)`
- **Datos**: Extracto de la sinopsis, enlace a Wikipedia

### Gestión de Sesiones

- **In-memory store**: Dict de `session_id → SessionContext`
- **Auto-generación**: UUID v4 si no se proporciona session_id
- **TTL**: 2 horas de inactividad → eliminación automática
- **Multi-turno**: Las entidades de turnos anteriores se fusionan con las nuevas (`_merge_entities`)
- **Almacena**: query, narrative, entities, recommendations de cada turno

### Sistema de Perfilado

El profiler (`profiler.py`) construye un perfil dinámico por sesión:

- **Genre affinity**: Counter de géneros, +2 por interacción positiva
- **Keyword affinity**: Counter de keywords temáticas
- **Mood affinity**: Counter de moods detectados
- **Era/Director/Country**: Afinidades adicionales
- **Archetype tags**: Etiquetas computadas como "Explorador Cósmico", "Alma Sensible", "Buscador de Tensión", "Cazador de Risas", etc.
- **Liked/Disliked movies**: Historial de películas para evitar re-recomendaciones

### Post-procesamiento de Texto

El pipeline de limpieza de texto maneja dos problemas opuestos:

| Problema | Ejemplo | Solución |
|----------|---------|----------|
| Sílabas separadas | `pel í cula` | Regex iterativo que colapsa single-char splits |
| Palabras concatenadas | `mealegroque` | Regex que inserta espacios en boundaries + diccionario |
| Puntuación pegada | `algo,que` | Regex para spacing después de `,;:.!?` |
| Markdown roto | `** negrita**` | Normalización de markers markdown |

<br/>

---

<br/>

## 🗺️ Roadmap

- [x] **Watchlist** — Guardar películas para ver después
- [x] **Trailers** — Integración de YouTube/TMDB para mostrar trailers
- [x] **Trivia/curiosidades** — Wikipedia y facts automáticos
- [x] **Exportar conversación** — Descargar recomendaciones y chat en Markdown/JSON
- [ ] **Ratings** — Permitir al usuario puntuar recomendaciones para mejorar el perfil
- [ ] **Multi-modelo** — Soporte para múltiples LLMs (Qwen3, Llama, Mistral) con routing inteligente
- [ ] **Embeddings** — Búsqueda semántica por embeddings de sinopsis
- [ ] **Streaming de voz** — Integración con Whisper + TTS para interacción por voz
- [ ] **Modo colectivo** — Recomendaciones para grupos (intersección de perfiles)
- [ ] **PWA** — Progressive Web App para móvil con notificaciones

<br/>

---

<br/>

<p align="center">
  <strong>Hecho con ❤️ y 🎬 por <a href="https://github.com/JLashN">JLashN</a></strong>
</p>

<p align="center">
  <em>Si este proyecto te ha sido útil, ¡dale una ⭐ en GitHub!</em>
</p>
