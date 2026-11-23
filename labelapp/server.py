import io
import os
from contextlib import asynccontextmanager
from datetime import date
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from . import config as C, designs, extract
from .designs.common import fmt_date
from .printer import PrinterError, printer

STATIC = os.path.join(os.path.dirname(__file__), "static")


@asynccontextmanager
async def lifespan(app):
    yield
    await printer.disconnect()

app = FastAPI(title="Label Printer", lifespan=lifespan)


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
    return await printer.status()


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
    try:
        return await extract.from_url(r.url.strip())
    except extract.ExtractError as e:
        return JSONResponse({"error": str(e)}, status_code=422)


@app.post("/api/extract/image")
async def extract_image(file: UploadFile = File(...)):
    raw = await file.read(25_000_000)
    try:
        return await extract.from_image(raw)
    except extract.ExtractError as e:
        return JSONResponse({"error": str(e)}, status_code=422)


@app.post("/api/print")
async def print_label(l: Label):
    try:
        dose = float(l.dose or "")
        if dose <= 0: raise ValueError
    except ValueError:
        raise HTTPException(400, "Dose in grams is required.")
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
