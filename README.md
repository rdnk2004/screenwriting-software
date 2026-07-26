# Screenwriting Webapp

A full-stack screenplay writing, outlining, character analysis, network visualization, and export suite built with **Django REST Framework** and **React** (featuring **CodeMirror 6** and **React Flow**) for writing screenplays in [Fountain format](https://fountain.io/).

---

## Key Features

- ✍️ **Fountain Screenplay Editor**: Custom CodeMirror 6 editor with real-time Fountain syntax highlighting, automatic screenplay element formatting, intuitive keyboard shortcuts (`Tab`, `Enter`), and an inline screenwriting glossary drawer.
- 📁 **Multi-Format Upload & Import**: Import scripts via raw Fountain text, or upload existing screenplay files in `.fountain`, `.txt`, or Microsoft Word (`.docx`) formats.
- 📄 **Multi-Format Export**: Export industry-formatted screenplays to plaintext Fountain (`.fountain`), standard screenplay PDF (`.pdf` rendered via WeasyPrint), or Word document (`.docx`).
- 👥 **Character Management & Extraction**: Auto-extract characters directly from screenplay dialogue lines. Manage character bios, motivations, arc notes, voice guidelines, and visual attributes.
- 🕸️ **Interactive Character Network Diagram**: Visual node-edge graph powered by React Flow to map character relationships (Allies, Rivals, Romantic, Family) and co-appearances with persistent drag-and-drop coordinates.
- 🎯 **Beat Board & Story Outline**: Structure screenplays into beat cards and acts, link beats directly to script scenes, and track section scene counts and estimated page counts.
- 📊 **Screenplay Analytics**: Deep script metrics including dialogue balance percentages, character co-appearance matrix, dialogue exchange pairs, top locations breakdown, and estimated page counts.

---

## Prerequisites

- **Python**: 3.11+
- **Node.js**: 18+
- **Database**: PostgreSQL (default) or SQLite (for local development)

---

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# (Optional) Use SQLite for local development
set DB_ENGINE=sqlite            # Windows (CMD)
# $env:DB_ENGINE="sqlite"       # Windows (PowerShell)
# export DB_ENGINE=sqlite       # macOS / Linux

# Run database migrations
python manage.py migrate

# (Optional) Run backend tests
python manage.py test scripts

# Start the Django development server
python manage.py runserver
```

The Django REST API will be available at **`http://localhost:8000/api/`**.

#### PostgreSQL Configuration (Default)

| Env Variable | Default |
|--------------|---------|
| `DB_NAME` | `screenwriter` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | *(empty)* |
| `DB_HOST` | `localhost` |
| `DB_PORT` | `5432` |

Create the database before running migrations:
```sql
CREATE DATABASE screenwriter;
```

---

### 2. Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```

The application UI will be available at **`http://localhost:3000`** (or `http://localhost:5173`).

---

## Frontend Routes

| Path | View Component | Description |
|------|----------------|-------------|
| `/` | `ScriptList.jsx` | Dashboard to view, create, upload, and delete scripts |
| `/scripts/:id` | `ScriptEditor.jsx` | CodeMirror 6 screenplay editor with glossary drawer |
| `/scripts/:id/characters` | `ScriptCharacters.jsx` | Character management and auto-extraction tool |
| `/scripts/:id/diagram` | `ScriptDiagram.jsx` | React Flow interactive character relationship graph |
| `/scripts/:id/outline` | `ScriptOutline.jsx` | Beat board and scene-linked story outline |
| `/scripts/:id/analysis` | `ScriptAnalysis.jsx` | Script statistics, dialogue balance, and location metrics |

---

## API Reference

### Scripts & Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/scripts/` | List all scripts |
| `POST` | `/api/scripts/` | Create a new script |
| `POST` | `/api/scripts/upload/` | Upload screenplay file (`.fountain`, `.txt`, `.docx`) |
| `GET` | `/api/scripts/:id/` | Get script details with nested scenes & lines |
| `PATCH` | `/api/scripts/:id/` | Update script metadata (e.g. title) |
| `DELETE` | `/api/scripts/:id/` | Delete a script |
| `POST` | `/api/scripts/:id/import_fountain/` | Replace script scenes/lines from Fountain text |
| `GET` | `/api/scripts/:id/export_fountain/` | Export script as plaintext Fountain |
| `GET` | `/api/scripts/:id/export_pdf/` | Export script as formatted PDF |
| `GET` | `/api/scripts/:id/export_word/` | Export script as Word document (`.docx`) |
| `POST` | `/api/scripts/:id/extract_characters/` | Auto-extract characters from script lines |
| `GET` | `/api/scripts/:id/analysis/` | Get dialogue balance, location counts, & act breakdowns |
| `GET` | `/api/scripts/:id/extraction/` | Get character co-appearances & dialogue exchanges |

### Characters & Relationships

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/api/characters/?script=:id` | List or create characters for a script |
| `PATCH/DELETE` | `/api/characters/:id/` | Update (bio, notes, graph coords) or delete character |
| `GET/POST` | `/api/relationships/?script=:id` | List or create character relationships |
| `PATCH/DELETE` | `/api/relationships/:id/` | Update or delete a relationship |

### Story Outline & Script Elements

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/api/beats/?script=:id` | List or create beat board outline items |
| `PATCH/DELETE` | `/api/beats/:id/` | Update (name, order, linked scene) or delete a beat |
| `GET/POST/PATCH/DELETE` | `/api/scenes/` | CRUD operations on screenplay scenes |
| `GET/POST/PATCH/DELETE` | `/api/lines/` | CRUD operations on screenplay lines |

---

## Editor Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Tab** | Cycle current line's screenplay element type (*Scene Heading → Action → Character → Dialogue → Parenthetical → Transition*) |
| **Enter** | Insert newline following screenplay conventions (e.g., Character → Dialogue, Dialogue → Action) |
| **Ctrl+S** / **Cmd+S** | Save screenplay changes (syncs Fountain text with backend) |

---

## Fountain Element Auto-formatting Rules

- **Scene Headings** — Recognized by `INT.`, `EXT.`, `INT./EXT.` prefix or forced with a leading dot `.`.
- **Character Cues** — ALL-CAPS single line text preceding dialogue.
- **Parentheticals** — Enclosed in parentheses `(text)` immediately following a character cue or dialogue line.
- **Dialogue** — Text immediately following a character cue or parenthetical line.
- **Transitions** — Recognized as ALL-CAPS ending in `TO:` or forced with a leading `>`.

---

## Project Structure

```
screenwriting-software/
├── README.md
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── screenwriter/            # Django project config (settings, urls, wsgi)
│   └── scripts/                 # Core screenwriting Django app
│       ├── models.py            # Script, Scene, Line, Character, Relationship, Beat
│       ├── serializers.py       # DRF serializers & character name normalization
│       ├── views.py             # ViewSets, analysis engine, import/export actions
│       ├── urls.py              # Router configuration
│       ├── fountain.py          # Fountain syntax parser & serializer
│       ├── exporter.py          # WeasyPrint PDF & python-docx Word exporters
│       ├── upload.py            # Screenplay file upload handler (.fountain, .txt, .docx)
│       └── tests.py             # Test suite for parser, exporter, & endpoints
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── main.jsx             # React entry point
        ├── App.jsx              # React Router configuration
        ├── api.js               # Axios API client functions
        ├── index.css            # Global CSS styling
        ├── components/
        │   └── GlossaryDrawer.jsx # Screenwriting term reference drawer
        ├── editor/
        │   ├── FountainEditor.jsx # CodeMirror 6 integration
        │   └── fountainMode.js    # Fountain syntax parser/highlighter extension
        └── pages/
            ├── ScriptList.jsx      # Script dashboard & file upload
            ├── ScriptEditor.jsx    # Screenplay editor page
            ├── ScriptCharacters.jsx# Character bios & auto-extraction page
            ├── ScriptDiagram.jsx   # Interactive character relationship network page
            ├── ScriptOutline.jsx   # Beat board & story outline page
            └── ScriptAnalysis.jsx  # Analytics & statistics breakdown page
```
