<template>
  <div class="pdf-viewer" ref="containerRef">
    <div v-if="loading" class="status-msg">加载中...</div>
    <div v-if="error" class="status-msg error">{{ error }}</div>
    <div v-if="!loading && !error && !renderedCanvas" class="status-msg">
      请上传 PDF 文件
    </div>
    <div v-if="renderedCanvas" class="page-wrap">
      <div class="page-stack" ref="pageStackRef" :style="stackStyle">
        <canvas
          ref="pdfCanvasRef"
          class="pdf-canvas"
          :style="canvasStyle"
        ></canvas>
        <slot name="overlay"></slot>
      </div>
      <div class="page-nav">
        <button @click="$emit('prevPage')" :disabled="currentPage <= 0">◀</button>
        <span>{{ currentPage + 1 }} / {{ totalPages }}</span>
        <button @click="$emit('nextPage')" :disabled="currentPage >= totalPages - 1">▶</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'

const props = defineProps<{
  renderedCanvas: HTMLCanvasElement | null
  currentPage: number
  totalPages: number
  loading: boolean
  error: string | null
  displayWidth?: number   // CSS display width in px (if retina rendering)
  displayHeight?: number  // CSS display height in px
}>()

defineEmits<{
  prevPage: []
  nextPage: []
}>()

const pdfCanvasRef = ref<HTMLCanvasElement | null>(null)
const pageStackRef = ref<HTMLDivElement | null>(null)

const canvasStyle = computed(() => {
  if (props.displayWidth && props.displayHeight) {
    return {
      width: props.displayWidth + 'px',
      height: props.displayHeight + 'px',
    }
  }
  return {}
})

const stackStyle = computed(() => {
  if (props.displayWidth && props.displayHeight) {
    return {
      width: props.displayWidth + 'px',
      height: props.displayHeight + 'px',
    }
  }
  return {}
})

watch(
  () => props.renderedCanvas,
  async (canvas) => {
    if (!canvas) return
    await nextTick()
    const dest = pdfCanvasRef.value
    if (!dest) return
    dest.width = canvas.width
    dest.height = canvas.height
    const ctx = dest.getContext('2d')!
    ctx.clearRect(0, 0, dest.width, dest.height)
    ctx.drawImage(canvas, 0, 0)
  }
)
</script>

<style scoped>
.pdf-viewer {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  overflow: auto;
}

.page-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.page-stack {
  position: relative;
  display: inline-block;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  line-height: 0;
}

.pdf-canvas {
  display: block;
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

.status-msg {
  padding: 40px;
  color: #888;
  font-size: 14px;
}

.status-msg.error {
  color: #d32f2f;
}
</style>
