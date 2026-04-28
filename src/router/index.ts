import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '@/views/DashboardView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
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
