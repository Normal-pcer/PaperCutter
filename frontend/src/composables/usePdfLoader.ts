import { ref, shallowRef } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl

const DEBUG = true
function log(...args: any[]) {
  if (DEBUG) console.log('[PdfLoader]', ...args)
}

export interface RenderedPage {
  pageNum: number
  canvas: HTMLCanvasElement
  width: number          // PDF points (unscaled)
  height: number         // PDF points (unscaled)
  displayZoom: number    // the user-facing zoom level
  renderScale: number    // actual render scale (displayZoom * dpr)
  _renderedWidth: number // canvas pixel width
  _renderedHeight: number // canvas pixel height
}

export function usePdfLoader() {
  const pdfDoc = shallowRef<pdfjsLib.PDFDocumentProxy | null>(null)
  const pageCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const debugInfo = ref<string[]>([])

  function addDebug(msg: string) {
    log(msg)
    debugInfo.value.push(`[${new Date().toLocaleTimeString()}] ${msg}`)
    if (debugInfo.value.length > 50) debugInfo.value.shift()
  }

  async function loadFromUrl(url: string): Promise<void> {
    addDebug(`loadFromUrl: ${typeof url === 'string' ? url.substring(0, 40) : 'N/A'}...`)

    if (!url || typeof url !== 'string') {
      error.value = `Invalid URL: ${JSON.stringify(url)}`
      loading.value = false
      return
    }

    loading.value = true
    error.value = null
    try {
      const doc = await pdfjsLib.getDocument({ url }).promise
      addDebug(`PDF loaded: ${doc.numPages} pages`)
      pdfDoc.value = doc
      pageCount.value = doc.numPages
    } catch (e: any) {
      addDebug(`ERROR: ${e.message}`)
      error.value = e?.message ?? 'Failed to load PDF'
      pdfDoc.value = null
      pageCount.value = 0
    } finally {
      loading.value = false
    }
  }

  async function loadFromFile(file: File): Promise<void> {
    addDebug(`loadFromFile: ${file?.name ?? 'null'}, ${file?.size ?? 0} bytes`)
    if (!file) { error.value = 'No file provided'; return }

    try {
      const url = URL.createObjectURL(file)
      addDebug(`Blob URL: ${url}`)
      await loadFromUrl(url)
    } catch (e: any) {
      addDebug(`Blob URL error: ${e.message}`)
      error.value = `Failed to create blob URL: ${e.message}`
    }
  }

  async function loadFromArrayBuffer(data: ArrayBuffer): Promise<void> {
    addDebug(`loadFromArrayBuffer: ${data.byteLength} bytes`)
    loading.value = true
    error.value = null
    try {
      const doc = await pdfjsLib.getDocument({ data }).promise
      addDebug(`PDF loaded from buffer: ${doc.numPages} pages`)
      pdfDoc.value = doc
      pageCount.value = doc.numPages
    } catch (e: any) {
      addDebug(`ERROR: ${e.message}`)
      error.value = e?.message ?? 'Failed to load PDF from buffer'
      pdfDoc.value = null
      pageCount.value = 0
    } finally {
      loading.value = false
    }
  }

  async function renderPageAtScale(
    pageNum: number,
    displayZoom: number = 1.0
  ): Promise<{ canvas: HTMLCanvasElement; displayZoom: number; renderScale: number } | null> {
    if (!pdfDoc.value) {
      addDebug(`renderPageAtScale: no pdfDoc, page ${pageNum}`)
      return null
    }
    if (pageNum < 0 || pageNum >= pdfDoc.value.numPages) {
      addDebug(`renderPageAtScale: page ${pageNum} out of range`)
      return null
    }

    try {
      // Render at devicePixelRatio × displayZoom for sharp text
      const dpr = Math.max(window.devicePixelRatio || 1, 1.5)
      const renderScale = displayZoom * dpr

      const page = await pdfDoc.value.getPage(pageNum + 1)
      const viewport = page.getViewport({ scale: renderScale })

      const canvas = document.createElement('canvas')
      canvas.width = viewport.width
      canvas.height = viewport.height
      const ctx = canvas.getContext('2d')!
      await page.render({ canvasContext: ctx, viewport }).promise

      return { canvas, displayZoom, renderScale }
    } catch (e: any) {
      addDebug(`ERROR rendering page ${pageNum}: ${e.message}`)
      return null
    }
  }

  async function getPageSize(pageNum: number): Promise<{ width: number; height: number } | null> {
    if (!pdfDoc.value) return null
    try {
      const page = await pdfDoc.value.getPage(pageNum + 1)
      const vp = page.getViewport({ scale: 1 })
      return { width: vp.width, height: vp.height }
    } catch {
      return null
    }
  }

  return {
    pdfDoc,
    pageCount,
    loading,
    error,
    debugInfo,
    loadFromUrl,
    loadFromFile,
    loadFromArrayBuffer,
    renderPageAtScale,
    getPageSize,
  }
}
