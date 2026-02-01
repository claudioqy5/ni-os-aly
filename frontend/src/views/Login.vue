<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../store/auth'
import { useRouter } from 'vue-router'
import { User, Lock, Loader2 } from 'lucide-vue-next'
import logoAly from '../assets/licfotosinfondo.png'
import fondoLogin from '../assets/fondologin.jpg'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')

const handleLogin = async () => {
  const success = await auth.login(username.value, password.value)
  if (success) {
    if (auth.user?.rol === 'admin') {
      router.push('/usuarios')
    } else {
      router.push('/')
    }
  }
}
</script>

<template>
  <div class="login-view-container min-h-screen flex items-center justify-center relative overflow-hidden">
    <!-- Fondo Estático (Sin animación por petición del usuario) -->
    <div class="fixed inset-0 z-0">
      <div 
        class="absolute inset-0 bg-cover bg-center"
        :style="{ 
          backgroundImage: `url(${fondoLogin})`
        }"
      ></div>
      <!-- Gradiente suave para eliminar "blancos" excesivos y dar profundidad -->
      <div class="absolute inset-0 bg-brand-pink-500/10 backdrop-brightness-[0.95]"></div>
    </div>

    <!-- Card de Login -->
    <div class="bg-white/40 backdrop-blur-2xl p-8 sm:p-12 rounded-[50px] shadow-[0_20px_50px_rgba(0,0,0,0.1)] w-full max-w-md border border-white/60 relative z-10 transform hover:scale-[1.01] transition-all duration-500">
      <div class="text-center mb-10">
        <div class="relative inline-block mb-6">
          <div class="absolute inset-0 bg-brand-pink-200 blur-2xl rounded-full opacity-50 scale-150 animate-pulse"></div>
          <img :src="logoAly" alt="Logo Aly" class="w-28 h-auto relative drop-shadow-2xl animate-bounce-subtle" />
        </div>

        <h1 class="text-4xl font-black text-gray-900 tracking-tighter mb-1">Niño Sano</h1>
        <p class="text-brand-pink-500 font-extrabold uppercase text-[10px] tracking-[0.2em]">Gestión Personalizada</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-6">
        <div>
          <label class="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2 px-1">Usuario</label>
          <div class="relative group">
            <span class="absolute inset-y-0 left-0 pl-4 flex items-center text-gray-400 group-focus-within:text-brand-pink-500 transition-colors">
              <User :size="18" />
            </span>
            <input 
              v-model="username"
              type="text" 
              required
              class="pl-12 w-full h-14 bg-white/50 border-2 border-transparent focus:border-brand-pink-300 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-700 shadow-sm"
              placeholder="Ingrese su usuario"
            />
          </div>
        </div>

        <div>
          <label class="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2 px-1">Contraseña</label>
          <div class="relative group">
            <span class="absolute inset-y-0 left-0 pl-4 flex items-center text-gray-400 group-focus-within:text-brand-pink-500 transition-colors">
              <Lock :size="18" />
            </span>
            <input 
              v-model="password"
              type="password" 
              required
              class="pl-12 w-full h-14 bg-white/50 border-2 border-transparent focus:border-brand-pink-300 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-700 shadow-sm"
              placeholder="••••••••"
            />
          </div>
        </div>

        <transition name="fade">
          <div v-if="auth.error" id="login-error" class="bg-red-50 text-red-600 p-4 rounded-2xl text-xs font-bold border border-red-100 flex items-center gap-3">
             <div class="w-1.5 h-10 bg-red-500 rounded-full"></div>
             {{ auth.error }}
          </div>
        </transition>

        <button 
          type="submit" 
          :disabled="auth.loading"
          class="w-full h-14 bg-gray-900 hover:bg-black text-white rounded-2xl flex items-center justify-center gap-3 text-lg font-black shadow-xl shadow-gray-200 active:scale-95 transition-all disabled:opacity-50"
        >
          <Loader2 v-if="auth.loading" class="animate-spin" :size="22" />
          {{ auth.loading ? 'Ingresando...' : 'Ingresar' }}
        </button>
      </form>

      <div class="mt-10 text-center text-[10px] font-black text-gray-400 uppercase tracking-[0.3em]">
        &copy; 2026 Niño Sano
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes bounce-subtle {
  0%, 100% { transform: translateY(0) rotate(0); }
  50% { transform: translateY(-8px) rotate(2deg); }
}

.animate-bounce-subtle {
  animation: bounce-subtle 4s ease-in-out infinite;
}

.fade-enter-active, .fade-leave-active {
  transition: all 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
