<template>
  <div class="source-panel">
    <div class="panel-header">
      <h3>源文件</h3>
      <button class="btn-sm" @click="clearPage" :disabled="!hasRegionsOnPage">
        清除本页选区
      </button>
    </div>
    <div class="viewer-area">
      <PdfViewer
        :rendered-canvas="renderedPage?.canvas ?? null"
        :current-page="currentPage"
        :total-pages="totalPages"
        :loading="loading"
        :error="error"
        :display-width="displayWidth"
        :display-height="displayHeight"
        @prev-page="$emit('prevPage')"
        @next-page="$emit('nextPage')"
      >
        <template #overlay>
          <canvas
            ref="overlayRef"
            class="selection-overlay"
            :style="overlayStyle"
            @mousedown="onMouseDown"
            @mousemove="onMouseMove"
            @mouseup="onMouseUp"
            @mouseleave="onMouseLeave"
            @contextmenu.prevent="onContextMenu"
          ></canvas>
        </template>
      </PdfViewer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import type { Rect, AppMode } from '../types'
import { useCutStore } from '../stores/cutStore'
import { useHistoryStore } from '../stores/historyStore'
import PdfViewer from './PdfViewer.vue'

const props = defineProps<{
  renderedPage: any
  currentPage: number
  totalPages: number
  loading: boolean
  error: string | null
  mode: AppMode
}>()

defineEmits<{
  prevPage: []
  nextPage: []
}>()

const cutStore = useCutStore()
const historyStore = useHistoryStore()
const overlayRef = ref<HTMLCanvasElement | null>(null)

const displayWidth = computed(() => {
  if (!props.renderedPage) return undefined
  return props.renderedPage.width * (props.renderedPage.displayZoom ?? 1)
})

const displayHeight = computed(() => {
  if (!props.renderedPage) return undefined
  return props.renderedPage.height * (props.renderedPage.displayZoom ?? 1)
})

const overlayStyle = computed(() => {
  if (displayWidth.value && displayHeight.value) {
    return {
      width: displayWidth.value + 'px',
      height: displayHeight.value + 'px',
    }
  }
  return {}
})

// Drawing state
const isDrawing = ref(false)
const drawStart = ref({ x: 0, y: 0 })
const drawCurrent = ref({ x: 0, y: 0 })

const hasRegionsOnPage = computed(() =>
  (cutStore.regionsByPage.get(props.currentPage) || []).length > 0
)

function clearPage() {
  historyStore.saveSnapshot()
  cutStore.clearPageRegions(props.currentPage)
}

// ─── Coordinate mapping ─────────────────────────────────────────────
// Two different scales needed because of retina rendering:
// - Canvas pixel size = pdfWidth * renderScale (e.g., pdfWidth * 1.8)
// - Canvas CSS size  = pdfWidth * displayZoom (e.g., pdfWidth * 0.9)
// - Mouse coords are in CSS space
// - Drawing must use pixel coordinates

function getDrawScale(): number {
  // PDF coords → canvas pixel coords (use renderScale)
  if (!props.renderedPage) return 1
  const pw = props.renderedPage.width
  return pw > 0 ? props.renderedPage._renderedWidth / pw : 1
}

function getCoordScale(): number {
  // Mouse CSS coords → PDF coords (use displayZoom)
  if (!props.renderedPage) return 1
  return props.renderedPage.displayZoom ?? getDrawScale()
}

// Convert mouse CSS coords to canvas pixel coords
function cssToPixel(sx: number, sy: number): { x: number; y: number } {
  const dw = displayWidth.value ?? props.renderedPage?._renderedWidth ?? 1
  const dh = displayHeight.value ?? props.renderedPage?._renderedHeight ?? 1
  const pw = props.renderedPage?._renderedWidth ?? dw
  const ph = props.renderedPage?._renderedHeight ?? dh
  return { x: sx * pw / dw, y: sy * ph / dh }
}

// ─── Drawing ────────────────────────────────────────────────────────

function drawAll() {
  const canvas = overlayRef.value
  if (!canvas || !props.renderedPage) return

  // Match overlay canvas size to rendered canvas (pixel size)
  canvas.width = props.renderedPage._renderedWidth
  canvas.height = props.renderedPage._renderedHeight

  const ctx = canvas.getContext('2d')!
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Use drawScale for PDF → canvas pixel conversion
  const ds = getDrawScale()
  const regions = cutStore.regionsByPage.get(props.currentPage) || []

  for (const region of regions) {
    const { x, y, w, h } = region.rect
    const isSelected = region.id === cutStore.selectedRegionId
    const px = x * ds, py = y * ds, pw = w * ds, ph = h * ds

    ctx.fillStyle = isSelected
      ? 'rgba(33, 150, 243, 0.2)'
      : 'rgba(76, 175, 80, 0.15)'
    ctx.fillRect(px, py, pw, ph)

    ctx.strokeStyle = isSelected ? '#2196F3' : '#4CAF50'
    ctx.lineWidth = 2
    ctx.strokeRect(px, py, pw, ph)

    // ID badge
    const badgeX = px
    const badgeY = Math.max(0, py - 20)
    ctx.fillStyle = isSelected ? '#2196F3' : '#4CAF50'
    ctx.beginPath()
    if (ctx.roundRect) {
      ctx.roundRect(badgeX, badgeY, 28, 20, 4)
    } else {
      ctx.fillRect(badgeX, badgeY, 28, 20)
    }
    ctx.fill()
    ctx.fillStyle = '#fff'
    ctx.font = 'bold 12px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(`${region.id}`, badgeX + 14, badgeY + 14)
  }

  // Current drawing rect — convert CSS coords to canvas pixel coords
  if (isDrawing.value) {
    const p1 = cssToPixel(drawStart.value.x, drawStart.value.y)
    const p2 = cssToPixel(drawCurrent.value.x, drawCurrent.value.y)
    const rx = Math.min(p1.x, p2.x)
    const ry = Math.min(p1.y, p2.y)
    const rw = Math.abs(p2.x - p1.x)
    const rh = Math.abs(p2.y - p1.y)
    ctx.fillStyle = 'rgba(255, 152, 0, 0.15)'
    ctx.fillRect(rx, ry, rw, rh)
    ctx.strokeStyle = '#FF9800'
    ctx.lineWidth = 1.5
    ctx.setLineDash([5, 3])
    ctx.strokeRect(rx, ry, rw, rh)
    ctx.setLineDash([])
  }
}

// ─── Mouse handlers ─────────────────────────────────────────────────

function onMouseDown(e: MouseEvent) {
  if (props.mode !== 'operate') return
  const canvas = overlayRef.value
  if (!canvas) return
  const bounds = canvas.getBoundingClientRect()
  const sx = e.clientX - bounds.left  // CSS coordinate
  const sy = e.clientY - bounds.top

  // Convert to PDF coords for hit testing
  const cs = getCoordScale()
  const pdfX = sx / cs
  const pdfY = sy / cs

  // Check if clicking existing region (for selection)
  const regions = (cutStore.regionsByPage.get(props.currentPage) || []).slice().reverse()
  for (const region of regions) {
    const r = region.rect
    if (pdfX >= r.x && pdfX <= r.x + r.w &&
        pdfY >= r.y && pdfY <= r.y + r.h) {
      cutStore.selectRegion(region.id)
      drawAll()
      return
    }
  }

  // Start new rect — store CSS coordinates
  isDrawing.value = true
  drawStart.value = { x: sx, y: sy }
  drawCurrent.value = { x: sx, y: sy }
}

function onMouseMove(e: MouseEvent) {
  const canvas = overlayRef.value
  if (!canvas) return
  const bounds = canvas.getBoundingClientRect()
  const sx = e.clientX - bounds.left
  const sy = e.clientY - bounds.top

  if (isDrawing.value) {
    drawCurrent.value = { x: sx, y: sy }
    drawAll()
    return
  }

  if (props.mode === 'operate') {
    const cs = getCoordScale()
    const pdfX = sx / cs
    const pdfY = sy / cs
    const regions = cutStore.regionsByPage.get(props.currentPage) || []
    const over = regions.some((r) => {
      return pdfX >= r.x && pdfX <= r.x + r.w &&
             pdfY >= r.y && pdfY <= r.y + r.h
    })
    canvas.style.cursor = over ? 'pointer' : 'crosshair'
  }
}

function onMouseUp() {
  if (!isDrawing.value) return
  isDrawing.value = false

  // Convert CSS coords to PDF coords for creating the region
  const cs = getCoordScale()
  const rx = Math.min(drawStart.value.x, drawCurrent.value.x)
  const ry = Math.min(drawStart.value.y, drawCurrent.value.y)
  const rw = Math.abs(drawCurrent.value.x - drawStart.value.x)
  const rh = Math.abs(drawCurrent.value.y - drawStart.value.y)

  if (rw >= 5 && rh >= 5) {
    historyStore.saveSnapshot()
    cutStore.addRegion(props.currentPage, {
      x: rx / cs,
      y: ry / cs,
      w: rw / cs,
      h: rh / cs,
    })
  }
  drawAll()
}

function onMouseLeave() {
  if (isDrawing.value) {
    isDrawing.value = false
    drawAll()
  }
}

function onContextMenu(e: MouseEvent) {
  if (props.mode !== 'operate') return
  const canvas = overlayRef.value
  if (!canvas) return
  const bounds = canvas.getBoundingClientRect()
  const sx = e.clientX - bounds.left
  const sy = e.clientY - bounds.top
  const cs = getCoordScale()
  const pdfX = sx / cs
  const pdfY = sy / cs

  const regions = (cutStore.regionsByPage.get(props.currentPage) || []).slice().reverse()
  for (const region of regions) {
    const r = region.rect
    if (pdfX >= r.x && pdfX <= r.x + r.w &&
        pdfY >= r.y && pdfY <= r.y + r.h) {
      historyStore.saveSnapshot()
      cutStore.deleteRegion(region.id)
      drawAll()
      return
    }
  }
}

// ─── Watch for redraw ───────────────────────────────────────────────

watch(
  () => [props.renderedPage, cutStore.regions, cutStore.selectedRegionId, props.currentPage],
  () => { void nextTick().then(() => drawAll()) },
  { deep: true }
)
</script>

<style scoped>
.source-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-right: 1px solid #e0e0e0;
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

.viewer-area {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  padding: 16px;
}

.selection-overlay {
  position: absolute;
  top: 0;
  left: 0;
}
</style>
