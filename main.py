import fitz  # PyMuPDF
import numpy as np

def merge_rects(rects, gap=5):
    """合并重叠或靠近的矩形"""
    if not rects:
        return []
    rects = sorted(rects, key=lambda r: (r.y0, r.x0))
    merged = [rects[0]]
    for r in rects[1:]:
        last = merged[-1]
        if r.y0 <= last.y1 + gap and r.x0 <= last.x1 + gap and r.x1 >= last.x0 - gap:
            merged[-1] = fitz.Rect(
                min(last.x0, r.x0), min(last.y0, r.y0),
                max(last.x1, r.x1), max(last.y1, r.y1)
            )
        else:
            merged.append(r)
    return merged


def split_by_whitespace(src_pdf, dst_pdf, min_gap_ratio=0.10):
    """
    将 src_pdf 每一页按垂直方向大于页高指定比例的空白切分，
    每部分放到一个 A4 页面，保存为 dst_pdf。
    """
    src = fitz.open(src_pdf)
    dst = fitz.open()
    a4 = fitz.Rect(0, 0, 595.28, 841.89)

    for page in src:
        page_height = page.rect.height

        blocks = page.get_text("blocks")
        rects = []
        for b in blocks:
            text = b[4]
            # 跳过空白块（只有不可见字符的块，即题目间空白）
            if not text.strip():
                continue
            # 跳过页码块（页面底部、内容仅为数字）
            y0 = b[1]
            stripped = text.strip()
            if y0 > page_height * 0.88 and stripped.isdigit():
                continue
            rects.append(fitz.Rect(b[:4]))

        # 收集图片和绘图的包围盒
        page_area = page.rect.width * page_height
        for img in page.get_image_info():
            r = fitz.Rect(img['bbox'])
            # 过滤掉全页背景图（占页面 95% 以上）
            if abs(r.get_area()) < page_area * 0.95:
                rects.append(r)
        for d in page.get_drawings():
            r = fitz.Rect(d['rect'])
            area = abs(r.get_area())
            # 过滤掉全页背景/边框（占页面 95% 以上）
            if area >= page_area * 0.95:
                continue
            # 过滤掉微小的绘制噪点（面积 < 5 平方点）
            if area < 5:
                continue
            rects.append(r)

        if not rects:
            continue

        # 合并重叠/靠近的矩形为连续内容区域
        rects = merge_rects(rects, gap=5)
        rects.sort(key=lambda r: r.y0)

        min_gap = page_height * min_gap_ratio

        # 按垂直空白分组
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

        # 输出每组为独立 A4 页面
        for group in groups:
            x0 = min(r.x0 for r in group)
            y0 = min(r.y0 for r in group)
            x1 = max(r.x1 for r in group)
            y1 = max(r.y1 for r in group)
            src_clip = fitz.Rect(x0, y0, x1, y1)

            # 跳过过小的内容（残留页码等）
            if src_clip.height < 15:
                continue

            new_page = dst.new_page(width=a4.width, height=a4.height)

            margin = 30
            avail_width = a4.width - 2 * margin
            scale = avail_width / src_clip.width if src_clip.width > avail_width else 1.0
            avail_height = a4.height - 2 * margin
            if src_clip.height * scale > avail_height:
                scale = avail_height / src_clip.height

            new_w = src_clip.width * scale
            new_h = src_clip.height * scale
            dest_rect = fitz.Rect(
                margin,
                margin,
                margin + new_w,
                margin + new_h
            )

            new_page.show_pdf_page(dest_rect, src, page.number, clip=src_clip)

    dst.save(dst_pdf)
    dst.close()
    src.close()


def split_by_image(src_pdf, dst_pdf, min_gap_ratio=0.10, dpi=150,
                   white_thresh=250, coverage=0.995):
    """
    将 src_pdf 每一页渲染为图像，以"几乎纯白且足够宽的行"作为空白分隔，
    切分后每部分放到一个 A4 页面，保存为 dst_pdf。

    white_thresh: 像素通道值 >= 此值视为"白"（255 为纯白）
    coverage:     一行中白像素占比 >= 此值视为"白行"
    """
    src = fitz.open(src_pdf)
    dst = fitz.open()
    a4 = fitz.Rect(0, 0, 595.28, 841.89)

    for page in src:
        pix = page.get_pixmap(dpi=dpi)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n)

        # 逐像素判白（取前 3 通道 RGB，忽略可能的 alpha）
        if pix.n >= 3:
            is_white_px = np.all(img[:, :, :3] >= white_thresh, axis=2)
        else:
            is_white_px = img[:, :, 0] >= white_thresh

        # 每行白像素占比 >= coverage → 白行
        white_ratio = np.mean(is_white_px, axis=1)
        is_white_row = white_ratio >= coverage

        # 标量：PDF 点 / 像素
        scale_y = page.rect.height / pix.height
        scale_x = page.rect.width / pix.width
        min_gap_px = int(pix.height * min_gap_ratio)

        # 找出所有足够高的连续白行区间（空白间隙）
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

        # 内容区间 = 间隙之间的区域
        content_ys = []
        prev_end = 0
        for gs, ge in gaps:
            if gs > prev_end:
                content_ys.append((prev_end, gs))
            prev_end = ge
        if prev_end < pix.height:
            content_ys.append((prev_end, pix.height))

        # 逐块输出
        for row_start, row_end in content_ys:
            # 在内容行范围内找水平边界
            block_mask = ~is_white_px[row_start:row_end, :]
            col_has_content = np.any(block_mask, axis=0)
            content_cols = np.where(col_has_content)[0]
            if len(content_cols) == 0:
                continue

            # 留少量像素内边距
            pad = int(5 * dpi / 72)
            col0 = max(0, content_cols[0] - pad)
            col1 = min(pix.width, content_cols[-1] + 1 + pad)
            row0 = max(0, row_start - pad)
            row1 = min(pix.height, row_end + pad)

            # 像素坐标 → PyMuPDF 坐标（原点在左上角，y 向下增长）
            src_y0 = row0 * scale_y
            src_y1 = row1 * scale_y
            src_x0 = col0 * scale_x
            src_x1 = col1 * scale_x
            src_clip = fitz.Rect(src_x0, src_y0, src_x1, src_y1)

            # 跳过过小的内容（残留页码等）
            if src_clip.height < 15:
                continue
            # 跳过页面底部孤立的页码块（极窄 + 靠近底部）
            if src_y0 > page.rect.height * 0.85 and src_clip.width < 50:
                continue

            new_page = dst.new_page(width=a4.width, height=a4.height)

            margin = 30
            avail_w = a4.width - 2 * margin
            s = avail_w / src_clip.width if src_clip.width > avail_w else 1.0
            avail_h = a4.height - 2 * margin
            if src_clip.height * s > avail_h:
                s = avail_h / src_clip.height

            new_w = src_clip.width * s
            new_h = src_clip.height * s
            dest_rect = fitz.Rect(margin, margin, margin + new_w, margin + new_h)
            new_page.show_pdf_page(dest_rect, src, page.number, clip=src_clip)

    dst.save(dst_pdf)
    dst.close()
    src.close()


# 使用示例
split_by_whitespace("1.pdf", "out_text.pdf", min_gap_ratio=0.10)
split_by_image("1.pdf", "out_image.pdf", min_gap_ratio=0.10)