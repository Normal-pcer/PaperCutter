<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <span class="app-title">PaperCutter</span>

      <!-- Upload -->
      <label class="btn btn-upload">
        上传 PDF
        <input type="file" accept=".pdf" hidden @change="onUpload" />
      </label>

      <div class="divider"></div>

      <!-- Mode -->
      <div class="mode-group">
        <button
          :class="{ active: mode === 'view' }"
          @click="$emit('update:mode', 'view')"
          title="查看模式"
        >🖐 查看</button>
        <button
          :class="{ active: mode === 'operate' }"
          @click="$emit('update:mode', 'operate')"
          title="操作模式：左侧剪切，右侧粘贴"
          :disabled="!hasFile"
        >✂ 操作</button>
      </div>

      <div class="divider"></div>

      <!-- Auto operations -->
      <div class="auto-group">
        <div class="dropdown" ref="autoCutDropdownRef">
          <button class="btn" @click="toggleAutoCutMenu" :disabled="!hasFile">
            🤖 自动剪切 ▾
          </button>
          <div v-if="autoCutMenuOpen" class="dropdown-menu">
            <div class="dd-section">内容识别</div>
            <div class="dd-item" @click="doAutoCut('content', 'page')">
              📄 本页
            </div>
            <div class="dd-item" @click="doAutoCut('content', 'all')">
              📚 全部页面
            </div>
            <div class="dd-section">图片处理</div>
            <div class="dd-item" @click="doAutoCut('image', 'page')">
              🖼 本页
            </div>
            <div class="dd-item" @click="doAutoCut('image', 'all')">
              🖼 全部页面
            </div>
          </div>
        </div>
        <button class="btn" @click="doAutoPaste" :disabled="!canAutoPaste">
          ⚡ 自动粘贴
        </button>
      </div>

      <div class="divider"></div>

      <!-- Undo / Redo -->
      <button class="btn" @click="undo" :disabled="historyStore.undoStack.length === 0" title="撤销 Ctrl+Z">
        ↩ 撤销
      </button>
      <button class="btn" @click="redo" :disabled="historyStore.redoStack.length === 0" title="重做 Ctrl+Y">
        ↪ 重做
      </button>
    </div>

    <div class="toolbar-right">
      <span v-if="zoom !== 1" class="zoom-badge">{{ Math.round(zoom * 100) }}%</span>
      <button class="btn" @click="$emit('zoomIn')">🔍+</button>
      <button class="btn" @click="$emit('zoomOut')">🔍−</button>
      <button class="btn" @click="$emit('zoomReset')">1:1</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { AppMode } from '../types'
import { useCutStore } from '../stores/cutStore'
import { useOutputStore } from '../stores/outputStore'
import { useLayoutStore } from '../stores/layoutStore'
import { useHistoryStore } from '../stores/historyStore'


const props = defineProps<{
  mode: AppMode
  zoom: number
  fileId: string
  hasFile: boolean
  autoCutLoading: boolean
}>()

const emit = defineEmits<{
  'update:mode': [mode: AppMode]
  upload: [file: File]
  autoCut: [strategy: 'content' | 'image', scope: 'page' | 'all']
  autoPaste: []
  zoomIn: []
  zoomOut: []
  zoomReset: []
  undo: []
  redo: []
}>()

const cutStore = useCutStore()
const outputStore = useOutputStore()
const layoutStore = useLayoutStore()
const historyStore = useHistoryStore()

const autoCutMenuOpen = ref(false)
const autoCutDropdownRef = ref<HTMLElement | null>(null)

const canAutoPaste = computed(() =>
  cutStore.unPastedRegions.length > 0
)

function toggleAutoCutMenu() {
  autoCutMenuOpen.value = !autoCutMenuOpen.value
}

function doAutoCut(strategy: 'content' | 'image', scope: 'page' | 'all') {
  autoCutMenuOpen.value = false
  if (!props.fileId) return
  emit('autoCut', strategy, scope)
}

function doAutoPaste() {
  emit('autoPaste')
}

function onUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    emit('upload', file)
  }
}

function undo() { emit('undo') }
function redo() { emit('redo') }

// Keyboard shortcuts
function onKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'z') {
    e.preventDefault()
    emit('undo')
  } else if (e.ctrlKey && e.key === 'y') {
    e.preventDefault()
    emit('redo')
  } else if (e.key === 'Delete' || e.key === 'Backspace') {
    // Delete selected region or paste
    if (cutStore.selectedRegionId !== null) {
      historyStore.saveSnapshot()
      cutStore.deleteRegion(cutStore.selectedRegionId)
    } else if (outputStore.selectedPasteId !== null) {
      historyStore.saveSnapshot()
      outputStore.deletePaste(outputStore.selectedPasteId)
    }
  }
}

// Close dropdown on outside click
function onDocClick(e: MouseEvent) {
  if (autoCutDropdownRef.value && !autoCutDropdownRef.value.contains(e.target as Node)) {
    autoCutMenuOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  document.addEventListener('click', onDocClick)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 14px;
  background: #fff;
  border-bottom: 2px solid #e0e0e0;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 4px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.app-title {
  font-size: 16px;
  font-weight: 700;
  color: #1976D2;
  margin-right: 8px;
  letter-spacing: -0.5px;
}

.btn {
  padding: 5px 12px;
  font-size: 12px;
  border-radius: 4px;
  border: 1px solid #ddd;
  background: #fff;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.1s;
}

.btn:hover {
  background: #f0f0f0;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-upload {
  background: #1976D2;
  color: #fff;
  border-color: #1976D2;
  cursor: pointer;
}

.btn-upload:hover {
  background: #1565C0;
}

.divider {
  width: 1px;
  height: 24px;
  background: #e0e0e0;
  margin: 0 4px;
}

.mode-group {
  display: flex;
  gap: 0;
}

.mode-group button {
  padding: 5px 14px;
  font-size: 12px;
  border: 1px solid #ddd;
  background: #fff;
  cursor: pointer;
  margin-left: -1px;
  transition: all 0.1s;
}

.mode-group button:first-child {
  border-radius: 4px 0 0 4px;
  margin-left: 0;
}

.mode-group button:last-child {
  border-radius: 0 4px 4px 0;
}

.mode-group button.active {
  background: #1976D2;
  color: #fff;
  border-color: #1976D2;
}

.auto-group {
  display: flex;
  gap: 4px;
}

.dropdown {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  z-index: 200;
  min-width: 150px;
  overflow: hidden;
}

.dd-section {
  padding: 6px 14px 2px;
  font-size: 10px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  cursor: default;
}

.dd-item {
  padding: 8px 14px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.dd-item:hover {
  background: #f0f0f0;
}

.zoom-badge {
  font-size: 11px;
  color: #888;
  margin-right: 4px;
}
</style>
