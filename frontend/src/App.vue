<template>
  <div class="app">
    <Toolbar
      v-model:mode="mode"
      :zoom="zoom"
      :file-id="fileId"
      :has-file="hasFile"
      :auto-cut-loading="autoCutLoading"
      @upload="onUpload"
      @auto-cut="onAutoCut"
      @auto-paste="autoPaste"
      @zoom-in="zoomIn"
      @zoom-out="zoomOut"
      @zoom-reset="zoomReset"
      @undo="undo"
      @redo="redo"
    />

    <div class="main-content">
      <SourcePanel
        :rendered-page="sourceRenderedPage"
        :current-page="sourcePage"
        :total-pages="totalSourcePages"
        :loading="sourceLoading"
        :error="displayError"
        :mode="mode"
        @prev-page="sourcePage = Math.max(0, sourcePage - 1)"
        @next-page="sourcePage = Math.min(totalSourcePages - 1, sourcePage + 1)"
      />

      <RegionList
        @go-to-page="(pageNum: number) => { sourcePage = pageNum; }"
      />

      <OutputPanel
        :file-id="fileId"
        :current-page="outputPage"
        :mode="mode"
        :pdf-doc="pdfDoc"
        :zoom="zoom"
        @prev-page="outputPage = Math.max(0, outputPage - 1)"
        @next-page="outputPage = Math.min(outputStore.pages.length - 1, outputPage + 1)"
      />

      <LayoutConfig />
    </div>

    <!-- Debug panel (toggle with F12 or always show when errors) -->
    <div v-if="showDebug" class="debug-panel">
      <div class="debug-header">
        <strong>调试信息</strong>
        <button @click="showDebug = false">✕</button>
      </div>
      <div class="debug-body">
        <div v-for="(line, i) in allDebugLines" :key="i" class="debug-line">{{ line }}</div>
      </div>
    </div>

    <!-- Status bar -->
    <div class="status-bar" @dblclick="showDebug = !showDebug">
      <span>模式: {{ modeLabel }}</span>
      <span v-if="fileId">文件: {{ fileName }}</span>
      <span>源页: {{ sourcePage + 1 }}/{{ totalSourcePages || 0 }}</span>
      <span>输出页: {{ outputPage + 1 }}/{{ outputStore.pages.length }}</span>
      <span>选区: {{ cutStore.regions.length }} (未贴: {{ cutStore.unPastedRegions.length }})</span>
      <span>↩{{ historyStore.undoStack.length }} ↪{{ historyStore.redoStack.length }}</span>
      <span v-if="sourceError || uploadError" class="status-error">
        ⚠ {{ (sourceError || uploadError)?.substring(0, 60) }}...
      </span>
      <span class="status-hint">双击状态栏查看调试</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { AppMode, RenderedPage, Rect } from './types'
import { useCutStore } from './stores/cutStore'
import { useOutputStore } from './stores/outputStore'
import { useLayoutStore } from './stores/layoutStore'
import { useHistoryStore } from './stores/historyStore'
import { usePdfLoader } from './composables/usePdfLoader'
import { uploadPdf, getPageImageUrl, autoCut as apiAutoCut } from './api'
import Toolbar from './components/Toolbar.vue'
import SourcePanel from './components/SourcePanel.vue'
import OutputPanel from './components/OutputPanel.vue'
import RegionList from './components/RegionList.vue'
import LayoutConfig from './components/LayoutConfig.vue'

// ─── Stores ──────────────────────────────────────────────────────────

const cutStore = useCutStore()
const outputStore = useOutputStore()
const layoutStore = useLayoutStore()
const historyStore = useHistoryStore()

// ─── PDF loader ──────────────────────────────────────────────────────

const { pdfDoc, loadFromFile, loadFromUrl, loadFromArrayBuffer, renderPageAtScale, getPageSize,
        pageCount, loading: sourceLoading, error: sourceError, debugInfo } = usePdfLoader()

// ─── State ───────────────────────────────────────────────────────────

const mode = ref<AppMode>('view')
const zoom = ref(0.9)  // Default display zoom — retina rendering keeps it sharp
const fileId = ref('')
const fileName = ref('')
const hasFile = ref(false)
const uploadError = ref<string | null>(null)
const showDebug = ref(false)

const sourcePage = ref(0)
const outputPage = ref(0)
const sourceRenderedPage = ref<RenderedPage | null>(null)
const autoCutLoading = ref(false)

const totalSourcePages = computed(() => pageCount.value)

// Combine errors for display
const displayError = computed(() => uploadError.value || sourceError.value)

// Debug lines from pdf loader + app
const appDebugLines = ref<string[]>([])
const allDebugLines = computed(() => [...debugInfo.value, ...appDebugLines.value])

const modeLabel = computed(() => {
  switch (mode.value) {
    case 'operate': return '操作'
    default: return '查看'
  }
})

// ─── Source page rendering ───────────────────────────────────────────

async function renderSourcePage() {
  if (!hasFile.value) return

  // Try pdf.js first (renders at displayZoom * dpr for sharpness)
  const result = await renderPageAtScale(sourcePage.value, zoom.value)
  if (result) {
    const size = await getPageSize(sourcePage.value)
    sourceRenderedPage.value = {
      pageNum: sourcePage.value,
      canvas: result.canvas,
      width: size?.width ?? 595,
      height: size?.height ?? 842,
      displayZoom: result.displayZoom,
      renderScale: result.renderScale,
      _renderedWidth: result.canvas.width,
      _renderedHeight: result.canvas.height,
    } as any
    return
  }

  // Fallback: use backend image API
  if (fileId.value) {
    appDebugLines.value.push(`pdf.js failed, falling back to backend image API for page ${sourcePage.value}`)
    try {
      const imgUrl = getPageImageUrl(fileId.value, sourcePage.value, Math.round(150 * zoom.value))
      const img = new Image()
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve()
        img.onerror = () => reject(new Error('Image load failed'))
        img.src = imgUrl
      })
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')!
      ctx.drawImage(img, 0, 0)
      sourceRenderedPage.value = {
        pageNum: sourcePage.value,
        canvas,
        width: 595.28,
        height: 841.89,
        _scale: 150 * zoom.value / 72,
        _renderedWidth: img.naturalWidth,
        _renderedHeight: img.naturalHeight,
      } as any
    } catch (e: any) {
      appDebugLines.value.push(`Backend image fallback also failed: ${e.message}`)
    }
  }
}

watch(sourcePage, () => { renderSourcePage() })
watch(zoom, () => { renderSourcePage() })

// ─── Upload ──────────────────────────────────────────────────────────

async function onUpload(file: File) {
  uploadError.value = null
  appDebugLines.value = []
  appDebugLines.value.push(`onUpload: file="${file.name}", size=${file.size}, type="${file.type}"`)

  try {
    sourceLoading.value = true
    fileName.value = file.name

    // 1. Upload to backend
    appDebugLines.value.push('Uploading to backend...')
    let info
    try {
      info = await uploadPdf(file)
      appDebugLines.value.push(`Backend upload OK: fileId=${info.fileId}, ${info.pageCount} pages`)
    } catch (e: any) {
      appDebugLines.value.push(`Backend upload FAILED: ${e.message}`)
      uploadError.value = `后端上传失败: ${e.message}`
      sourceLoading.value = false
      return
    }

    fileId.value = info.fileId
    hasFile.value = true

    // 2. Load via pdf.js for frontend rendering
    appDebugLines.value.push('Loading via pdf.js...')
    appDebugLines.value.push(`Worker URL: ${(window as any).pdfjsWorkerUrl || 'using ?url import'}`)

    try {
      await loadFromFile(file)
    } catch (e: any) {
      appDebugLines.value.push(`pdf.js loadFromFile threw: ${e.message}`)
    }

    // If pdf.js failed, try loading from the backend as ArrayBuffer
    if (!pageCount.value && !sourceError.value) {
      appDebugLines.value.push('pdf.js returned no pages, trying via ArrayBuffer...')
      const blobUrl = getPageImageUrl(fileId.value, 0).replace('/page/0/image', '')
      // Actually, let's fetch the raw PDF from backend
      try {
        const resp = await fetch(`http://127.0.0.1:8000/api/pdf/${fileId.value}/page/0/image`)
        // The backend doesn't serve the raw PDF, let's use the file directly
        appDebugLines.value.push('Using file ArrayBuffer for pdf.js...')
        const buffer = await file.arrayBuffer()
        await loadFromArrayBuffer(buffer)
      } catch (e: any) {
        appDebugLines.value.push(`ArrayBuffer fallback also failed: ${e.message}`)
      }
    }

    if (sourceError.value) {
      appDebugLines.value.push(`pdf.js error: ${sourceError.value}`)
      appDebugLines.value.push('Will use backend image API for rendering instead')
      // Don't fail - we can still render via backend
      pageCount.value = info.pageCount // use backend page count
    }

    // 3. Render first page
    sourcePage.value = 0
    outputPage.value = 0
    await renderSourcePage()

    if (!sourceRenderedPage.value) {
      appDebugLines.value.push('WARNING: No page rendered after upload!')
    }

    // Reset stores
    historyStore.clear()
    cutStore.regions = []
    cutStore.nextId = 1
    outputStore.pages = [{ pageNum: 0, layoutId: outputStore.defaultLayoutId }]
    outputStore.pastes = []

    mode.value = 'operate'
    appDebugLines.value.push('Upload complete, entering operate mode')
  } catch (e: any) {
    const msg = e?.message ?? 'Unknown error'
    appDebugLines.value.push(`FATAL: ${msg}`)
    uploadError.value = msg
  } finally {
    sourceLoading.value = false
  }
}

// ─── Auto-cut ────────────────────────────────────────────────────────

async function onAutoCut(strategy: 'content' | 'image', scope: 'page' | 'all') {
  if (!fileId.value) return
  autoCutLoading.value = true
  try {
    const pageNum = scope === 'page' ? sourcePage.value : undefined
    const result = await apiAutoCut(fileId.value, strategy, { pageNum } as any)
    historyStore.saveSnapshot()
    if (scope === 'page') {
      // Remove existing regions for this page, keep others
      cutStore.regions = cutStore.regions.filter((r) => r.pageNum !== sourcePage.value)
      const startId = cutStore.nextId
      for (const r of result.regions) {
        cutStore.regions.push({
          id: startId + result.regions.indexOf(r),
          pageNum: r.pageNum,
          rect: { ...r.rect },
          pasted: false,
        })
      }
      cutStore.nextId = startId + result.regions.length
    } else {
      cutStore.regions = []
      cutStore.nextId = 1
      cutStore.setRegions(result.regions)
    }
  } catch (e: any) {
    appDebugLines.value.push(`Auto-cut failed: ${e.message}`)
  } finally {
    autoCutLoading.value = false
  }
}

// ─── Auto-paste ──────────────────────────────────────────────────────

function autoPaste() {
  const unpasted = [...cutStore.unPastedRegions]
  if (unpasted.length === 0) return

  historyStore.saveSnapshot()

  let currentPageNum = outputPage.value
  for (const region of unpasted) {
    let page = outputStore.pages.find((p) => p.pageNum === currentPageNum)
    if (!page) {
      page = outputStore.addPage()
      currentPageNum = page.pageNum
    }

    const layoutId = page.layoutId
    const slots = layoutStore.getSlots(layoutId)

    let destRect: Rect

    if (layoutId === 'free' || slots.length === 0) {
      const existingOnPage = (outputStore.pastesByPage.get(currentPageNum) || [])
      const yOffset = existingOnPage.length * (region.rect.h + 20) + 30
      destRect = { x: 30, y: yOffset, w: region.rect.w, h: region.rect.h }
    } else {
      const pagePastes = outputStore.pastesByPage.get(currentPageNum) || []
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
        const newPage = outputStore.addPage(currentPageNum)
        // Inherit layout from the page that overflowed
        outputStore.setPageLayout(newPage.pageNum, layoutId)
        currentPageNum = newPage.pageNum
        const newSlots = layoutStore.getSlots(layoutId)
        targetSlot = newSlots[0] ?? { x: 30, y: 30, w: region.rect.w, h: region.rect.h }
      }

      destRect = {
        x: targetSlot.x, y: targetSlot.y,
        w: targetSlot.w, h: targetSlot.h,
      }
    }

    outputStore.addPaste(region.id, region.pageNum, currentPageNum, region.rect, destRect)
  }

  outputPage.value = Math.min(outputPage.value, outputStore.pages.length - 1)
}

// ─── Zoom ────────────────────────────────────────────────────────────

function zoomIn() { zoom.value = Math.min(3.0, zoom.value + 0.25) }
function zoomOut() { zoom.value = Math.max(0.25, zoom.value - 0.25) }
function zoomReset() { zoom.value = 1.0 }

// ─── Undo / Redo ─────────────────────────────────────────────────────

function undo() {
  historyStore.undo()
  renderSourcePage()
}
function redo() {
  historyStore.redo()
  renderSourcePage()
}
</script>

<style>
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html,
body,
#app {
  height: 100%;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
  font-size: 14px;
  color: #333;
  background: #f0f2f5;
}
</style>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.debug-panel {
  position: fixed;
  bottom: 28px;
  left: 0;
  right: 0;
  height: 200px;
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 11px;
  z-index: 1000;
  border-top: 2px solid #555;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.debug-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 12px;
  background: #333;
  color: #fff;
}

.debug-header button {
  background: none;
  border: none;
  color: #fff;
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
}

.debug-body {
  flex: 1;
  overflow-y: auto;
  padding: 4px 12px;
}

.debug-line {
  padding: 1px 0;
  border-bottom: 1px solid #2a2a2a;
  white-space: nowrap;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 4px 14px;
  background: #fafafa;
  border-top: 1px solid #e0e0e0;
  font-size: 11px;
  color: #888;
  flex-shrink: 0;
  cursor: default;
}

.status-error {
  color: #d32f2f;
  font-weight: 500;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-hint {
  color: #bbb;
  font-style: italic;
}
</style>
