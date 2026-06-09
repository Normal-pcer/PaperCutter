// ─── Geometry ──────────────────────────────────────────────────────────

export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

// ─── Source: Cut Regions ──────────────────────────────────────────────

export interface CutRegion {
  id: number        // auto-increment, 1-based, user-visible
  pageNum: number   // source page (0-based)
  rect: Rect        // in source PDF coordinates
  pasted: boolean   // has been placed on output?
}

// ─── Output: Pastes & Pages ───────────────────────────────────────────

export interface PasteItem {
  id: string           // unique paste ID (uuid)
  cutRegionId: number  // which cut region this paste uses
  srcPageNum: number   // source page number
  pageNum: number      // output page (0-based)
  rect: Rect           // source clip rect
  destRect: Rect       // position on output page
}

export interface OutputPage {
  pageNum: number
  layoutId: string     // '1up' | '2up' | 'free'
}

// ─── Layout Presets ───────────────────────────────────────────────────

export interface LayoutPreset {
  id: string
  name: string
  slots: Rect[]  // snap slots on an A4 page (595.28 x 841.89 pts)
}

// ─── Backend API Types ────────────────────────────────────────────────

export interface PdfInfo {
  fileId: string
  filename: string
  pageCount: number
  pages: PageInfo[]
}

export interface PageInfo {
  pageNum: number
  width: number
  height: number
}

export interface AutoCutResult {
  regions: {
    pageNum: number
    rect: Rect
  }[]
}

// ─── Constants ────────────────────────────────────────────────────────

export const A4_WIDTH = 595.28
export const A4_HEIGHT = 841.89
export const DEFAULT_MARGIN = 30

// ─── Application Mode ─────────────────────────────────────────────────

export type AppMode = 'view' | 'operate'
