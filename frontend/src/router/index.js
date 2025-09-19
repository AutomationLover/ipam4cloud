import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Prefixes from '../views/Prefixes.vue'
import PrefixDetail from '../views/PrefixDetail.vue'
import VRFs from '../views/VRFs.vue'
import VPCs from '../views/VPCs.vue'

const routes = [
  // Management interface routes
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/prefixes',
    name: 'Prefixes',
    component: Prefixes
  },
  {
    path: '/prefixes/:prefixId',
    name: 'PrefixDetail',
    component: PrefixDetail
  },
  {
    path: '/vrfs',
    name: 'VRFs',
    component: VRFs
  },
  {
    path: '/vpcs',
    name: 'VPCs',
    component: VPCs
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router

