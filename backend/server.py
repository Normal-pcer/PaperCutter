"""
FastAPI server for PaperCutter.

Provides REST API for PDF upload, auto-cut, output PDF building,
and page image rendering.
"""

import os
import uuid
import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import fitz

from cutter import auto_cut_content, auto_cut_image
from builder import build_output_original_size

app = FastAPI(title="PaperCutter API")

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


# ─── Request/Response Models ────────────────────────────────────────────

class RectModel(BaseModel):
    x: float
    y: float
    w: float
    h: float


class CutRegionResult(BaseModel):
    pageNum: int
    rect: RectModel


class AutoCutRequest(BaseModel):
    strategy: str = "content"  # "content" | "image"
    minGapRatio: float = 0.10
    dpi: int = 150
    whiteThresh: int = 250
    coverage: float = 0.995
    pageNum: int | None = None  # None = all pages, int = specific page


class PasteItemModel(BaseModel):
    cutRegionId: int
    srcPageNum: int
    pageNum: int
    rect: RectModel       # source clip rect
    destRect: RectModel   # target position on output page


class OutputPageModel(BaseModel):
    pageNum: int
    layoutId: str = "1up"


class BuildRequest(BaseModel):
    fileId: str
    pastes: list[PasteItemModel]
    pages: list[OutputPageModel]


# ─── Endpoints ──────────────────────────────────────────────────────────

@app.post("/api/pdf/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a source PDF. Returns fileId, page count, and page sizes."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    file_id = uuid.uuid4().hex
    dest = UPLOAD_DIR / f"{file_id}.pdf"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Gather page info
    try:
        doc = fitz.open(dest)
        pages = []
        for i, page in enumerate(doc):
            r = page.rect
            pages.append({
                "pageNum": i,
                "width": round(r.width, 2),
                "height": round(r.height, 2),
            })
        page_count = len(pages)
        doc.close()
    except Exception as e:
        raise HTTPException(500, f"Failed to read PDF: {e}")

    return {
        "fileId": file_id,
        "filename": file.filename,
        "pageCount": page_count,
        "pages": pages,
    }


@app.post("/api/auto-cut/{file_id}")
async def auto_cut(file_id: str, req: AutoCutRequest):
    """Run auto-cut on the uploaded PDF using the specified strategy."""
    src_path = UPLOAD_DIR / f"{file_id}.pdf"
    if not src_path.exists():
        raise HTTPException(404, "File not found")

    try:
        pg = req.pageNum  # None = all pages
        if req.strategy == "content":
            regions = auto_cut_content(str(src_path), req.minGapRatio, page_num=pg)
        elif req.strategy == "image":
            regions = auto_cut_image(
                str(src_path),
                req.minGapRatio,
                req.dpi,
                req.whiteThresh,
                req.coverage,
                page_num=pg,
            )
        else:
            raise HTTPException(400, f"Unknown strategy: {req.strategy}")
    except Exception as e:
        raise HTTPException(500, f"Auto-cut failed: {e}")

    return {"regions": regions}


@app.post("/api/build")
async def build_pdf(req: BuildRequest):
    """Build output PDF from paste instructions."""
    src_path = UPLOAD_DIR / f"{req.fileId}.pdf"
    if not src_path.exists():
        raise HTTPException(404, "Source file not found")

    pastes = [p.model_dump() for p in req.pastes]
    pages = [p.model_dump() for p in req.pages]

    try:
        pdf_bytes = build_output_original_size(str(src_path), pastes, pages)
    except Exception as e:
        raise HTTPException(500, f"Build failed: {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=output.pdf"},
    )


@app.get("/api/pdf/{file_id}/info")
async def pdf_info(file_id: str):
    """Get metadata for an uploaded PDF."""
    src_path = UPLOAD_DIR / f"{file_id}.pdf"
    if not src_path.exists():
        raise HTTPException(404, "File not found")

    doc = fitz.open(src_path)
    pages = []
    for i, page in enumerate(doc):
        r = page.rect
        pages.append({
            "pageNum": i,
            "width": round(r.width, 2),
            "height": round(r.height, 2),
        })
    doc.close()
    return {"fileId": file_id, "pageCount": len(pages), "pages": pages}


@app.get("/api/pdf/{file_id}/page/{page_num}/image")
async def render_page_image(file_id: str, page_num: int, dpi: int = 150):
    """Render a single PDF page as a PNG image."""
    src_path = UPLOAD_DIR / f"{file_id}.pdf"
    if not src_path.exists():
        raise HTTPException(404, "File not found")

    doc = fitz.open(src_path)
    if page_num < 0 or page_num >= len(doc):
        doc.close()
        raise HTTPException(404, "Page number out of range")

    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    doc.close()

    return Response(
        content=pix.tobytes("png"),
        media_type="image/png",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7652)
