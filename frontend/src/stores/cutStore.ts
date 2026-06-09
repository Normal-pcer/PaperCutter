import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { CutRegion, Rect } from '../types'

export const useCutStore = defineStore('cut', () => {
  const regions = ref<CutRegion[]>([])
  const nextId = ref(1)
  const selectedRegionId = ref<number | null>(null)

  const selectedRegion = computed(() =>
    regions.value.find((r) => r.id === selectedRegionId.value) ?? null
  )

  const regionsByPage = computed(() => {
    const map = new Map<number, CutRegion[]>()
    for (const r of regions.value) {
      const list = map.get(r.pageNum) || []
      list.push(r)
      map.set(r.pageNum, list)
    }
    return map
  })

  const unPastedRegions = computed(() =>
    regions.value.filter((r) => !r.pasted).sort((a, b) => a.id - b.id)
  )

  // ─── Actions ──────────────────────────────────────────────────────

  function addRegion(pageNum: number, rect: Rect): CutRegion {
    const id = nextId.value++
    const region: CutRegion = { id, pageNum, rect, pasted: false }
    regions.value.push(region)
    return region
  }

  function deleteRegion(id: number) {
    const idx = regions.value.findIndex((r) => r.id === id)
    if (idx === -1) return
    regions.value.splice(idx, 1)
    if (selectedRegionId.value === id) {
      selectedRegionId.value = null
    }
    // Re-number: IDs after the deleted one remain unchanged,
    // but nextId stays; we don't compact existing IDs.
  }

  function insertRegion(pageNum: number, rect: Rect, beforeId: number): CutRegion | null {
    // Insert a new region before the given ID, shifting IDs up
    const beforeIdx = regions.value.findIndex((r) => r.id === beforeId)
    if (beforeIdx === -1) return null

    const newId = nextId.value++
    // Shift all IDs >= beforeId up by reserving the slot conceptually
    // Actually, we give it a new ID and just insert at the position
    const region: CutRegion = { id: newId, pageNum, rect, pasted: false }
    regions.value.splice(beforeIdx, 0, region)
    return region
  }

  function moveRegion(id: number, newPageNum: number, newRect: Rect) {
    const region = regions.value.find((r) => r.id === id)
    if (!region) return
    region.pageNum = newPageNum
    region.rect = { ...newRect }
  }

  function clearPageRegions(pageNum: number) {
    regions.value = regions.value.filter((r) => r.pageNum !== pageNum)
    if (selectedRegionId.value !== null) {
      const stillExists = regions.value.some((r) => r.id === selectedRegionId.value)
      if (!stillExists) selectedRegionId.value = null
    }
  }

  function selectRegion(id: number | null) {
    selectedRegionId.value = id
  }

  function markPasted(id: number) {
    const region = regions.value.find((r) => r.id === id)
    if (region) region.pasted = true
  }

  function markUnpasted(id: number) {
    const region = regions.value.find((r) => r.id === id)
    if (region) region.pasted = false
  }

  function setRegions(newRegions: { pageNum: number; rect: Rect }[]) {
    regions.value = newRegions.map((r, i) => ({
      id: nextId.value + i,
      pageNum: r.pageNum,
      rect: { ...r.rect },
      pasted: false,
    }))
    nextId.value += newRegions.length
  }

  // ─── Snapshot for undo/redo ────────────────────────────────────────

  function getSnapshot() {
    return JSON.parse(JSON.stringify({
      regions: regions.value,
      nextId: nextId.value,
      selectedRegionId: selectedRegionId.value,
    }))
  }

  function restoreSnapshot(snap: ReturnType<typeof getSnapshot>) {
    regions.value = snap.regions
    nextId.value = snap.nextId
    selectedRegionId.value = snap.selectedRegionId
  }

  return {
    regions,
    nextId,
    selectedRegionId,
    selectedRegion,
    regionsByPage,
    unPastedRegions,
    addRegion,
    deleteRegion,
    insertRegion,
    moveRegion,
    clearPageRegions,
    selectRegion,
    markPasted,
    markUnpasted,
    setRegions,
    getSnapshot,
    restoreSnapshot,
  }
})
