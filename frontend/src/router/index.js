import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Prefixes from '../views/Prefixes.vue'
import PrefixDetail from '../views/PrefixDetail.vue'
import VRFs from '../views/VRFs.vue'
import VRFDetail from '../views/VRFDetail.vue'
import VPCs from '../views/VPCs.vue'
import VPCDetail from '../views/VPCDetail.vue'

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
    path: '/vrfs/:vrfId',
    name: 'VRFDetail',
    component: VRFDetail
  },
  {
    path: '/vpcs',
    name: 'VPCs',
    component: VPCs
  },
  {
    path: '/vpcs/:vpcId',
    name: 'VPCDetail',
    component: VPCDetail
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router

