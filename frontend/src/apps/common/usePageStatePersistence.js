import { onMounted, watch } from 'vue'

const cloneState = (state) => JSON.parse(JSON.stringify(state))

export function usePageStatePersistence(storageKey, source, options = {}) {
  const {
    deep = true,
    serialize = cloneState,
    hydrate,
    debounce = 0,
    enabled = true
  } = options

  if (!storageKey || typeof source !== 'function') {
    throw new Error('usePageStatePersistence requires a storage key and source getter')
  }

  let timer = null

  const saveState = () => {
    if (!enabled) return

    try {
      const snapshot = serialize(source())
      localStorage.setItem(storageKey, JSON.stringify(snapshot))
    } catch (error) {
      console.error(`Failed to persist page state for ${storageKey}:`, error)
    }
  }

  const scheduleSave = () => {
    if (debounce <= 0) {
      saveState()
      return
    }

    clearTimeout(timer)
    timer = setTimeout(saveState, debounce)
  }

  const clearState = () => {
    clearTimeout(timer)
    localStorage.removeItem(storageKey)
  }

  onMounted(() => {
    if (!enabled) return

    const savedState = localStorage.getItem(storageKey)
    if (!savedState) return

    try {
      const parsed = JSON.parse(savedState)
      if (hydrate) {
        hydrate(parsed)
      }
    } catch (error) {
      console.error(`Failed to restore page state for ${storageKey}:`, error)
      localStorage.removeItem(storageKey)
    }
  })

  watch(source, scheduleSave, { deep })

  return {
    saveState,
    clearState
  }
}
