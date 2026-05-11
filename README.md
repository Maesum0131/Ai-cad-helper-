# AI CAD Helper

AI-powered site layout generator for civil engineers. Paste a spec document → get a fully editable CAD layout in seconds.

## Project Structure

```
ai-cad-helper/
├── frontend/
│   ├── editor.html       ← Full CAD editor (open directly in browser)
│   └── index.html        ← Landing page / marketing site
├── backend/
│   ├── main.py           ← FastAPI backend
│   └── requirements.txt
└── README.md
```

## Quick Start — Frontend Only (no backend needed)

Just open `frontend/editor.html` in your browser. The editor calls the Anthropic API directly from the browser.

Add your API key in `editor.html` — search for the `fetch('https://api.anthropic.com/v1/messages'` line and add:
```js
headers: {
  'Content-Type': 'application/json',
  'x-api-key': 'sk-ant-YOUR_KEY_HERE',
  'anthropic-version': '2023-06-01',
  'anthropic-dangerous-direct-browser-access': 'true'
}
```

## Full Stack Setup (Frontend + FastAPI Backend)

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE

# Start the server
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
API docs at: http://localhost:8000/docs

### 2. Frontend

Open `frontend/editor.html` directly, or serve with:
```bash
cd frontend
python -m http.server 3000
# Open http://localhost:3000/editor.html
```

To use the backend instead of direct API calls, update the fetch URL in `editor.html`:
```js
// Change:
fetch('https://api.anthropic.com/v1/messages', ...)
// To:
fetch('http://localhost:8000/api/generate', ...)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate` | Generate layout from text spec |
| POST | `/api/generate-from-pdf` | Upload PDF spec → layout |
| POST | `/api/edit` | Plain-English edit instruction |
| POST | `/api/export/dxf` | Export elements to DXF |
| GET | `/health` | Health check |

### Example API Call

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "2.4 acre commercial site C-2 zoning, 8500sf retail building, 42 parking spaces, detention pond SW corner, front setback 25ft"
  }'
```

## CAD Editor Features

- **AI Generate** — paste any spec, get a layout
- **Draw tools** — Rectangle (R), Circle (C), Line (L), Text (T)
- **Select & edit** — drag to move, handles to resize
- **Properties panel** — change type, dimensions, colors
- **Layers panel** — manage all elements
- **Snap to grid** — configurable (5/10/20/50 ft)
- **Undo/Redo** — full history (Ctrl+Z / Ctrl+Y)
- **Export** — SVG (renders anywhere) + DXF (AutoCAD ready)
- **Save/Load** — JSON project files

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| V | Select tool |
| R | Rectangle |
| C | Circle |
| L | Line |
| T | Text |
| Space | Pan |
| Del | Delete selected |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+D | Duplicate |
| Ctrl+A | Select all |
| Esc | Deselect |

## Deployment

**Fastest (Netlify):**
1. Drag the `frontend/` folder to [netlify.com/drop](https://netlify.com/drop)
2. Get a live URL instantly

**Backend (Railway/Render):**
1. Push to GitHub
2. Connect to [railway.app](https://railway.app) or [render.com](https://render.com)
3. Set `ANTHROPIC_API_KEY` environment variable
4. Deploy — auto-detects FastAPI

## Resume Description

> **Founder & Engineer — AI CAD Helper** | 2025  
> Built an AI-powered site layout generator for civil engineers. Paste a project specification → get a fully editable, dimensioned CAD site plan in under 30 seconds. Features a browser-based CAD editor with drag/resize, snap-to-grid, layer management, and DXF export for AutoCAD compatibility. Stack: FastAPI, Anthropic Claude API, vanilla JS canvas.  
> Live: [your-url] | GitHub: [your-repo]
