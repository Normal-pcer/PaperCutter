<template>
  <div class="layout-config">
    <div class="config-header">
      <h4>布局设置</h4>
    </div>
    <div class="config-body">
      <div class="form-group">
        <label>默认布局</label>
        <select
          :value="layoutStore.fileDefaultLayoutId"
          @change="onDefaultChange"
        >
          <option v-for="preset in layoutStore.presets" :key="preset.id" :value="preset.id">
            {{ preset.name }}
          </option>
        </select>
      </div>
      <div class="form-group">
        <label>每页布局覆盖</label>
        <div
          v-for="page in outputStore.pages"
          :key="page.pageNum"
          class="page-layout-row"
        >
          <span>页 {{ page.pageNum + 1 }}</span>
          <select
            :value="page.layoutId"
            @change="(e) => setPageLayout(page.pageNum, (e.target as HTMLSelectElement).value)"
          >
            <option v-for="preset in layoutStore.presets" :key="preset.id" :value="preset.id">
              {{ preset.name }}
            </option>
          </select>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useLayoutStore } from '../stores/layoutStore'
import { useOutputStore } from '../stores/outputStore'
import { useHistoryStore } from '../stores/historyStore'

const layoutStore = useLayoutStore()
const outputStore = useOutputStore()
const historyStore = useHistoryStore()

function onDefaultChange(e: Event) {
  const select = e.target as HTMLSelectElement
  historyStore.saveSnapshot()
  layoutStore.fileDefaultLayoutId = select.value
  outputStore.defaultLayoutId = select.value
  // Apply to all existing pages
  for (const page of outputStore.pages) {
    outputStore.setPageLayout(page.pageNum, select.value)
  }
}

function setPageLayout(pageNum: number, layoutId: string) {
  historyStore.saveSnapshot()
  outputStore.setPageLayout(pageNum, layoutId)
}
</script>

<style scoped>
.layout-config {
  background: #fff;
  border-left: 1px solid #e0e0e0;
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.config-header {
  padding: 8px 12px;
  border-bottom: 1px solid #e0e0e0;
}

.config-header h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
}

.config-body {
  padding: 12px;
  flex: 1;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #666;
  margin-bottom: 4px;
}

.form-group select {
  width: 100%;
  padding: 6px 8px;
  font-size: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
}

.page-layout-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}

.page-layout-row select {
  width: 100px;
  padding: 4px 6px;
  font-size: 11px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
</style>
