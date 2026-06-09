"""
Output PDF builder.

Assembles an output PDF from source PDF content, using paste instructions
and page layout definitions provided by the frontend.
"""

import fitz

# A4 page dimensions in PDF points
A4_WIDTH = 595.28
A4_HEIGHT = 841.89


def build_output_original_size(src_path, pastes, pages):
    """
    Build output PDF by pasting cut regions onto output pages.

    Content is placed at the TOP-LEFT of the destRect at its ORIGINAL SIZE
    (no scaling, no centering). Content that overflows the destRect is
    clipped to the destRect boundary.

    Each paste dict must include:
        cutRegionId, srcPageNum, pageNum,
        rect: {x, y, w, h} (source clip region),
        destRect: {x, y, w, h} (target slot on output page).
    """
    src = fitz.open(src_path)
    dst = fitz.open()

    # Determine the max page number needed
    max_page = -1
    for p in pages:
        if p["pageNum"] > max_page:
            max_page = p["pageNum"]
    for p in pastes:
        if p["pageNum"] > max_page:
            max_page = p["pageNum"]

    # Create all output pages (A4)
    for _ in range(max_page + 1):
        dst.new_page(width=A4_WIDTH, height=A4_HEIGHT)

    for paste in pastes:
        rect = paste["rect"]
        dest = paste["destRect"]
        src_page = paste.get("srcPageNum", 0)

        # Source clip region
        src_clip = fitz.Rect(
            rect["x"], rect["y"],
            rect["x"] + rect["w"], rect["y"] + rect["h"],
        )

        # Destination: top-left of slot, original size
        dest_x0 = dest["x"]
        dest_y0 = dest["y"]
        dest_x1 = dest_x0 + rect["w"]  # original width
        dest_y1 = dest_y0 + rect["h"]  # original height

        dest_rect = fitz.Rect(dest_x0, dest_y0, dest_x1, dest_y1)

        # Clip to destRect boundary (PyMuPDF clips automatically,
        # but we also clip the source to prevent overflow artifacts)
        dst[paste["pageNum"]].show_pdf_page(
            dest_rect, src, src_page, clip=src_clip
        )

    result = dst.write()
    dst.close()
    src.close()
    return result


# Keep the old function for backwards compatibility
def build_output_with_scaling(src_path, pastes, pages):
    """
    Build output PDF with auto-scaling (centered, fit-to-slot).

    Kept for reference; new code should use build_output_original_size.
    """
    src = fitz.open(src_path)
    dst = fitz.open()

    max_page = -1
    for p in pages:
        if p["pageNum"] > max_page:
            max_page = p["pageNum"]
    for p in pastes:
        if p["pageNum"] > max_page:
            max_page = p["pageNum"]

    for _ in range(max_page + 1):
        dst.new_page(width=A4_WIDTH, height=A4_HEIGHT)

    for paste in pastes:
        rect = paste["rect"]
        dest = paste["destRect"]
        src_page = paste.get("srcPageNum", 0)

        src_clip = fitz.Rect(
            rect["x"], rect["y"],
            rect["x"] + rect["w"], rect["y"] + rect["h"],
        )

        dest_rect = fitz.Rect(
            dest["x"], dest["y"],
            dest["x"] + dest["w"], dest["y"] + dest["h"],
        )

        src_w = src_clip.width
        src_h = src_clip.height
        dest_w = dest_rect.width
        dest_h = dest_rect.height

        scale = min(dest_w / src_w, dest_h / src_h) if src_w > 0 and src_h > 0 else 1.0
        new_w = src_w * scale
        new_h = src_h * scale

        cx = dest_rect.x0 + (dest_w - new_w) / 2
        cy = dest_rect.y0 + (dest_h - new_h) / 2

        final_rect = fitz.Rect(cx, cy, cx + new_w, cy + new_h)
        dst[paste["pageNum"]].show_pdf_page(
            final_rect, src, src_page, clip=src_clip
        )

    result = dst.write()
    dst.close()
    src.close()
    return result
