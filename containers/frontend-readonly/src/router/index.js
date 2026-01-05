import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Prefixes from '../views/Prefixes.vue'
import PrefixDetail from '../views/PrefixDetail.vue'
import VRFs from '../views/VRFs.vue'
import VPCs from '../views/VPCs.vue'
import IPAddresses from '../views/IPAddresses.vue'

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
    path: '/ip-addresses',
    name: 'ReadOnlyIPAddresses',
    component: IPAddresses
  },
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router
