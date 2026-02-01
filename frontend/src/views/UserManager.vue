<script setup>
import { ref, onMounted } from 'vue'
import { UserPlus, User, Shield, Power, Trash2, Edit3, Save, X, Loader2, Key, Calendar } from 'lucide-vue-next'
import apiClient from '../api/client'
import { useAuthStore } from '../store/auth'

const auth = useAuthStore()
const users = ref([])
const loading = ref(false)
const saving = ref(false)
const showModal = ref(false)
const editingUser = ref(null)

const form = ref({
  usuario: '',
  nombre_completo: '',
  rol: 'gestor',
  is_active: 1,
  password: '',
  fecha_expiracion: ''
})

const fetchUsers = async () => {
  loading.value = true
  try {
    const { data } = await apiClient.get('/auth/users')
    users.value = data
  } catch (err) {
    console.error('Error fetching users:', err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchUsers)

const openCreate = () => {
  editingUser.value = null
  form.value = {
    usuario: '',
    nombre_completo: '',
    rol: 'gestor',
    is_active: 1,
    password: '',
    fecha_expiracion: ''
  }
  showModal.value = true
}

const openEdit = (user) => {
  editingUser.value = user
  form.value = {
    usuario: user.usuario,
    nombre_completo: user.nombre_completo,
    rol: user.rol,
    is_active: user.is_active,
    fecha_expiracion: user.fecha_expiracion || '',
    password: '' // No cargar el password
  }
  showModal.value = true
}

const saveUser = async () => {
  saving.value = true
  try {
    // Preparar datos: convertir strings vacíos de fecha en null
    const payload = { ...form.value }
    if (!payload.fecha_expiracion) payload.fecha_expiracion = null
    if (!payload.password) delete payload.password // No enviar clave si está vacía en edición

    if (editingUser.value) {
      await apiClient.put(`/auth/users/${editingUser.value.id}`, payload)
    } else {
      await apiClient.post('/auth/users', payload)
    }
    showModal.value = false
    fetchUsers()
  } catch (err) {
    const detail = err.response?.data?.detail
    const msg = Array.isArray(detail) ? detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join('\n') : detail
    alert(msg || 'Error al guardar usuario')
  } finally {
    saving.value = false
  }
}

const showDeleteModal = ref(false)
const userToDelete = ref(null)
const adminPassword = ref('')
const verifying = ref(false)

const openDeleteConfirm = (user) => {
  userToDelete.value = user
  adminPassword.value = ''
  showDeleteModal.value = true
}

const confirmDelete = async () => {
  if (!adminPassword.value) return
  
  verifying.value = true
  try {
    // 1. Verificar contraseña del admin
    await apiClient.post('/auth/verify-password', { password: adminPassword.value })
    
    // 2. Si es correcta, eliminar
    await apiClient.delete(`/auth/users/${userToDelete.value.id}`)
    showDeleteModal.value = false
    fetchUsers()
  } catch (err) {
    const detail = err.response?.data?.detail
    const msg = Array.isArray(detail) ? detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join('\n') : detail
    alert(msg || 'Contraseña incorrecta o error al eliminar')
  } finally {
    verifying.value = false
  }
}

const toggleStatus = async (user) => {
  try {
    const newStatus = user.is_active ? 0 : 1
    await apiClient.put(`/auth/users/${user.id}`, { is_active: newStatus })
    fetchUsers()
  } catch (err) {
    alert('Error al cambiar estado')
  }
}
</script>

<template>
  <div class="space-y-6 max-w-6xl mx-auto">
    <div class="flex items-center justify-between border-b border-gray-100 pb-4">
      <div>
        <h1 class="text-3xl font-black text-gray-900 tracking-tight">Gestión de Usuarios</h1>
        <p class="text-sm text-gray-400 font-bold uppercase tracking-widest">Administración de Acceso al Sistema</p>
      </div>
      <button @click="openCreate" class="btn-primary h-12 px-6 flex items-center gap-2 shadow-lg shadow-blue-100">
        <UserPlus :size="20" />
        <span>Nuevo Usuario</span>
      </button>
    </div>

    <div v-if="loading" class="flex flex-col items-center justify-center py-20 gap-4">
      <Loader2 class="animate-spin text-blue-500" :size="48" />
      <p class="text-gray-400 font-bold uppercase text-xs tracking-widest">Cargando Usuarios...</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="user in users" :key="user.id" 
        class="bg-white rounded-[32px] p-6 shadow-sm border border-gray-100 hover:shadow-xl hover:translate-y-[-4px] transition-all group relative overflow-hidden"
      >
        <!-- Badge Rol -->
        <div class="absolute top-4 right-4 capitalize px-3 py-1 rounded-full text-[10px] font-black tracking-widest border"
          :class="user.rol === 'admin' ? 'bg-indigo-50 text-indigo-600 border-indigo-100' : 'bg-gray-50 text-gray-500 border-gray-100'"
        >
          {{ user.rol }}
        </div>

        <div class="flex items-start gap-4 mb-6">
          <div class="w-14 h-14 bg-gray-50 rounded-2xl flex items-center justify-center text-gray-400 group-hover:bg-blue-50 group-hover:text-blue-500 transition-colors">
            <User :size="28" />
          </div>
          <div>
            <h3 class="font-black text-gray-900 text-lg leading-tight">{{ user.nombre_completo || 'Sin Nombre' }}</h3>
            <p class="text-blue-500 font-bold text-sm tracking-tight">@{{ user.usuario }}</p>
          </div>
        </div>

        <div class="space-y-3 mb-6">
          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-2xl border border-gray-50">
            <span class="text-[9px] font-black text-gray-400 uppercase tracking-widest">Estado</span>
            <span :class="user.is_active ? 'text-green-600' : 'text-red-500'" class="text-[10px] font-black uppercase tracking-widest flex items-center gap-1">
              <div :class="user.is_active ? 'bg-green-500' : 'bg-red-500'" class="w-1.5 h-1.5 rounded-full"></div>
              {{ user.is_active ? 'Activo' : 'Inactivo' }}
            </span>
          </div>
          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-2xl border border-gray-50">
            <span class="text-[9px] font-black text-gray-400 uppercase tracking-widest">Creado</span>
            <span class="text-[10px] font-black text-gray-700 uppercase">{{ new Date(user.created_at).toLocaleDateString() }}</span>
          </div>
          <div class="flex items-center justify-between p-3 rounded-2xl border transition-colors"
            :class="user.fecha_expiracion && new Date(user.fecha_expiracion) < new Date() ? 'bg-red-50 border-red-100' : 'bg-gray-50 border-gray-50'"
          >
            <span class="text-[9px] font-black text-gray-400 uppercase tracking-widest">Expira</span>
            <span class="text-[10px] font-black uppercase tracking-widest flex items-center gap-1"
              :class="user.fecha_expiracion && new Date(user.fecha_expiracion) < new Date() ? 'text-red-600' : 'text-gray-700'"
            >
              {{ user.fecha_expiracion ? new Date(user.fecha_expiracion + 'T00:00:00').toLocaleDateString() : 'Nunca' }}
              <Calendar v-if="user.fecha_expiracion && new Date(user.fecha_expiracion) < new Date()" :size="10" />
            </span>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-2 pt-4 border-t border-gray-50">
          <button @click="openEdit(user)" class="h-10 border border-gray-100 rounded-xl flex items-center justify-center gap-2 text-xs font-black text-gray-500 hover:bg-gray-50 transition-all uppercase tracking-widest">
            <Edit3 :size="14" /> Editar
          </button>
          <button @click="openDeleteConfirm(user)" 
            v-if="user.id !== auth.user.id"
            class="h-10 border border-red-50 rounded-xl flex items-center justify-center gap-2 text-xs font-black text-red-400 hover:bg-red-50 transition-all uppercase tracking-widest">
            <Trash2 :size="14" /> Eliminar
          </button>
        </div>

        <button @click="toggleStatus(user)" class="absolute bottom-6 right-6 p-2 text-gray-300 hover:text-blue-500 transition-colors" title="Alternar Estado">
          <Power :size="16" />
        </button>
      </div>
    </div>

    <!-- Modal Formulario -->
    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
        <div class="bg-white rounded-[40px] shadow-2xl w-full max-w-md animate-in zoom-in-95 duration-300 overflow-hidden">
          <div class="p-8 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
            <div>
              <h3 class="text-xl font-black text-gray-900 tracking-tight">{{ editingUser ? 'Editar Usuario' : 'Nuevo Usuario' }}</h3>
              <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Credenciales y Permisos</p>
            </div>
            <button @click="showModal = false" class="p-2 hover:bg-gray-200 rounded-full transition-colors text-gray-400">
              <X :size="24" />
            </button>
          </div>

          <form @submit.prevent="saveUser" class="p-8 space-y-6">
            <div class="space-y-4">
              <!-- Nombre Completo -->
              <div>
                <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 pl-1">Nombre Completo</label>
                <input v-model="form.nombre_completo" type="text" required class="form-input h-12" placeholder="Ej: Alicia Yapu" />
              </div>

              <!-- Usuario -->
              <div>
                <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 pl-1">Nombre de Usuario</label>
                <div class="relative">
                  <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400 font-black text-xs italic">@</span>
                  <input v-model="form.usuario" type="text" required class="form-input h-12 pl-10" placeholder="usuario" :disabled="!!editingUser" />
                </div>
              </div>

              <!-- Password -->
              <div>
                <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 pl-1">
                  {{ editingUser ? 'Nueva Contraseña (Opcional)' : 'Contraseña' }}
                </label>
                <div class="relative">
                  <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400">
                    <Key :size="16" />
                  </span>
                  <input v-model="form.password" type="password" :required="!editingUser" class="form-input h-12 pl-10" placeholder="••••••••" />
                </div>
              </div>

              <!-- Rol, Estado y Expiración -->
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 pl-1">Rol</label>
                  <select v-model="form.rol" class="form-input h-12 text-xs font-bold appearance-none">
                    <option value="gestor">Gestor</option>
                    <option value="admin">Administrador</option>
                  </select>
                </div>
                <div>
                  <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 pl-1">Estado Acceso</label>
                  <select v-model="form.is_active" class="form-input h-12 text-xs font-bold">
                    <option :value="1">Activo</option>
                    <option :value="0">Bloqueado</option>
                  </select>
                </div>
              </div>

              <!-- Fecha de Expiración -->
              <div>
                <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1 pl-1">Fecha de Expiración (Opcional)</label>
                <div class="relative">
                  <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400">
                    <Calendar :size="16" />
                  </span>
                  <input v-model="form.fecha_expiracion" type="date" class="form-input h-12 pl-10" />
                </div>
                <p class="text-[9px] text-gray-400 mt-1 pl-1">El usuario se bloqueará automáticamente al llegar esta fecha.</p>
              </div>
            </div>

            <div class="pt-6 flex gap-3">
              <button type="button" @click="showModal = false" class="flex-1 h-14 rounded-2xl font-black text-xs uppercase tracking-widest text-gray-400 hover:bg-gray-50 transition-all">
                Cancelar
              </button>
              <button type="submit" :disabled="saving" class="flex-[2] h-14 bg-black text-white rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-gray-800 transition-all flex items-center justify-center gap-2 shadow-xl shadow-gray-200">
                <Loader2 v-if="saving" class="animate-spin" :size="16" />
                <Save v-else :size="16" />
                {{ saving ? 'Guardando...' : 'Guardar Usuario' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Modal Confirmación Eliminación -->
    <Teleport to="body">
      <div v-if="showDeleteModal" class="fixed inset-0 z-[110] flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
        <div class="bg-white rounded-[40px] shadow-2xl w-full max-w-md animate-in zoom-in-95 duration-300 overflow-hidden border border-red-100">
          <div class="p-8 bg-red-50/50 flex flex-col items-center text-center">
            <div class="w-16 h-16 bg-red-100 rounded-3xl flex items-center justify-center text-red-600 mb-4">
              <Trash2 :size="32" />
            </div>
            <h3 class="text-xl font-black text-gray-900 tracking-tight">Confirmar Eliminación</h3>
            <p class="text-xs font-bold text-red-500 uppercase tracking-widest mt-1">Acción Irreversible</p>
            <p class="text-sm text-gray-500 mt-4 px-4">
              Estás a punto de eliminar al usuario <span class="font-black text-gray-900">@{{ userToDelete?.usuario }}</span> y toda su información (niños y visitas).
            </p>
          </div>

          <form @submit.prevent="confirmDelete" class="p-8 space-y-6">
            <div>
              <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 pl-1">Confirme su Contraseña de Administrador</label>
              <div class="relative">
                <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400">
                  <Key :size="18" />
                </span>
                <input v-model="adminPassword" type="password" required class="form-input h-14 pl-10 border-red-100 focus:ring-red-50" placeholder="••••••••" />
              </div>
            </div>

            <div class="flex gap-3">
              <button type="button" @click="showDeleteModal = false" class="flex-1 h-14 rounded-2xl font-black text-xs uppercase tracking-widest text-gray-400 hover:bg-gray-50 transition-all">
                Cancelar
              </button>
              <button type="submit" :disabled="verifying" class="flex-[2] h-14 bg-red-600 text-white rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-red-700 transition-all flex items-center justify-center gap-2 shadow-xl shadow-red-100">
                <Loader2 v-if="verifying" class="animate-spin" :size="16" />
                <Trash2 v-else :size="16" />
                {{ verifying ? 'Verificando...' : 'Borrar Permanentemente' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.form-input {
  @apply w-full bg-gray-50 border border-gray-100 rounded-2xl px-4 text-sm font-bold text-gray-900 outline-none focus:ring-4 focus:ring-blue-100 focus:border-blue-300 transition-all;
}
</style>
