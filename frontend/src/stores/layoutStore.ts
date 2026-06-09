import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { LayoutPreset, Rect } from '../types'
import { A4_WIDTH, A4_HEIGHT, DEFAULT_MARGIN } from '../types'

export const useLayoutStore = defineStore('layout', () => {
  const presets = ref<LayoutPreset[]>([
    {
      id: '1up',
      name: '一页一题',
      slots: [
        { x: DEFAULT_MARGIN, y: DEFAULT_MARGIN,
          w: A4_WIDTH - 2 * DEFAULT_MARGIN,
          h: A4_HEIGHT - 2 * DEFAULT_MARGIN },
      ],
    },
    {
      id: '2up',
      name: '一页两题',
      slots: [
        { x: DEFAULT_MARGIN, y: DEFAULT_MARGIN,
          w: A4_WIDTH - 2 * DEFAULT_MARGIN,
          h: (A4_HEIGHT - 3 * DEFAULT_MARGIN) / 2 },
        { x: DEFAULT_MARGIN, y: (A4_HEIGHT + DEFAULT_MARGIN) / 2,
          w: A4_WIDTH - 2 * DEFAULT_MARGIN,
          h: (A4_HEIGHT - 3 * DEFAULT_MARGIN) / 2 },
      ],
    },
    {
      id: 'free',
      name: '自由布局',
      slots: [],
    },
  ])

  const fileDefaultLayoutId = ref('1up')

  function getPreset(id: string): LayoutPreset | undefined {
    return presets.value.find((p) => p.id === id)
  }

  function getSlots(layoutId: string): Rect[] {
    const preset = getPreset(layoutId)
    return preset ? [...preset.slots] : []
  }

  return {
    presets,
    fileDefaultLayoutId,
    getPreset,
    getSlots,
  }
})
