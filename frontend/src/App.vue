<script setup>
import { useAuthStore } from './store/auth'
import { useRouter } from 'vue-router'
import { LogOut, Home, Users, Calendar, LayoutGrid, FileSpreadsheet, Settings, Loader2 } from 'lucide-vue-next'
import { ref, onMounted, onUnmounted } from 'vue'
import apiClient from './api/client'
import bgHeader from './assets/paltitas.jpg'
import logoAly from './assets/licfotosinfondo.png'

const auth = useAuthStore()
const router = useRouter()

const isGlobalProcessing = ref(false)
let pollInterval = null

const checkProcessing = async () => {
  if (!auth.isAuthenticated) return
  try {
    const { data } = await apiClient.get('/excel/history')
    isGlobalProcessing.value = data.some(item => item.estado === 'procesando')
  } catch (err) {
    console.warn('Poll skip')
  }
}

onMounted(() => {
  checkProcessing()
  pollInterval = setInterval(checkProcessing, 10000) // Cada 10s es suficiente para global
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

const logout = () => {
  auth.logout()
}
</script>

<template>
  <div class="min-h-screen flex flex-col font-minsa bg-brand-pink-100">
    <!-- Minimalist Navbar with Background Image -->
    <nav v-if="auth.isAuthenticated" 
      class="sticky top-0 z-50 border-b border-brand-pink-100 bg-cover bg-center"
      :style="{ backgroundImage: `linear-gradient(rgba(252, 232, 235, 0.9), rgba(252, 232, 235, 0.9)), url(${bgHeader})` }"
    >
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="flex justify-between h-20 items-center">
          <div class="flex items-center gap-10">
            <router-link to="/" class="flex items-center gap-3 group">
              <img :src="logoAly" alt="Logo Aly" class="h-12 w-auto object-contain group-hover:scale-110 transition-transform duration-300" />
              <div class="flex flex-col leading-none">
                <span class="font-black text-xl tracking-tighter text-gray-900">Niño Sano</span>
                <span class="text-[9px] font-black text-brand-pink-500 uppercase tracking-widest">{{ auth.user?.rol === 'admin' ? 'Administración' : 'Gestión' }} {{ auth.user?.nombre || auth.user?.username }}</span>
              </div>
            </router-link>
            <div class="hidden md:flex space-x-1">
              <template v-if="auth.user?.rol !== 'admin'">
                <router-link to="/" class="nav-link">
                  <LayoutGrid :size="18" /> Inicio
                </router-link>
                <router-link to="/ninos" class="nav-link">
                  <Users :size="18" /> Total de <br> Niños
                </router-link>
                <router-link to="/resumen" class="nav-link">
                  <Calendar :size="18" /> Resumen <br> Mensual
                </router-link>
                <router-link to="/historial" class="nav-link">
                  <FileSpreadsheet :size="18" /> Historial <br>de Cargas
                </router-link>
              </template>
              <router-link v-if="auth.user?.rol === 'admin'" to="/usuarios" class="nav-link">
                <Settings :size="18" /> Usuarios
              </router-link>
            </div>
          </div>
          <div class="flex items-center gap-6">
            <!-- Global Processing Indicator -->
            <div v-if="isGlobalProcessing" class="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-indigo-50 text-indigo-600 rounded-full animate-pulse border border-indigo-100">
              <Loader2 :size="14" class="animate-spin" />
              <span class="text-[10px] font-black uppercase tracking-widest">Procesando...</span>
            </div>

            <div class="hidden sm:flex flex-col items-end">
              <span class="text-sm font-bold text-gray-900">{{ auth.user?.nombre || auth.user?.username }}</span>
              <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">{{ auth.user?.rol || 'Gestor' }}</span>
            </div>
            <button @click="logout" class="p-2.5 text-brand-pink-500 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all">
              <LogOut :size="20" />
            </button>
          </div>
        </div>
      </div>
    </nav>

    <main :class="[$route.path === '/login' ? 'flex-grow w-full' : 'flex-grow container mx-auto px-6 py-10 max-w-[1600px]']">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <footer v-if="$route.path !== '/login'" class="py-10 text-center text-brand-pink-500/50 text-xs font-bold uppercase tracking-widest bg-white/50 border-t border-brand-pink-100/50">
      &copy; 2026 Niño Sano &bull; Gestión Personalizada
    </footer>
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

.font-minsa {
  font-family: 'Inter', sans-serif;
}

.nav-link {
  @apply px-4 py-2 rounded-xl flex items-center gap-2 text-sm font-bold text-brand-pink-500/70 hover:text-brand-pink-600 hover:bg-brand-pink-100/50 transition-all;
}

.router-link-active.nav-link {
  @apply text-brand-pink-600 bg-brand-pink-100/50;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateY(5px);
}
</style>
