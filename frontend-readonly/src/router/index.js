import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Prefixes from '../views/Prefixes.vue'
import VRFs from '../views/VRFs.vue'
import VPCs from '../views/VPCs.vue'

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
    path: '/vrfs',
    name: 'ReadOnlyVRFs',
    component: VRFs
  },
  {
    path: '/vpcs',
    name: 'ReadOnlyVPCs',
    component: VPCs
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router
