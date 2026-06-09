import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useCutStore } from './cutStore'
import { useOutputStore } from './outputStore'

interface Snapshot {
  cut: any
  output: any
}

export const useHistoryStore = defineStore('history', () => {
  const undoStack = ref<Snapshot[]>([])
  const redoStack = ref<Snapshot[]>([])
  const maxDepth = 50
  const enabled = ref(true)

  function log(msg: string) {
    console.log(`[History] ${msg} (undo: ${undoStack.value.length}, redo: ${redoStack.value.length})`)
  }

  function saveSnapshot() {
    if (!enabled.value) {
      log('saveSnapshot SKIPPED (disabled)')
      return
    }
    try {
      const cutStore = useCutStore()
      const outputStore = useOutputStore()
      const snap = {
        cut: JSON.parse(JSON.stringify(cutStore.getSnapshot())),
        output: JSON.parse(JSON.stringify(outputStore.getSnapshot())),
      }
      undoStack.value.push(snap)
      if (undoStack.value.length > maxDepth) {
        undoStack.value.shift()
      }
      redoStack.value = []
      log('saveSnapshot OK')
    } catch (e: any) {
      log(`saveSnapshot ERROR: ${e.message}`)
    }
  }

  function undo() {
    log('undo() called')
    if (undoStack.value.length === 0) {
      log('undo: stack empty, nothing to undo')
      return false
    }
    try {
      const cutStore = useCutStore()
      const outputStore = useOutputStore()

      // Save current state to redo
      redoStack.value.push({
        cut: JSON.parse(JSON.stringify(cutStore.getSnapshot())),
        output: JSON.parse(JSON.stringify(outputStore.getSnapshot())),
      })

      const snap = undoStack.value.pop()!
      enabled.value = false
      cutStore.restoreSnapshot(snap.cut)
      outputStore.restoreSnapshot(snap.output)
      enabled.value = true
      log('undo OK')
      return true
    } catch (e: any) {
      log(`undo ERROR: ${e.message}`)
      enabled.value = true
      return false
    }
  }

  function redo() {
    log('redo() called')
    if (redoStack.value.length === 0) {
      log('redo: stack empty')
      return false
    }
    try {
      const cutStore = useCutStore()
      const outputStore = useOutputStore()

      undoStack.value.push({
        cut: JSON.parse(JSON.stringify(cutStore.getSnapshot())),
        output: JSON.parse(JSON.stringify(outputStore.getSnapshot())),
      })

      const snap = redoStack.value.pop()!
      enabled.value = false
      cutStore.restoreSnapshot(snap.cut)
      outputStore.restoreSnapshot(snap.output)
      enabled.value = true
      log('redo OK')
      return true
    } catch (e: any) {
      log(`redo ERROR: ${e.message}`)
      enabled.value = true
      return false
    }
  }

  function clear() {
    undoStack.value = []
    redoStack.value = []
    log('history cleared')
  }

  return {
    undoStack,
    redoStack,
    saveSnapshot,
    undo,
    redo,
    clear,
  }
})
