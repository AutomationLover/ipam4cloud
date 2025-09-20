import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Prefixes from '../views/Prefixes.vue'
import PrefixDetail from '../views/PrefixDetail.vue'
import VRFs from '../views/VRFs.vue'
import VPCs from '../views/VPCs.vue'
import ExportImport from '../views/ExportImport.vue'

const routes = [
  {
    path: '/',
    name: 'ReadOnlyHome',
    component: Home
  },
  {
    path: '/prefixes',
    name: 'ReadOnlyPrefixes',
    component: Prefixes
  },
  {
    path: '/prefixes/:prefixId',
    name: 'ReadOnlyPrefixDetail',
    component: PrefixDetail
  },
  {
    path: '/vrfs',
    name: 'ReadOnlyVRFs',
    component: VRFs
  },
  {
    path: '/vpcs',
    name: 'ReadOnlyVPCs',
    component: VPCs
  },
  {
    path: '/export-import',
    name: 'ReadOnlyExportImport',
    component: ExportImport
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router
