import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Prefixes from '../views/Prefixes.vue'
import VRFs from '../views/VRFs.vue'
import VPCs from '../views/VPCs.vue'

// Read-only components
import ReadOnlyApp from '../ReadOnlyApp.vue'
import ReadOnlyHome from '../views/readonly/Home.vue'
import ReadOnlyPrefixes from '../views/readonly/Prefixes.vue'
import ReadOnlyVRFs from '../views/readonly/VRFs.vue'
import ReadOnlyVPCs from '../views/readonly/VPCs.vue'

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
    path: '/vrfs',
    name: 'VRFs',
    component: VRFs
  },
  {
    path: '/vpcs',
    name: 'VPCs',
    component: VPCs
  },
  // Read-only interface routes
  {
    path: '/readonly',
    component: ReadOnlyApp,
    children: [
      {
        path: '',
        name: 'ReadOnlyHome',
        component: ReadOnlyHome
      },
      {
        path: 'prefixes',
        name: 'ReadOnlyPrefixes',
        component: ReadOnlyPrefixes
      },
      {
        path: 'vrfs',
        name: 'ReadOnlyVRFs',
        component: ReadOnlyVRFs
      },
      {
        path: 'vpcs',
        name: 'ReadOnlyVPCs',
        component: ReadOnlyVPCs
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router

