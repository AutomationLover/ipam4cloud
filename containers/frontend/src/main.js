import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// Suppress ResizeObserver loop warnings (common with Element Plus tables)
// These warnings are harmless and occur when components resize rapidly
const originalError = console.error
const originalWarn = console.warn
console.error = (...args) => {
  if (
    typeof args[0] === 'string' &&
    (args[0].includes('ResizeObserver loop limit exceeded') ||
     args[0].includes('ResizeObserver loop completed with undelivered notifications'))
  ) {
    return
  }
  originalError.apply(console, args)
}
console.warn = (...args) => {
  if (
    typeof args[0] === 'string' &&
    (args[0].includes('ResizeObserver loop limit exceeded') ||
     args[0].includes('ResizeObserver loop completed with undelivered notifications'))
  ) {
    return
  }
  originalWarn.apply(console, args)
}

const app = createApp(App)

// Register all Element Plus icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(router)
app.use(ElementPlus)
app.mount('#app')

