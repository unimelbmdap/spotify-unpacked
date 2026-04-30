import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '@/views/DashboardView.vue'
import PresentationRoot from '@/views/PresentationRoot.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'presentation',
      component: PresentationRoot,
    },
    {
      path: '/upload',
      name: 'dashboard',
      component: DashboardView,
    },
    {
      path: '/donate',
      name: 'donate',
      component: () => import('@/views/DonateView.vue'),
    },
    {
      path: '/downloadsteps',
      name: 'downloadsteps',
      component: () => import('@/views/DownloadSteps.vue'),
    },
    {
      path: '/wrapped',
      name: 'wrapped',
      component: () => import('@/views/WrappedView.vue'),
    },
  ],
})

export default router
