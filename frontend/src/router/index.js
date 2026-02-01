import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import UploadHistory from '../views/UploadHistory.vue'
import ChildrenList from '../views/ChildrenList.vue'
import ChildDetail from '../views/ChildDetail.vue'
import ChildHistory from '../views/ChildHistory.vue'
import MonthlySummary from '../views/MonthlySummary.vue'
import UserManager from '../views/UserManager.vue'
import { useAuthStore } from '../store/auth'

const routes = [
    { path: '/login', name: 'Login', component: Login, meta: { public: true } },
    { path: '/', name: 'Dashboard', component: Dashboard },
    { path: '/historial', name: 'UploadHistory', component: UploadHistory },
    { path: '/ninos', name: 'ChildrenList', component: ChildrenList },
    { path: '/ninos/:id/:visitaId?', name: 'ChildDetail', component: ChildDetail, props: true },
    { path: '/resumen', name: 'MonthlySummary', component: MonthlySummary },
    { path: '/usuarios', name: 'UserManager', component: UserManager, meta: { requiresAdmin: true } },
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach((to, from, next) => {
    const auth = useAuthStore()
    if (!to.meta.public && !auth.isAuthenticated) {
        next('/login')
    } else if (to.name === 'Login' && auth.isAuthenticated) {
        next('/')
    } else if (to.meta.requiresAdmin && auth.user?.rol !== 'admin') {
        next('/')
    } else {
        next()
    }
})

export default router
