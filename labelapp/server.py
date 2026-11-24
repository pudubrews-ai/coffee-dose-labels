import io
import os
from contextlib import asynccontextmanager
from datetime import date
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from . import capabilities, config as C, designs, extract
from .designs.common import fmt_date, fmt_dose
from .printer import PrinterError, printer

MAX_UPLOAD = 25_000_000
STATIC = os.path.join(os.path.dirname(__file__), "static")


@asynccontextmanager
async def lifespan(app):
    capabilities.start()          # background; never blocks startup or page load
    yield
    await printer.disconnect()

app = FastAPI(title="Label Printer", lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])  # blocks DNS rebinding


class Label(BaseModel):
    design: str = "classic"
    roaster: str | None = None
    coffee_name: str | None = None
    origin: str | None = None
    region: str | None = None
    producer: str | None = None
    process: str | None = None
    variety: str | None = None
    altitude: str | None = None
    notes: str | None = None
    roast_date: str | None = None
    source_url: str | None = None
    dose: str | None = None
    seal_date: str | None = None
    copies: int = 1


class PrinterSel(BaseModel):
    id: str | None = None
    name: str | None = None


class UrlReq(BaseModel):
    url: str


def render_label(l: Label):
    try:
        return designs.render(l.design, l.model_dump())
    except KeyError:
        raise HTTPException(404, f"Unknown design {l.design!r}")


@app.get("/api/designs")
def list_designs():
    return {"designs": designs.listing(), "today": fmt_date(date.today())}


@app.get("/api/status")
async def status():
    s = await printer.status()
    s["selected"] = {"id": printer.selected_id, "name": printer.selected_name} if printer.selected_id else None
    return s


@app.get("/api/printers")
async def printers():
    try:
        found = await printer.scan(6.0)
    except Exception as e:
        return JSONResponse({"error": f"Bluetooth scan failed ({type(e).__name__}). Is Bluetooth on and allowed for this terminal?"}, status_code=502)
    return {"printers": found, "selected": printer.selected_id}


@app.get("/api/printer")
def current_printer():
    return {"id": printer.selected_id, "name": printer.selected_name}


@app.post("/api/printer/select")
async def select_printer(r: PrinterSel):
    try:
        await printer.select(r.id, r.name)
    except PrinterError as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    return {"id": printer.selected_id, "name": printer.selected_name}


@app.get("/api/capabilities")
async def caps(refresh: bool = False):
    return await capabilities.get(refresh)


async def require_extract():
    c = await capabilities.get()
    if not c["extract"]:
        c = await capabilities.get(refresh=True)      # cheap; picks up a fresh install or login
    if not c["extract"]:
        raise HTTPException(503, capabilities.MESSAGE)


@app.get("/api/print/progress")
def progress():
    return printer.progress


@app.post("/api/preview")
def preview(l: Label):
    im = render_label(l)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return Response(buf.getvalue(), media_type="image/png")


@app.post("/api/extract/url")
async def extract_url(r: UrlReq):
    await require_extract()
    try:
        return await extract.from_url(r.url.strip())
    except extract.ExtractError as e:
        return JSONResponse({"error": str(e)}, status_code=422)


@app.post("/api/extract/image")
async def extract_image(file: UploadFile = File(...)):
    await require_extract()
    raw = await file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD:
        return JSONResponse({"error": "Photo is too large (25 MB max)."}, status_code=413)
    try:
        return await extract.from_image(raw)
    except extract.ExtractError as e:
        return JSONResponse({"error": str(e)}, status_code=422)


@app.post("/api/print")
async def print_label(l: Label):
    if not fmt_dose(l.model_dump()):         # same parsing as the preview (accepts '17,5')
        raise HTTPException(400, "Dose in grams is required (a number above 0, up to 1000).")
    if not 1 <= l.copies <= 50:
        raise HTTPException(400, "Copies must be between 1 and 50.")
    im = render_label(l)
    try:
        return await printer.print_image(im, l.copies)
    except PrinterError as e:
        return JSONResponse({"error": str(e)}, status_code=502)


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"), headers={"Cache-Control": "no-store"})

app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=C.HOST, port=C.PORT, log_level="info")
