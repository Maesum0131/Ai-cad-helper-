"""
AI CAD Helper — FastAPI Backend
Run: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import anthropic
import json
import io
import os

app = FastAPI(title="AI CAD Helper API", version="1.0.0")

# CORS — allow the frontend to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # lock down in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend files
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# ──────────────────────────────────────────────
# MODELS
# ──────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    site_width: Optional[int] = 600    # feet
    site_height: Optional[int] = 450   # feet

class UpdateRequest(BaseModel):
    elements: list
    instruction: str   # plain-English edit command


# ──────────────────────────────────────────────
# SYSTEM PROMPT
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are a civil engineering CAD layout AI. Given a project specification or site description, generate a JSON array of site plan elements.

Return ONLY valid JSON — no markdown, no backticks, no explanation. Use this exact structure:
{
  "elements": [
    {
      "type": "rect",           // rect | circle | line | text-label
      "elType": "building",     // building | road | parking | pond | setback | utility | greenspace | label | generic
      "x": 80,                  // left edge in feet from origin
      "y": 60,                  // top edge in feet from origin
      "w": 200,                 // width in feet (rect only)
      "h": 140,                 // height in feet (rect only)
      "label": "BUILDING",
      "sublabel": "8,500 SF",
      "fill": "#1e3a5f",
      "stroke": "#3b82f6",
      "dashed": false
    }
  ],
  "metadata": {
    "site_area_acres": 2.4,
    "total_building_sf": 8500,
    "parking_spaces": 42,
    "notes": "Front setback 25ft per C-2 zoning"
  }
}

Element type rules:
- rect: x, y, w, h required. For site boundary use elType "setback" with fill "transparent" and dashed true.
- circle (ponds/roundabouts): x, y are top-left of bounding box. Also include cx=x+r, cy=y+r, r, w=r*2, h=r*2
- line (utilities/roads centerlines): x, y, x2, y2. Add dashed:true for underground utilities, arrow:true for flow direction
- text-label: x, y, label, fontSize (8-14), color

Scale and layout rules:
- 1 unit = 1 foot
- Default site: ~600ft wide × 450ft tall for a 2-4 acre site. Scale proportionally for larger/smaller sites.
- Start all layouts at x=20, y=20 with a site boundary rect
- Inside boundary: add setback line (dashed) offset 25-30ft inside boundary
- Then place major elements: building, parking, roads, pond, utilities
- Add dimension labels (text-label elements) showing key measurements
- Always add a north arrow text-label at top-right: {"type":"text-label","elType":"label","x":550,"y":25,"label":"N ↑","fontSize":14,"color":"#3b82f6"}
- Add a scale bar text-label at bottom: {"type":"text-label","elType":"label","x":25,"y":430,"label":"SCALE: 1\" = 40'","fontSize":9,"color":"#94a3b8"}

Color palette (dark engineering theme):
- building: fill=#1e3a5f stroke=#3b82f6
- road: fill=#1a2030 stroke=#6b7280
- parking: fill=#172030 stroke=#4b5563
- pond/water: fill=#0d2b1e stroke=#10b981
- setback (dashed): fill=transparent stroke=#facc15
- utility line: stroke=#8b5cf6 dashed=true
- greenspace: fill=#0f2a15 stroke=#22c55e
- labels: color=#94a3b8

Generate 10-18 elements for a complete realistic preliminary site plan."""


EDIT_PROMPT = """You are a civil engineering CAD editor. The user has an existing site plan and wants to make a specific change.

You will receive:
1. Current elements as JSON
2. A plain-English instruction

Return ONLY the complete updated elements array as JSON:
{"elements": [...]}

Apply only the requested change. Preserve all other elements and their exact properties.
Common edits:
- "move X to southwest corner" → update x,y of matching element
- "make building bigger" → increase w,h proportionally
- "add a road along north boundary" → add new road rect
- "rotate parking 90 degrees" → swap w and h
- "remove the pond" → filter out pond elements"""


# ──────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse("../frontend/editor.html")


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/generate")
async def generate_layout(req: GenerateRequest):
    """Generate a site layout from a text specification."""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Generate a complete site plan for:\n\n{req.prompt}\n\nSite canvas: {req.site_width}ft × {req.site_height}ft"
            }]
        )

        raw = message.content[0].text
        # Strip any accidental markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)

        # Assign IDs server-side
        for i, el in enumerate(data.get("elements", [])):
            el["id"] = f"el_{i+1}"

        return JSONResponse(content=data)

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-from-pdf")
async def generate_from_pdf(file: UploadFile = File(...)):
    """Upload a PDF spec document and generate a site layout."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    contents = await file.read()
    import base64
    b64 = base64.standard_b64encode(contents).decode("utf-8")

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": b64
                        }
                    },
                    {
                        "type": "text",
                        "text": "Generate a complete site plan from this specification document."
                    }
                ]
            }]
        )

        raw = message.content[0].text.replace("```json","").replace("```","").strip()
        data = json.loads(raw)
        for i, el in enumerate(data.get("elements", [])):
            el["id"] = f"el_{i+1}"

        return JSONResponse(content=data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/edit")
async def edit_layout(req: UpdateRequest):
    """Apply a plain-English edit instruction to an existing layout."""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=EDIT_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Current elements:\n{json.dumps(req.elements, indent=2)}\n\nInstruction: {req.instruction}"
            }]
        )

        raw = message.content[0].text.replace("```json","").replace("```","").strip()
        data = json.loads(raw)
        return JSONResponse(content=data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export/dxf")
async def export_dxf(elements: list):
    """Convert elements to DXF format server-side."""
    dxf = "0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n"

    for el in elements:
        layer = el.get("elType", "0")
        if el["type"] == "rect":
            x, y, w, h = el["x"], el["y"], el["w"], el["h"]
            dxf += f"0\nLWPOLYLINE\n8\n{layer}\n90\n4\n70\n1\n"
            for px, py in [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]:
                dxf += f"10\n{px}\n20\n{-py}\n"
        elif el["type"] == "line":
            dxf += f"0\nLINE\n8\n{layer}\n10\n{el['x']}\n20\n{-el['y']}\n11\n{el['x2']}\n21\n{-el['y2']}\n"
        elif el["type"] == "circle":
            dxf += f"0\nCIRCLE\n8\n{layer}\n10\n{el.get('cx',el['x'])}\n20\n{-el.get('cy',el['y'])}\n40\n{el['r']}\n"
        elif el["type"] == "text-label":
            dxf += f"0\nTEXT\n8\n0\n10\n{el['x']}\n20\n{-el['y']}\n40\n{el.get('fontSize',12)}\n1\n{el.get('label','')}\n"

    dxf += "0\nENDSEC\n0\nEOF"
    return {"dxf": dxf}


# ──────────────────────────────────────────────
# RUN
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
