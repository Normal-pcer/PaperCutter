<template>
  <div class="output-panel">
    <div class="panel-header">
      <h3>输出文件</h3>
      <div class="header-actions">
        <select class="layout-select" :value="currentLayoutId" @change="onLayoutChange">
          <option v-for="preset in layoutStore.presets" :key="preset.id" :value="preset.id">
            {{ preset.name }}
          </option>
        </select>
        <button class="btn-sm" @click="addPage">+ 页</button>
        <button class="btn-sm btn-danger" @click="deletePage"
          :disabled="outputStore.pages.length <= 1">删除此页</button>
        <button class="btn-sm btn-primary" @click="downloadPdf"
          :disabled="!canDownload">下载 PDF</button>
      </div>
    </div>
    <div class="viewer-area">
      <div class="page-wrap">
        <div class="page-stack" :style="pageStackStyle">
          <!-- Content canvas: shows blank page + pasted source content -->
          <canvas ref="contentCanvasRef" class="output-canvas" :style="canvasCssStyle"></canvas>
          <!-- Overlay canvas: shows slots, selection borders, badges -->
          <canvas
            ref="overlayRef"
            class="paste-overlay"
            :style="canvasCssStyle"
            @mousedown="onMouseDown"
            @mousemove="onMouseMove"
            @mouseup="onMouseUp"
            @mouseleave="onMouseLeave"
            @contextmenu.prevent="onContextMenu"
          ></canvas>
        </div>
        <div class="page-nav">
          <button @click="prevPage" :disabled="currentPage <= 0">◀</button>
          <span>{{ currentPage + 1 }} / {{ outputStore.pages.length }}</span>
          <button @click="nextPage"
            :disabled="currentPage >= outputStore.pages.length - 1">▶</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import type { Rect, AppMode, PasteItem } from '../types'
import { A4_WIDTH, A4_HEIGHT, DEFAULT_MARGIN } from '../types'
import { useOutputStore } from '../stores/outputStore'
import { useCutStore } from '../stores/cutStore'
import { useLayoutStore } from '../stores/layoutStore'
import { useHistoryStore } from '../stores/historyStore'
import { buildPdf } from '../api'
import type { PDFDocumentProxy } from 'pdfjs-dist'

const props = defineProps<{
  fileId: string
  currentPage: number
  mode: AppMode
  pdfDoc: PDFDocumentProxy | null
  zoom: number
}>()

const emit = defineEmits<{
  prevPage: []
  nextPage: []
}>()

const outputStore = useOutputStore()
const cutStore = useCutStore()
const layoutStore = useLayoutStore()
const historyStore = useHistoryStore()

const contentCanvasRef = ref<HTMLCanvasElement | null>(null)
const overlayRef = ref<HTMLCanvasElement | null>(null)
const rendering = ref(false)

// CSS display size — canvases render at zoom * dpr resolution, displayed at zoom size
const canvasCssStyle = computed(() => ({
  width: (A4_WIDTH * props.zoom) + 'px',
  height: (A4_HEIGHT * props.zoom) + 'px',
}))

const pageStackStyle = computed(() => ({
  width: (A4_WIDTH * props.zoom) + 'px',
  height: (A4_HEIGHT * props.zoom) + 'px',
}))

const currentLayoutId = computed(() => {
  const page = outputStore.pages.find((p) => p.pageNum === props.currentPage)
  return page?.layoutId ?? outputStore.defaultLayoutId
})

const canDownload = computed(() => !!props.fileId && outputStore.pastes.length > 0)

// ─── Drag state ─────────────────────────────────────────────────────

const isDragging = ref(false)
const dragItemId = ref<string | null>(null)
const dragOffset = ref({ x: 0, y: 0 })

// ─── Render output page with pasted content ─────────────────────────

async function renderOutputPage() {
  const canvas = contentCanvasRef.value
  if (!canvas) return

  // Render at higher resolution for sharpness (retina)
  const dpr = Math.max(window.devicePixelRatio || 1, 1.5)
  const renderScale = props.zoom * dpr
  const cw = A4_WIDTH * renderScale
  const ch = A4_HEIGHT * renderScale
  canvas.width = cw
  canvas.height = ch
  // CSS display size set via style below

  const ctx = canvas.getContext('2d')!

  // 1. Blank A4 page
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, cw, ch)
  ctx.strokeStyle = '#ccc'
  ctx.lineWidth = dpr  // slightly thicker for high-res
  ctx.strokeRect(0.5, 0.5, cw - 1, ch - 1)

  // 2. Render pasted content
  const pagePastes = outputStore.pastesByPage.get(props.currentPage) || []

  for (const paste of pagePastes) {
    if (!props.pdfDoc) continue

    try {
      const srcPage = await props.pdfDoc.getPage(paste.srcPageNum + 1)

      // Render source page at high resolution
      const viewport = srcPage.getViewport({ scale: renderScale })
      const srcCanvas = document.createElement('canvas')
      srcCanvas.width = viewport.width
      srcCanvas.height = viewport.height
      const srcCtx = srcCanvas.getContext('2d')!
      await srcPage.render({ canvasContext: srcCtx, viewport }).promise

      // Source rect in high-res pixels
      const sx = paste.rect.x * renderScale
      const sy = paste.rect.y * renderScale
      const sw = paste.rect.w * renderScale
      const sh = paste.rect.h * renderScale

      // Destination: top-left of destRect, at original size (high-res)
      const dx = paste.destRect.x * renderScale
      const dy = paste.destRect.y * renderScale

      ctx.drawImage(srcCanvas,
        sx, sy, sw, sh,     // source clip
        dx, dy, sw, sh       // dest: same size, top-left of slot
      )
    } catch (e) {
      console.warn('Failed to render paste content:', e)
    }
  }
}

// ─── Retina helpers ────────────────────────────────────────────────

function getRenderScale(): number {
  const dpr = Math.max(window.devicePixelRatio || 1, 1.5)
  return props.zoom * dpr
}

// ─── Draw overlay (slots, borders, badges) ──────────────────────────

function drawOverlay() {
  const canvas = overlayRef.value
  if (!canvas) return
  const rs = getRenderScale()
  canvas.width = A4_WIDTH * rs
  canvas.height = A4_HEIGHT * rs
  const ctx = canvas.getContext('2d')!
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const pagePastes = outputStore.pastesByPage.get(props.currentPage) || []
  const page = outputStore.pages.find((p) => p.pageNum === props.currentPage)
  const layoutId = page?.layoutId ?? outputStore.defaultLayoutId

  // Draw layout slots (dashed) at high resolution
  if (layoutId !== 'free') {
    const slots = layoutStore.getSlots(layoutId)
    for (const slot of slots) {
      ctx.strokeStyle = '#bdbdbd'
      ctx.lineWidth = 2
      ctx.setLineDash([6 * rs, 4 * rs])
      ctx.strokeRect(
        slot.x * rs, slot.y * rs,
        slot.w * rs, slot.h * rs
      )
      ctx.setLineDash([])
    }
  }

  // Draw paste borders and badges at high resolution
  for (const paste of pagePastes) {
    const { x, y, w, h } = paste.destRect
    const isSelected = paste.id === outputStore.selectedPasteId

    // Border only (no fill - content shows through)
    ctx.strokeStyle = isSelected ? '#9C27B0' : '#7B1FA2'
    ctx.lineWidth = isSelected ? 3 : 2
    ctx.strokeRect(
      x * rs, y * rs,
      w * rs, h * rs
    )

    // Badge
    const badgeX = x * rs
    const badgeY = Math.max(0, y * rs - 22)
    ctx.fillStyle = '#9C27B0'
    ctx.beginPath()
    if (ctx.roundRect) {
      ctx.roundRect(badgeX, badgeY, 40, 22, 4)
    } else {
      ctx.fillRect(badgeX, badgeY, 40, 22)
    }
    ctx.fill()
    ctx.fillStyle = '#fff'
    ctx.font = 'bold 11px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(`#${paste.cutRegionId}`, badgeX + 20, badgeY + 15)
  }
}

// ─── Mouse handlers ─────────────────────────────────────────────────

function screenToPdf(sx: number, sy: number): { x: number; y: number } {
  return { x: sx / props.zoom, y: sy / props.zoom }
}

function onMouseDown(e: MouseEvent) {
  if (props.mode !== 'operate') return
  const canvas = overlayRef.value
  if (!canvas) return
  const rect2 = canvas.getBoundingClientRect()
  const sx = e.clientX - rect2.left
  const sy = e.clientY - rect2.top
  const pdf = screenToPdf(sx, sy)

  // Check clicking existing paste (for drag or select)
  const pagePastes = (outputStore.pastesByPage.get(props.currentPage) || []).slice().reverse()
  for (const paste of pagePastes) {
    const r = paste.destRect
    if (pdf.x >= r.x && pdf.x <= r.x + r.w &&
        pdf.y >= r.y && pdf.y <= r.y + r.h) {
      outputStore.selectPaste(paste.id)
      isDragging.value = true
      dragItemId.value = paste.id
      dragOffset.value = { x: pdf.x - r.x, y: pdf.y - r.y }
      drawOverlay()
      return
    }
  }

  // Click empty space → paste
  historyStore.saveSnapshot()
  doPaste(pdf.x, pdf.y)
  renderOutputPage().then(() => drawOverlay())
}

function doPaste(pdfX: number, pdfY: number) {
  const selected = cutStore.selectedRegion
  let region = selected
  if (!region) {
    const unpasted = cutStore.unPastedRegions
    if (unpasted.length === 0) return
    region = unpasted[0]
  }
  if (region.pasted) return

  const page = outputStore.pages.find((p) => p.pageNum === props.currentPage)
  const layoutId = page?.layoutId ?? outputStore.defaultLayoutId

  let destRect: Rect

  if (layoutId === 'free') {
    // In free layout, destRect has same size as source (original size)
    destRect = { x: pdfX, y: pdfY, w: region.rect.w, h: region.rect.h }
  } else {
    const slots = layoutStore.getSlots(layoutId)
    const pagePastes = outputStore.pastesByPage.get(props.currentPage) || []
    const usedSlotIndices = new Set<number>()
    for (const paste of pagePastes) {
      for (let i = 0; i < slots.length; i++) {
        const sl = slots[i]
        if (Math.abs(paste.destRect.x - sl.x) < 1 &&
            Math.abs(paste.destRect.y - sl.y) < 1) {
          usedSlotIndices.add(i)
          break
        }
      }
    }
    let targetSlot: Rect | null = null
    for (let i = 0; i < slots.length; i++) {
      if (!usedSlotIndices.has(i)) {
        targetSlot = slots[i]
        break
      }
    }
    if (!targetSlot) {
      const newPage = outputStore.addPage(props.currentPage)
      const newSlots = layoutStore.getSlots(newPage.layoutId)
      targetSlot = newSlots[0] ?? { x: DEFAULT_MARGIN, y: DEFAULT_MARGIN,
                                     w: region.rect.w, h: region.rect.h }
      targetSlot = { x: pdfX, y: pdfY, w: region.rect.w, h: region.rect.h }
    }
    // destRect = slot position and size (content is placed top-left within)
    destRect = {
      x: targetSlot.x, y: targetSlot.y,
      w: targetSlot.w, h: targetSlot.h,
    }
  }

  outputStore.addPaste(region.id, region.pageNum, props.currentPage, region.rect, destRect)
}

function onMouseMove(e: MouseEvent) {
  const canvas = overlayRef.value
  if (!canvas) return
  const rect2 = canvas.getBoundingClientRect()
  const sx = e.clientX - rect2.left
  const sy = e.clientY - rect2.top
  const pdf = screenToPdf(sx, sy)

  if (isDragging.value && dragItemId.value) {
    const paste = outputStore.pastes.find((p) => p.id === dragItemId.value)
    if (paste) {
      outputStore.movePaste(dragItemId.value, props.currentPage, {
        x: pdf.x - dragOffset.value.x,
        y: pdf.y - dragOffset.value.y,
        w: paste.destRect.w,
        h: paste.destRect.h,
      })
      drawOverlay()
      // Re-render content for new position
      renderOutputPage().then(() => {})
    }
    return
  }

  if (props.mode === 'operate') {
    const pagePastes = outputStore.pastesByPage.get(props.currentPage) || []
    const over = pagePastes.some((p) => {
      const r = p.destRect
      return pdf.x >= r.x && pdf.x <= r.x + r.w &&
             pdf.y >= r.y && pdf.y <= r.y + r.h
    })
    canvas.style.cursor = over ? 'move' : 'cell'
  }
}

function onMouseUp() {
  if (isDragging.value && dragItemId.value) {
    historyStore.saveSnapshot()
  }
  isDragging.value = false
  dragItemId.value = null
}

function onMouseLeave() {
  isDragging.value = false
  dragItemId.value = null
}

function onContextMenu(e: MouseEvent) {
  if (props.mode !== 'operate') return
  const canvas = overlayRef.value
  if (!canvas) return
  const rect2 = canvas.getBoundingClientRect()
  const sx = e.clientX - rect2.left
  const sy = e.clientY - rect2.top
  const pdf = screenToPdf(sx, sy)

  const pagePastes = (outputStore.pastesByPage.get(props.currentPage) || []).slice().reverse()
  for (const paste of pagePastes) {
    const r = paste.destRect
    if (pdf.x >= r.x && pdf.x <= r.x + r.w &&
        pdf.y >= r.y && pdf.y <= r.y + r.h) {
      historyStore.saveSnapshot()
      outputStore.deletePaste(paste.id)
      renderOutputPage().then(() => drawOverlay())
      return
    }
  }
}

// ─── Actions ────────────────────────────────────────────────────────

function prevPage() { emit('prevPage') }
function nextPage() { emit('nextPage') }

function onLayoutChange(e: Event) {
  historyStore.saveSnapshot()
  outputStore.setPageLayout(props.currentPage, (e.target as HTMLSelectElement).value)
}

function addPage() {
  historyStore.saveSnapshot()
  outputStore.addPage(props.currentPage)
}

function deletePage() {
  if (outputStore.pages.length <= 1) return
  historyStore.saveSnapshot()
  outputStore.deletePage(props.currentPage)
}

async function downloadPdf() {
  if (!props.fileId) return
  try {
    const blob = await buildPdf(props.fileId, outputStore.pastes, outputStore.pages)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'output.pdf'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Download failed:', e)
  }
}

// ─── Lifecycle ──────────────────────────────────────────────────────

onMounted(() => {
  renderOutputPage().then(() => drawOverlay())
})

watch(
  () => [props.currentPage, outputStore.pastes, outputStore.selectedPasteId,
         outputStore.pages, props.pdfDoc],
  () => {
    void nextTick().then(async () => {
      await renderOutputPage()
      drawOverlay()
    })
  },
  { deep: true }
)
</script>

<style scoped>
.output-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fafafa;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.panel-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.layout-select {
  padding: 4px 8px;
  font-size: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 4px;
  border: 1px solid #ccc;
  background: #fff;
  cursor: pointer;
}

.btn-sm:hover { background: #f5f5f5; }
.btn-sm:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-primary {
  background: #1976D2;
  color: #fff;
  border-color: #1976D2;
}

.btn-primary:hover { background: #1565C0; }

.btn-danger {
  color: #d32f2f;
  border-color: #d32f2f;
}

.btn-danger:hover { background: #ffebee; }

.viewer-area {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  padding: 16px;
}

.page-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.page-stack {
  position: relative;
  display: inline-block;
  box-shadow: 0 2px 12px rgba(0,0,0,0.15);
  line-height: 0;
}

.output-canvas {
  display: block;
}

.paste-overlay {
  position: absolute;
  top: 0;
  left: 0;
}

.page-nav {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  padding: 4px 12px;
  background: #f5f5f5;
  border-radius: 6px;
}

.page-nav button {
  border: 1px solid #ccc;
  background: #fff;
  border-radius: 4px;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 14px;
}

.page-nav button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
