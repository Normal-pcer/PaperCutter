"""
Auto-cut strategies for detecting content regions in PDF pages.

Refactored from main.py — these now return lists of region dicts
instead of writing output PDFs directly.
"""

import fitz
import numpy as np


def merge_rects(rects, gap=5):
    """Merge overlapping or nearby rectangles."""
    if not rects:
        return []
    rects = sorted(rects, key=lambda r: (r.y0, r.x0))
    merged = [rects[0]]
    for r in rects[1:]:
        last = merged[-1]
        if (
            r.y0 <= last.y1 + gap
            and r.x0 <= last.x1 + gap
            and r.x1 >= last.x0 - gap
        ):
            merged[-1] = fitz.Rect(
                min(last.x0, r.x0),
                min(last.y0, r.y0),
                max(last.x1, r.x1),
                max(last.y1, r.y1),
            )
        else:
            merged.append(r)
    return merged


def auto_cut_content(src_path, min_gap_ratio=0.10, page_num=None):
    """
    Content-recognition strategy: uses text blocks, images, and drawings
    to find content regions, then splits by vertical whitespace gaps.

    If page_num is provided, only processes that specific page.
    Otherwise processes all pages.

    Returns a list of {pageNum, rect: {x, y, w, h}} dicts.
    """
    src = fitz.open(src_path)
    regions = []

    pages_to_process = [src[page_num]] if page_num is not None else src
    for page in pages_to_process:
        page_height = page.rect.height

        blocks = page.get_text("blocks")
        rects = []
        for b in blocks:
            text = b[4]
            if not text.strip():
                continue
            y0 = b[1]
            stripped = text.strip()
            # Skip page numbers (bottom of page, digits only)
            if y0 > page_height * 0.88 and stripped.isdigit():
                continue
            rects.append(fitz.Rect(b[:4]))

        page_area = page.rect.width * page_height
        for img in page.get_image_info():
            r = fitz.Rect(img["bbox"])
            if abs(r.get_area()) < page_area * 0.95:
                rects.append(r)
        for d in page.get_drawings():
            r = fitz.Rect(d["rect"])
            area = abs(r.get_area())
            if area >= page_area * 0.95:
                continue
            if area < 5:
                continue
            rects.append(r)

        if not rects:
            continue

        rects = merge_rects(rects, gap=5)
        rects.sort(key=lambda r: r.y0)

        min_gap = page_height * min_gap_ratio

        # Group by vertical whitespace
        groups = []
        current_group = [rects[0]]
        for i in range(1, len(rects)):
            g = rects[i].y0 - current_group[-1].y1
            if g >= min_gap:
                groups.append(current_group)
                current_group = [rects[i]]
            else:
                current_group.append(rects[i])
        groups.append(current_group)

        for group in groups:
            x0 = min(r.x0 for r in group)
            y0 = min(r.y0 for r in group)
            x1 = max(r.x1 for r in group)
            y1 = max(r.y1 for r in group)

            h = y1 - y0
            if h < 15:
                continue

            regions.append(
                {
                    "pageNum": page.number,
                    "rect": {
                        "x": float(round(x0, 2)),
                        "y": float(round(y0, 2)),
                        "w": float(round(x1 - x0, 2)),
                        "h": float(round(h, 2)),
                    },
                }
            )

    src.close()
    return regions


def auto_cut_image(
    src_path, min_gap_ratio=0.10, dpi=150, white_thresh=250, coverage=0.995,
    page_num=None,
):
    """
    Image-processing strategy: renders each page as an image and uses
    pixel analysis to find white-space gaps between content regions.

    If page_num is provided, only processes that specific page.
    Otherwise processes all pages.

    Returns a list of {pageNum, rect: {x, y, w, h}} dicts.
    """
    src = fitz.open(src_path)
    regions = []

    pages_to_process = [src[page_num]] if page_num is not None else src
    for page in pages_to_process:
        pix = page.get_pixmap(dpi=dpi)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )

        if pix.n >= 3:
            is_white_px = np.all(img[:, :, :3] >= white_thresh, axis=2)
        else:
            is_white_px = img[:, :, 0] >= white_thresh

        white_ratio = np.mean(is_white_px, axis=1)
        is_white_row = white_ratio >= coverage

        scale_y = page.rect.height / pix.height
        scale_x = page.rect.width / pix.width
        min_gap_px = int(pix.height * min_gap_ratio)

        # Find continuous white row gaps
        gaps = []
        in_gap = False
        gap_start = 0
        for i, w in enumerate(is_white_row):
            if w and not in_gap:
                gap_start = i
                in_gap = True
            elif not w and in_gap:
                if i - gap_start >= min_gap_px:
                    gaps.append((gap_start, i))
                in_gap = False
        if in_gap and pix.height - gap_start >= min_gap_px:
            gaps.append((gap_start, pix.height))

        # Content intervals = regions between gaps
        content_ys = []
        prev_end = 0
        for gs, ge in gaps:
            if gs > prev_end:
                content_ys.append((prev_end, gs))
            prev_end = ge
        if prev_end < pix.height:
            content_ys.append((prev_end, pix.height))

        for row_start, row_end in content_ys:
            block_mask = ~is_white_px[row_start:row_end, :]
            col_has_content = np.any(block_mask, axis=0)
            content_cols = np.where(col_has_content)[0]
            if len(content_cols) == 0:
                continue

            pad = int(5 * dpi / 72)
            col0 = max(0, content_cols[0] - pad)
            col1 = min(pix.width, content_cols[-1] + 1 + pad)
            row0 = max(0, row_start - pad)
            row1 = min(pix.height, row_end + pad)

            src_y0 = row0 * scale_y
            src_y1 = row1 * scale_y
            src_x0 = col0 * scale_x
            src_x1 = col1 * scale_x

            h = src_y1 - src_y0
            w = src_x1 - src_x0
            if h < 15:
                continue
            if src_y0 > page.rect.height * 0.85 and w < 50:
                continue

            regions.append(
                {
                    "pageNum": page.number,
                    "rect": {
                        "x": float(round(src_x0, 2)),
                        "y": float(round(src_y0, 2)),
                        "w": float(round(w, 2)),
                        "h": float(round(h, 2)),
                    },
                }
            )

    src.close()
    return regions
