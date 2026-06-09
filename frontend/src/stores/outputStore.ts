import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { PasteItem, OutputPage, Rect } from '../types'
import { useCutStore } from './cutStore'

let pasteCounter = 0

export const useOutputStore = defineStore('output', () => {
  const pages = ref<OutputPage[]>([{ pageNum: 0, layoutId: '1up' }])
  const pastes = ref<PasteItem[]>([])
  const selectedPasteId = ref<string | null>(null)
  const defaultLayoutId = ref<string>('1up')

  const selectedPaste = computed(() =>
    pastes.value.find((p) => p.id === selectedPasteId.value) ?? null
  )

  const pastesByPage = computed(() => {
    const map = new Map<number, PasteItem[]>()
    for (const p of pastes.value) {
      const list = map.get(p.pageNum) || []
      list.push(p)
      map.set(p.pageNum, list)
    }
    return map
  })

  // ─── Page actions ──────────────────────────────────────────────────

  function addPage(afterPageNum?: number): OutputPage {
    const insertAt = afterPageNum !== undefined ? afterPageNum + 1 : pages.value.length
    const newPageNum = insertAt

    // Shift page numbers of subsequent pages
    for (const p of pages.value) {
      if (p.pageNum >= newPageNum) p.pageNum++
    }
    for (const p of pastes.value) {
      if (p.pageNum >= newPageNum) p.pageNum++
    }

    const page: OutputPage = { pageNum: newPageNum, layoutId: defaultLayoutId.value }
    pages.value.splice(insertAt, 0, page)
    pages.value.sort((a, b) => a.pageNum - b.pageNum)
    return page
  }

  function deletePage(pageNum: number) {
    // Remove pastes on this page
    const cutStore = useCutStore()
    for (const p of pastes.value.filter((p) => p.pageNum === pageNum)) {
      cutStore.markUnpasted(p.cutRegionId)
    }
    pastes.value = pastes.value.filter((p) => p.pageNum !== pageNum)
    pages.value = pages.value.filter((p) => p.pageNum !== pageNum)

    // Shift remaining page numbers down
    for (const p of pages.value) {
      if (p.pageNum > pageNum) p.pageNum--
    }
    for (const p of pastes.value) {
      if (p.pageNum > pageNum) p.pageNum--
    }

    if (pages.value.length === 0) {
      pages.value.push({ pageNum: 0, layoutId: defaultLayoutId.value })
    }
  }

  function setPageLayout(pageNum: number, layoutId: string) {
    const page = pages.value.find((p) => p.pageNum === pageNum)
    if (page) page.layoutId = layoutId
  }

  // ─── Paste actions ─────────────────────────────────────────────────

  function addPaste(cutRegionId: number, srcPageNum: number,
                    pageNum: number, srcRect: Rect, destRect: Rect): PasteItem {
    const id = `paste_${++pasteCounter}`
    const paste: PasteItem = { id, cutRegionId, srcPageNum, pageNum,
                               rect: { ...srcRect }, destRect: { ...destRect } }
    pastes.value.push(paste)

    const cutStore = useCutStore()
    cutStore.markPasted(cutRegionId)
    return paste
  }

  function movePaste(id: string, newPageNum: number, newDestRect: Rect) {
    const paste = pastes.value.find((p) => p.id === id)
    if (!paste) return
    paste.pageNum = newPageNum
    paste.destRect = { ...newDestRect }
  }

  function deletePaste(id: string) {
    const paste = pastes.value.find((p) => p.id === id)
    if (!paste) return
    const cutStore = useCutStore()
    cutStore.markUnpasted(paste.cutRegionId)
    pastes.value = pastes.value.filter((p) => p.id !== id)
    if (selectedPasteId.value === id) selectedPasteId.value = null
  }

  function selectPaste(id: string | null) {
    selectedPasteId.value = id
  }

  // ─── Snapshot for undo/redo ────────────────────────────────────────

  function getSnapshot() {
    return JSON.parse(JSON.stringify({
      pages: pages.value,
      pastes: pastes.value,
      selectedPasteId: selectedPasteId.value,
      defaultLayoutId: defaultLayoutId.value,
    }))
  }

  function restoreSnapshot(snap: ReturnType<typeof getSnapshot>) {
    pages.value = snap.pages
    pastes.value = snap.pastes
    selectedPasteId.value = snap.selectedPasteId
    defaultLayoutId.value = snap.defaultLayoutId
  }

  return {
    pages,
    pastes,
    selectedPasteId,
    selectedPaste,
    defaultLayoutId,
    pastesByPage,
    addPage,
    deletePage,
    setPageLayout,
    addPaste,
    movePaste,
    deletePaste,
    selectPaste,
    getSnapshot,
    restoreSnapshot,
  }
})
