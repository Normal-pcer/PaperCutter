<template>
  <div class="region-list">
    <div class="list-header">
      <h4>选区列表</h4>
      <span class="count">{{ cutStore.regions.length }} 个</span>
    </div>
    <div class="list-body">
      <div v-if="cutStore.regions.length === 0" class="empty-hint">
        在源文件上用剪切模式绘制选区
      </div>
      <div
        v-for="region in sortedRegions"
        :key="region.id"
        class="region-item"
        :class="{
          selected: region.id === cutStore.selectedRegionId,
          pasted: region.pasted,
        }"
        @click="cutStore.selectRegion(region.id)"
        @dblclick="goToPage(region.pageNum)"
      >
        <span class="region-id">{{ region.id }}</span>
        <span class="region-info">
          页 {{ region.pageNum + 1 }}
          <span v-if="region.pasted" class="pasted-badge">✓</span>
        </span>
        <span class="region-size">
          {{ Math.round(region.rect.w) }}×{{ Math.round(region.rect.h) }}
        </span>
        <button
          class="delete-btn"
          @click.stop="deleteRegion(region.id)"
          title="删除"
        >×</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCutStore } from '../stores/cutStore'
import { useHistoryStore } from '../stores/historyStore'

const cutStore = useCutStore()
const historyStore = useHistoryStore()

const sortedRegions = computed(() =>
  [...cutStore.regions].sort((a, b) => a.id - b.id)
)

const emit = defineEmits<{
  goToPage: [pageNum: number]
}>()

function deleteRegion(id: number) {
  historyStore.saveSnapshot()
  cutStore.deleteRegion(id)
}

function goToPage(pageNum: number) {
  emit('goToPage', pageNum)
}
</script>

<style scoped>
.region-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-left: 1px solid #e0e0e0;
  width: 200px;
  flex-shrink: 0;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid #e0e0e0;
}

.list-header h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
}

.count {
  font-size: 11px;
  color: #888;
}

.list-body {
  flex: 1;
  overflow-y: auto;
}

.empty-hint {
  padding: 20px 12px;
  font-size: 12px;
  color: #aaa;
  text-align: center;
}

.region-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.1s;
}

.region-item:hover {
  background: #f5f5f5;
}

.region-item.selected {
  background: #e3f2fd;
}

.region-item.pasted {
  opacity: 0.5;
}

.region-id {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: #4CAF50;
  color: #fff;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.region-item.pasted .region-id {
  background: #9E9E9E;
}

.region-info {
  flex: 1;
  font-size: 12px;
  color: #555;
}

.region-size {
  font-size: 10px;
  color: #999;
}

.pasted-badge {
  color: #4CAF50;
  font-weight: bold;
  margin-left: 4px;
}

.delete-btn {
  background: none;
  border: none;
  color: #ccc;
  font-size: 16px;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
}

.delete-btn:hover {
  color: #d32f2f;
}
</style>
