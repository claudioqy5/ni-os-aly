<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Search, Filter, Eye, CheckCircle, AlertCircle, ChevronRight, User, MapPin, ChevronDown, RefreshCcw, X } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import apiClient from '../api/client'

const router = useRouter()
const searchQuery = ref('')
const filterStatus = ref('Todos')
const filterEESS = ref('Todos')
const children = ref([])
const eessOptions = ref([])
const loading = ref(true)

const fetchChildren = async () => {
  try {
    const { data } = await apiClient.get('/ninos/')
    children.value = data
    // Extraer EESS únicos para el filtro
    eessOptions.value = [...new Set(data.map(c => c.establecimiento_asignado).filter(Boolean))].sort()
  } catch (err) {
    console.error('Error fetching children:', err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchChildren)

const currentPage = ref(1)
const itemsPerPage = 15

const resetFilters = () => {
  searchQuery.value = ''
  filterStatus.value = 'Todos'
  filterEESS.value = 'Todos'
  currentPage.value = 1
}

const filteredChildren = computed(() => {
  const query = searchQuery.value.toLowerCase().trim()
  return children.value.filter(child => {
    const searchFields = [
      child.dni_nino, 
      child.nombres, 
      child.dni_madre, 
      child.establecimiento_asignado,
      child.direccion,
      child.historia_clinica,
      child.rango_edad
    ].map(f => (f || '').toLowerCase())
    
    const matchesSearch = query === '' || searchFields.some(field => field.includes(query))
    
    // Filtrar por estado
    const matchesStatus = filterStatus.value === 'Todos' || 
      (child.estado || 'Pendiente').toLowerCase() === filterStatus.value.toLowerCase()

    // Filtrar por EESS
    const matchesEESS = filterEESS.value === 'Todos' || 
      child.establecimiento_asignado === filterEESS.value

    return matchesSearch && matchesStatus && matchesEESS
  })
})

// Reiniciar página cuando cambia la búsqueda
watch([searchQuery, filterStatus, filterEESS], () => {
  currentPage.value = 1
})

const totalPages = computed(() => Math.ceil(filteredChildren.value.length / itemsPerPage))

const paginatedChildren = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  const end = start + itemsPerPage
  return filteredChildren.value.slice(start, end)
})

const nextPage = () => {
  if (currentPage.value < totalPages.value) currentPage.value++
}

const prevPage = () => {
  if (currentPage.value > 1) currentPage.value--
}

const getStatusClass = (estado) => {
  const s = (estado || 'Pendiente').toLowerCase()
  if (s === 'encontrado') return 'text-green-600 bg-green-50 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider'
  if (s === 'no encontrado') return 'text-red-600 bg-red-50 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider'
  return 'text-gray-400 bg-gray-50 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider'
}

const goToDetail = (id) => {
  router.push(`/ninos/${id}`)
}

const formatDate = (dateStr) => {
  if (!dateStr || dateStr === '---') return '---'
  const parts = dateStr.split('-')
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`
  }
  return dateStr
}
</script>

<template>
  <div class="space-y-8 max-w-[95vw] mx-auto">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
      <h1 class="text-3xl font-bold text-gray-900 tracking-tight">Niños Registrados</h1>
      <div class="flex gap-4">
        <span class="text-xs font-black uppercase tracking-widest text-gray-400">Total: {{ children.length }}</span>
      </div>
    </div>

    <!-- Harmonized Search/Filter Section -->
    <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-4 mb-4 bg-white p-4 rounded-[32px] shadow-sm border border-gray-100">
      <div class="flex flex-wrap items-center gap-3">
        <h3 class="text-sm font-black text-gray-400 uppercase tracking-widest mr-2">Filtros:</h3>
        
        <!-- Filter EESS -->
        <div class="relative min-w-[200px]">
          <MapPin class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="14" />
          <select 
            v-model="filterEESS" 
            class="w-full bg-gray-50 border-none rounded-xl pl-9 pr-8 py-2.5 text-xs font-bold text-gray-700 outline-none focus:ring-2 focus:ring-brand-pink-200 appearance-none cursor-pointer"
          >
            <option value="Todos">Todos los EESS</option>
            <option v-for="eess in eessOptions" :key="eess" :value="eess">{{ eess }}</option>
          </select>
          <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" :size="14" />
        </div>

        <!-- Filter Estado -->
        <div class="relative min-w-[180px]">
          <Filter class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="14" />
          <select 
            v-model="filterStatus" 
            class="w-full bg-gray-50 border-none rounded-xl pl-9 pr-8 py-2.5 text-xs font-bold text-gray-700 outline-none focus:ring-2 focus:ring-brand-pink-200 appearance-none cursor-pointer"
          >
            <option value="Todos">Todos los Estados</option>
            <option value="Encontrado">Encontrado</option>
            <option value="No Encontrado">No Encontrado</option>            
            <option value="Pendiente">Pendiente</option>
          </select>
          <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" :size="14" />
        </div>

        <!-- Botón Quitar Filtros -->
        <button 
          v-if="searchQuery || filterStatus !== 'Todos' || filterEESS !== 'Todos'"
          @click="resetFilters"
          class="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-500 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-red-50 hover:text-red-500 transition-all active:scale-95 border border-transparent hover:border-red-100"
          title="Quitar todos los filtros"
        >
          <X :size="14" />
          <span>Quitar Filtros</span>
        </button>
      </div>

      <div class="relative w-full xl:w-80">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="16" />
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Buscar por DNI, Madre, Dirección..." 
          class="w-full pl-10 pr-4 py-2.5 rounded-xl text-xs border-none bg-gray-50 font-bold focus:ring-2 focus:ring-brand-pink-300 transition-all uppercase"
        />
      </div>
    </div>

    <!-- Detailed Table -->
    <div class="card-minimal overflow-hidden flex flex-col">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="text-[10px] font-black text-gray-600 uppercase tracking-widest border-b border-gray-100 bg-gray-50/50">
              <th class="py-3 pl-4">DNI Niño</th>
              <th class="py-3 px-2">Nombres y Apellidos</th>
              <th class="py-3 px-2">F. Nacimiento</th>
              <th class="py-3 px-2">Edad</th>
              <th class="py-3 px-2">H.C.</th>
              <th class="py-3 px-2">Dirección</th>
              <th class="py-3 px-2">Madre</th>
              <th class="py-3 px-2">Celular</th>
              <th class="py-3 px-2">EESS</th>
              <th class="py-3 pr-4 text-right">Estado</th>
            </tr>
          </thead>
          <tbody class="text-[11px] text-gray-600 font-medium divide-y divide-gray-50">
            <tr 
              v-for="child in paginatedChildren" 
              :key="child.id"
              @click="goToDetail(child.id)"
              :class="[
                'group hover:bg-brand-pink-50/20 cursor-pointer transition-colors border-l-4',
                child.es_nuevo ? 'bg-cyan-50/70 hover:bg-cyan-100/70 border-cyan-500' : 'border-transparent'
              ]"
            >
              <td class="py-3 pl-4 font-mono font-bold text-gray-900 group-hover:text-brand-pink-600 transition-colors whitespace-nowrap">
                <div class="flex items-center gap-2">
                    {{ child.dni_nino }}
                    <span v-if="child.es_nuevo" class="px-2 py-0.5 bg-cyan-500 text-white text-[8px] font-black rounded-lg uppercase tracking-widest shadow-sm">NUEVO</span>
                </div>
              </td>
              <td class="py-3 px-2 text-gray-900 font-bold leading-tight min-w-[150px]">
                {{ child.nombres }}
              </td>
              <td class="py-3 px-2 text-gray-500 font-mono whitespace-nowrap">
                {{ formatDate(child.fecha_nacimiento) }}
              </td>
              <td class="py-3 px-2 text-gray-500 whitespace-nowrap">
                {{ child.rango_edad || '---' }}
              </td>
              <td class="py-3 px-2 text-gray-500 font-mono whitespace-nowrap">
                {{ child.historia_clinica || '---' }}
              </td>
              <td class="py-3 px-2 text-gray-500 leading-tight min-w-[150px]">
                {{ child.direccion || '---' }}
              </td>
              <td class="py-3 px-2">
                <div class="flex flex-col leading-tight">
                  <span class="text-gray-900 font-bold text-[10px]">{{ child.dni_madre || 'S/D' }}</span>
                  <span class="text-gray-500 text-[9px] truncate max-w-[100px]" :title="child.nombre_madre">{{ child.nombre_madre }}</span>
                </div>
              </td>
              <td class="py-3 px-2 font-mono text-gray-500 whitespace-nowrap">
                {{ child.celular_madre || '---' }}
              </td>
              <td class="py-3 px-2 text-[10px] max-w-[120px] truncate leading-tight" :title="child.establecimiento_asignado">
                {{ child.establecimiento_asignado }}
              </td>
              <td class="py-3 pr-4 text-right">
                 <span :class="getStatusClass(child.estado)">{{ child.estado || 'Pendiente' }}</span>
              </td>
            </tr>
            
            <!-- Loading State -->
            <tr v-if="loading" class="border-none">
              <td colspan="10" class="py-20 text-center">
                <div class="flex flex-col items-center justify-center gap-4">
                  <RefreshCcw class="animate-spin text-brand-pink-500" :size="32" />
                  <p class="text-xs font-black text-gray-400 uppercase tracking-[0.2em]">Cargando niños...</p>
                </div>
              </td>
            </tr>

            <!-- No Results State -->
            <tr v-else-if="paginatedChildren.length === 0" class="border-none">
              <td colspan="10" class="py-20 text-center text-gray-400 font-medium italic">
                No se encontraron resultados para tu búsqueda.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Controls -->
      <div v-if="filteredChildren.length > 0" class="p-4 border-t border-gray-100 bg-gray-50/50 flex justify-between items-center">
        <div class="text-xs text-gray-400 font-medium">
          Mostrando {{ (currentPage - 1) * itemsPerPage + 1 }} - {{ Math.min(currentPage * itemsPerPage, filteredChildren.length) }} de {{ filteredChildren.length }}
        </div>
        <div class="flex gap-2">
          <button 
            @click="prevPage" 
            :disabled="currentPage === 1"
            class="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-bold text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Anterior
          </button>
          <span class="bg-white px-4 py-2 border border-gray-200 rounded-lg text-sm font-bold text-gray-900 flex items-center">
            {{ currentPage }} / {{ totalPages }}
          </span>
          <button 
            @click="nextPage" 
            :disabled="currentPage === totalPages"
            class="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-bold text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
