# Screenwriting Webapp

Django + Postgres backend with a React/CodeMirror 6 frontend for writing screenplays in Fountain format.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (or use SQLite for local dev — see below)

---

## Backend Setup

```bash
cd backend

# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Use SQLite instead of Postgres
set DB_ENGINE=sqlite            # Windows
# export DB_ENGINE=sqlite       # macOS/Linux

# 4. Run migrations
python manage.py migrate

# 5. Start the dev server
python manage.py runserver
```

The API will be available at http://localhost:8000/api/

### Postgres config (default)

| Env var | Default |
|---------|---------|
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

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at http://localhost:3000

---

## API Reference

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/scripts/` | List all scripts |
| POST | `/api/scripts/` | Create a script |
| GET | `/api/scripts/:id/` | Get script with nested scenes/lines |
| PATCH | `/api/scripts/:id/` | Update script title |
| DELETE | `/api/scripts/:id/` | Delete script |
| POST | `/api/scripts/:id/import_fountain/` | Replace scenes/lines from Fountain text |
| GET | `/api/scripts/:id/export_fountain/` | Get script as Fountain plaintext |
| GET/POST/PATCH/DELETE | `/api/scenes/` | CRUD on scenes |
| GET/POST/PATCH/DELETE | `/api/lines/` | CRUD on lines |

---

## Editor Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Tab** | Cycle current line's element type (scene heading → action → character → dialogue → parenthetical → transition → …) |
| **Enter** | Insert newline; next line type follows screenplay convention (after character → dialogue, after dialogue → action, etc.) |
| **Ctrl+S** / **Cmd+S** | Save (sends Fountain text to `import_fountain` endpoint) |

---

## Fountain Element Auto-formatting

- **Scene headings** — auto-uppercased; recognized by `INT.`/`EXT.` prefix or forced with leading `.`
- **Character cues** — auto-uppercased; recognized as ALL-CAPS single line
- **Transitions** — recognized as ALL-CAPS ending in `TO:` or forced with leading `>`
- **Parentheticals** — recognized as `(text)` after a character/dialogue line
- **Dialogue** — any text immediately following a character/parenthetical

---

## Project Structure

```
backend/
  manage.py
  requirements.txt
  screenwriter/         Django project
    settings.py
    urls.py
  scripts/              Django app
    models.py           Script, Scene, Line models
    serializers.py      DRF serializers
    views.py            ViewSets + import/export actions
    urls.py             Router config
    fountain.py         Fountain parser + serializer
    migrations/

frontend/
  package.json
  vite.config.js
  src/
    main.jsx
    App.jsx
    api.js              Axios wrappers
    index.css
    pages/
      ScriptList.jsx
      ScriptEditor.jsx
    editor/
      FountainEditor.jsx  CodeMirror 6 wrapper
      fountainMode.js     Fountain CM6 extension
```
