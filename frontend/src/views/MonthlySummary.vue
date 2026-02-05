<script setup>
import { ref, onMounted } from 'vue'
import { Search, Calendar, ChevronRight, Users, CheckCircle, AlertCircle, Eye, Download, Trash2, Clock, RefreshCcw, Activity, Lock } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import apiClient from '../api/client'

const router = useRouter()

const monthlyData = ref([])
const loading = ref(true)
const searchQuery = ref('')
const eessFilter = ref('')
const statusFilter = ref('')
const nuevoFilter = ref('')
const searchTimeout = ref(null)
const globalError = ref(null)
const establishmentList = ref([])

// Variables para eliminación segura
const deletePassword = ref('')
const deleteError = ref('')

const fetchMonthlySummary = async () => {
  globalError.value = null
  try {
    const { data } = await apiClient.get('/visitas/resumen')
    // Inicializar cada mes con su propio estado de carga y lista de niños
    monthlyData.value = data.map(item => ({
      ...item,
      children: [],
      eessOptions: [],
      page: 0,
      hasMore: true,
      loadingDetails: false,
      isOpen: false,
      // Guardar valores originales del resumen para restaurarlos al cerrar
      originalEncontrados: item.encontrados,
      originalNoEncontrados: item.noEncontrados,
      originalPendientes: item.pendientes,
      originalTotalNinos: item.totalNinos
    }))
  } catch (err) {
    console.error('Error fetching monthly summary:', err)
    globalError.value = "Error al cargar el resumen mensual. Por favor, intente de nuevo."
  } finally {
    loading.value = false
  }
}

const fetchAllEstablishments = async () => {
  try {
    const { data } = await apiClient.get('/visitas/eess/all')
    establishmentList.value = data
  } catch (err) {
    console.error('Error fetching all establishments:', err)
  }
}

onMounted(() => {
  fetchMonthlySummary()
  fetchAllEstablishments()
})

const selectedMonthItem = ref(null)
const showDeleteModal = ref(false)
const reportToDelete = ref(null)

const fetchChildren = async (item, isNewSearch = false) => {
  if (item.loadingDetails) return
  globalError.value = null
  
  if (isNewSearch) {
    item.page = 0
    item.children = []
    item.hasMore = true
  }

  item.loadingDetails = true
  try {
    const limit = 50
    const skip = item.page * limit
    const { data } = await apiClient.get(`/visitas/detalle/${item.anio}/${item.mes}`, {
      params: {
        skip,
        limit,
        search: searchQuery.value || undefined,
        eess: eessFilter.value || undefined,
        estado: statusFilter.value || undefined,
        solo_nuevos: nuevoFilter.value === 'true' ? true : undefined
      }
    })
    
    item.children = [...item.children, ...data.children]
    item.hasMore = data.has_more
    item.totalAtMoment = data.total 
    item.totalChildren = data.total_children
    item.totalNinos = data.total // Actualizar el contador del encabezado con el total filtrado
    
    // Actualizar contadores dinámicos según el filtro
    item.encontrados = data.encontrados
    item.noEncontrados = data.no_encontrados
    item.pendientes = data.pendientes || 0  // Si no viene del backend, usar 0
    
    item.page++
  } catch (err) {
    console.error('Error fetching children:', err)
    globalError.value = "Error al cargar el detalle de niños de este mes."
  } finally {
    item.loadingDetails = false
  }
}

const fetchEESSOptions = async (item) => {
  try {
    const { data } = await apiClient.get(`/visitas/eess/${item.anio}/${item.mes}`)
    item.eessOptions = data
  } catch (err) {
    console.error('Error fetching EESS options:', err)
  }
}

const toggleMonth = async (item) => {
  if (selectedMonthItem.value === item) {
    // CERRAR: Restaurar valores originales y limpiar filtros
    selectedMonthItem.value = null
    item.isOpen = false
    
    // Restaurar valores originales del resumen
    item.encontrados = item.originalEncontrados
    item.noEncontrados = item.originalNoEncontrados
    item.pendientes = item.originalPendientes
    item.totalNinos = item.originalTotalNinos
    
    // Limpiar datos cargados para forzar recarga en próxima apertura
    item.children = []
    item.page = 0
    item.hasMore = true
    
    // Limpiar filtros
    searchQuery.value = ''
    eessFilter.value = ''
    statusFilter.value = ''
    nuevoFilter.value = ''
  } else {
    // ABRIR: Cerrar el anterior si existe
    if (selectedMonthItem.value) {
      selectedMonthItem.value.isOpen = false
      // Restaurar valores del mes anterior
      selectedMonthItem.value.encontrados = selectedMonthItem.value.originalEncontrados
      selectedMonthItem.value.noEncontrados = selectedMonthItem.value.originalNoEncontrados
      selectedMonthItem.value.pendientes = selectedMonthItem.value.originalPendientes
      selectedMonthItem.value.totalNinos = selectedMonthItem.value.originalTotalNinos
    }
    
    selectedMonthItem.value = item
    item.isOpen = true
    
    // Resetear filtros al cambiar de mes
    searchQuery.value = ''
    eessFilter.value = ''
    statusFilter.value = ''
    nuevoFilter.value = ''
    
    // Cargar EESS y niños
    if (item.eessOptions.length === 0) fetchEESSOptions(item)
    if (item.children.length === 0) await fetchChildren(item)
  }
}

const handleFilterChange = () => {
  if (selectedMonthItem.value) {
    fetchChildren(selectedMonthItem.value, true)
  }
}

const handleSearch = () => {
  if (searchTimeout.value) clearTimeout(searchTimeout.value)
  
  searchTimeout.value = setTimeout(() => {
    handleFilterChange()
  }, 500) // Debounce de 500ms
}

const resetFilters = () => {
  searchQuery.value = ''
  eessFilter.value = ''
  statusFilter.value = ''
  nuevoFilter.value = ''
  if (selectedMonthItem.value) {
    fetchChildren(selectedMonthItem.value, true)
  }
}

const downloadReport = async (item) => {
  const monthName = item.month.split(' ')[0]
  globalError.value = null
  try {
    const response = await apiClient.get(`/excel/export/${item.anio}/${item.mes}`, {
      params: {
        search: searchQuery.value || undefined,
        eess: eessFilter.value || undefined,
        estado: statusFilter.value || undefined,
        solo_nuevos: nuevoFilter.value === 'true' ? true : undefined
      },
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `Reporte_${monthName}_${item.anio}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (err) {
    console.error('Error downloading report:', err)
    globalError.value = "No se pudo descargar el reporte con los filtros actuales."
  }
}

const deleteReport = (item) => {
  reportToDelete.value = item
  deletePassword.value = ''
  deleteError.value = ''
  showDeleteModal.value = true
}

const confirmDelete = async () => {
  if (!reportToDelete.value) return
  if (!deletePassword.value) {
    deleteError.value = "Debes ingresar tu contraseña para continuar."
    return
  }
  
  const item = reportToDelete.value
  deleteError.value = ''
  
  try {
    await apiClient.delete(`/visitas/${item.anio}/${item.mes}`, {
      data: { password: deletePassword.value }
    })
    showDeleteModal.value = false
    fetchMonthlySummary()
    selectedMonthItem.value = null
    reportToDelete.value = null
    deletePassword.value = ''
  } catch (err) {
    console.error('Error deleting report:', err)
    if (err.response?.status === 401) {
      deleteError.value = "Contraseña incorrecta. No se pudo eliminar el reporte."
    } else {
      globalError.value = "No se pudo eliminar el reporte mensual."
    }
  }
}

const goToDetail = (id, mes, anio) => {
  router.push({
    path: `/ninos/${id}`,
    query: { mes, anio }
  })
}

const formatDate = (dateStr) => {
  if (!dateStr || dateStr === '---') return '---'
  const parts = dateStr.split('-')
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`
  }
  return dateStr
}

// La lista estática se mantiene como fallback o base común
const BASE_EESS_LIST = [
  'C.M.I. Villa María del Triunfo',
  'P.S. 12 de Junio',
  'P.S. Santa Rosa de Belén',
  'C.S. José Carlos Mariátegui',
  'P.S. Villa Limatambo',
  'P.S. Juan Carlos Soberon',
  'P.S. Buenos Aires',
  'P.S. Valle Alto',
  'P.S. Paraíso Alto',
  'P.S. Valle Bajo',
  'C.M.I. José Galvez',
  'P.S. Módulo I',
  'P.S. Nuevo Progreso',
  'P.S. Ciudad de Gosen',
  'C.S. Nueva Esperanza',
  'P.S. Módulo Virgen de Lourdes',
  'P.S. Módulo César Vallejo II',
  'P.S. Nueva Esperanza Alta',
  'C.S. Daniel A. Carrión',
  'P.S. Torres de Melgar',
  'P.S. Micaela Bastidas',
  'C.M.I. Tablada de Lurín',
  'P.S. Santa Rosa de las Conchitas',
  'P.S. David Guerrero Duarte'
]

const RANGO_EDAD_OPTIONS = [
  '0 - 3 meses',
  '3 - 5 meses',
  '5 - 12 meses'
]

// Lógica de Creación de Niño
const showAddChildModal = ref(false)
const isCreatingChild = ref(false)
const newChild = ref({
  dni_nino: '',
  nombres: '',
  fecha_nacimiento: '',
  direccion: '',
  dni_madre: '',
  nombre_madre: '',
  celular_madre: '',
  rango_edad: '',
  historia_clinica: '',
  establecimiento_asignado: '',
  // Campo para periodo inicial
  mes_inicio: new Date().getMonth() + 1,
  anio_inicio: new Date().getFullYear()
})

const resetNewChild = () => {
  newChild.value = {
    dni_nino: '', nombres: '', fecha_nacimiento: '', direccion: '',
    dni_madre: '', nombre_madre: '', celular_madre: '',
    rango_edad: '', historia_clinica: '', establecimiento_asignado: '',
    mes_inicio: new Date().getMonth() + 1,
    anio_inicio: new Date().getFullYear()
  }
}

const handleCreateChild = async () => {
  if (!newChild.value.dni_nino || !newChild.value.nombres) {
    globalError.value = "DNI y Nombres son obligatorios."
    return
  }
  
  isCreatingChild.value = true
  globalError.value = null
  
  try {
    // 1. Crear el niño
    const { data: createdChild } = await apiClient.post('/ninos/', {
      dni_nino: newChild.value.dni_nino,
      nombres: newChild.value.nombres,
      fecha_nacimiento: newChild.value.fecha_nacimiento || null,
      direccion: newChild.value.direccion,
      dni_madre: newChild.value.dni_madre,
      nombre_madre: newChild.value.nombre_madre,
      celular_madre: newChild.value.celular_madre,
      rango_edad: newChild.value.rango_edad,
      historia_clinica: newChild.value.historia_clinica,
      establecimiento_asignado: newChild.value.establecimiento_asignado
    })
    
    // 2. Crear la visita inicial para el periodo seleccionado
    const fechaVisita = `${newChild.value.anio_inicio}-${String(newChild.value.mes_inicio).padStart(2, '0')}-01`
    await apiClient.post('/visitas/', {
      nino_id: createdChild.id,
      fecha_visita: fechaVisita,
      estado: 'pendiente'
    })
    
    showAddChildModal.value = false
    resetNewChild()
    fetchMonthlySummary() // Recargar resumen para ver el nuevo registro
    
  } catch (err) {
    console.error('Error creating child:', err)
    globalError.value = err.response?.data?.detail || "No se pudo crear el registro del niño."
  } finally {
    isCreatingChild.value = false
  }
}

// Lógica de Eliminación de Niño
const showConfirmDeleteChild = ref(false)
const childToDelete = ref(null)
const isDeletingChild = ref(false)

const openDeleteChild = (child) => {
  childToDelete.value = child
  showConfirmDeleteChild.value = true
}

const confirmDeleteChild = async () => {
  if (!childToDelete.value) return
  isDeletingChild.value = true
  try {
    await apiClient.delete(`/ninos/${childToDelete.value.id}`)
    showConfirmDeleteChild.value = false
    childToDelete.value = null
    fetchMonthlySummary()
  } catch (err) {
    console.error('Error deleting child:', err)
    globalError.value = "No se pudo eliminar al niño."
  } finally {
    isDeletingChild.value = false
  }
}
</script>

<template>
  <div class="space-y-8 max-w-[1600px] mx-auto">
    <div class="flex items-center justify-between bg-white p-6 rounded-[32px] shadow-sm border border-gray-100">
      <div class="flex items-center gap-4">
        <div class="bg-brand-pink-500 p-3 rounded-2xl shadow-lg shadow-brand-pink-200">
          <Calendar class="text-white" :size="24" />
        </div>
        <h1 class="text-3xl font-black text-gray-900 tracking-tight">Resumen Mensual</h1>
      </div>
      <button @click="showAddChildModal = true" class="group flex items-center gap-3 bg-black text-white px-8 py-4 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-gray-800 transition-all active:scale-95 shadow-xl shadow-gray-200">
        <Users :size="18" />
        <span>Crear Nuevo Niño</span>
      </button>
    </div>

    <!-- Global Error Display -->
    <transition name="fade">
      <div v-if="globalError" class="p-4 bg-red-50 border border-red-100 rounded-2xl flex items-center gap-4 animate-in slide-in-from-top duration-300">
        <div class="bg-red-500 text-white p-2 rounded-xl">
          <AlertCircle :size="20" />
        </div>
        <p class="text-sm font-bold text-red-600 flex-grow">{{ globalError }}</p>
        <button @click="globalError = null" class="text-red-400 hover:text-red-600">
          <Trash2 :size="16" />
        </button>
      </div>
    </transition>

    <div class="grid grid-cols-1 gap-6">
      <div v-for="item in monthlyData" :key="item.month" class="card-minimal overflow-hidden">
        <div 
          @click="toggleMonth(item)"
          class="p-6 cursor-pointer flex items-center justify-between transition-colors hover:bg-gray-50"
        >
          <div class="flex items-center gap-6">
            <div class="bg-gray-100 p-4 rounded-2xl">
              <Calendar class="text-gray-600" :size="24" />
            </div>
            <div class="space-y-2">
              <h2 class="text-xl font-bold text-gray-800">{{ item.month }}</h2>
              <div class="flex flex-wrap items-center gap-4">
                <div class="flex items-center gap-3 px-4 py-2 bg-gray-100 rounded-xl border border-gray-200 min-w-[100px] justify-center transition-all">
                  <Users class="text-gray-400" :size="16" />
                  <div class="flex flex-col items-start font-black">
                    <span class="text-lg text-gray-700 leading-none">{{ item.totalNinos }}</span>
                    <span class="text-[8px] text-gray-400 uppercase tracking-widest mt-0.5">Niños</span>
                  </div>
                </div>
                
                <div class="flex items-center gap-3">
                  <!-- Encontrados Badge -->
                  <div class="flex items-center gap-3 px-4 py-2 bg-green-50 rounded-xl border border-green-100/40 min-w-[100px] justify-center transition-all hover:bg-green-100/50">
                    <CheckCircle class="text-green-500/50" :size="16" />
                    <div class="flex flex-col items-start">
                      <span class="text-lg font-black text-green-600 leading-none">{{ item.encontrados }}</span>
                      <span class="text-[8px] font-black text-green-600/60 uppercase tracking-widest mt-0.5">Encontrados</span>
                    </div>
                  </div>

                  <!-- No encontrados Badge -->
                  <div class="flex items-center gap-3 px-4 py-2 bg-red-50 rounded-xl border border-red-100/40 min-w-[100px] justify-center transition-all hover:bg-red-100/50">
                    <AlertCircle class="text-red-500/50" :size="16" />
                    <div class="flex flex-col items-start">
                      <span class="text-lg font-black text-red-600 leading-none">{{ item.noEncontrados }}</span>
                      <span class="text-[8px] font-black text-red-600/60 uppercase tracking-widest mt-0.5">No encontrados</span>
                    </div>
                  </div>
                  
                  <!-- Pendientes Badge -->
                  <div class="flex items-center gap-3 px-4 py-2 bg-amber-50 rounded-xl border border-amber-100/40 min-w-[100px] justify-center transition-all hover:bg-amber-100/50">
                    <Clock class="text-amber-500/50" :size="16" />
                    <div class="flex flex-col items-start">
                      <span class="text-lg font-black text-amber-600 leading-none">{{ item.pendientes || 0 }}</span>
                      <span class="text-[8px] font-black text-amber-600/60 uppercase tracking-widest mt-0.5">Pendientes</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-2">
               <button 
                  @click.stop="downloadReport(item)"
                  class="flex items-center gap-2 px-4 py-2 bg-green-50 text-green-700 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-green-100 transition-colors"
                >
                  <Download :size="14" /> EXCEL
                </button>
                <button 
                  @click.stop="deleteReport(item)"
                  class="flex items-center gap-2 px-4 py-2 bg-red-50 text-red-600 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-red-100 transition-colors"
                >
                  <Trash2 :size="14" /> ELIMINAR
                </button>
            </div>

            <ChevronRight 
              :class="['text-gray-300 transition-transform duration-300', item.isOpen ? 'rotate-90' : '']" 
              :size="24" 
            />
          </div>
        </div>

        <!-- Detail Section (Expandable) -->
        <transition name="fade">
          <div v-if="item.isOpen" class="border-t border-gray-50 bg-gray-50/30 p-6 space-y-4">
            <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-4 mb-4 bg-white p-4 rounded-3xl shadow-sm border border-gray-100">
              <div class="flex flex-wrap items-center gap-3">
                <h3 class="text-sm font-black text-gray-400 uppercase tracking-widest mr-2">Filtros:</h3>
                
                <!-- Filter EESS -->
                <select 
                  v-model="eessFilter" 
                  @change="handleFilterChange"
                  class="bg-gray-50 border-none rounded-xl px-4 py-2 text-xs font-bold text-gray-700 outline-none focus:ring-2 focus:ring-brand-pink-200 min-w-[200px]"
                >
                  <option value="">Todos los EESS</option>
                  <option v-for="opt in item.eessOptions" :key="opt" :value="opt">{{ opt }}</option>
                </select>

                <div class="h-6 w-px bg-gray-100 mx-1 hidden xl:block"></div>

                <!-- Filter Estado (Reverted to Select) -->
                <select 
                  v-model="statusFilter" 
                  @change="handleFilterChange"
                  class="bg-gray-50 border-none rounded-xl px-4 py-2 text-xs font-bold text-gray-700 outline-none focus:ring-2 focus:ring-brand-pink-200"
                >
                  <option value="">Todos los Estados</option>
                  <option value="encontrado">Encontrados</option>
                  <option value="no encontrado">No Encontrados</option>
                  <option value="pendiente">Pendientes</option>
                </select>

                <div class="h-6 w-px bg-gray-100 mx-1 hidden xl:block"></div>

                <!-- Filter: Tipo (Elegant Pills) -->
                <div class="flex items-center p-1 bg-gray-100/60 rounded-2xl gap-1">
                  <button 
                    @click="nuevoFilter = ''; handleFilterChange()"
                    :class="[
                      'px-4 py-2 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all duration-300',
                      nuevoFilter === '' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-400 hover:text-gray-600'
                    ]"
                  >
                    Total
                  </button>
                  <button 
                    @click="nuevoFilter = 'true'; handleFilterChange()"
                    :class="[
                      'px-4 py-2 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all duration-300',
                      nuevoFilter === 'true' ? 'bg-cyan-500 text-white shadow-lg shadow-cyan-200' : 'text-gray-400 hover:text-cyan-600'
                    ]"
                  >
                    Nuevos
                  </button>
                </div>

                <div class="h-6 w-px bg-gray-100 mx-1 hidden xl:block"></div>

                <!-- Botón Quitar Filtros -->
                <button 
                  v-if="searchQuery || eessFilter || statusFilter || nuevoFilter !== ''"
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
                  @input="handleSearch"
                  type="text" 
                  placeholder="Buscar DNI o nombre..." 
                  class="w-full pl-10 pr-4 py-2.5 rounded-xl text-xs border-none bg-gray-50 font-bold focus:ring-2 focus:ring-brand-pink-300 transition-all"
                />
              </div>
            </div>

            <!-- Detailed Children Table -->
            <div class="card-minimal overflow-hidden mt-4">
              <div class="overflow-x-auto relative">
                <!-- Loading Overlay -->
                <div v-if="item.loadingDetails && item.children.length === 0" class="flex flex-col items-center justify-center py-20 bg-white/50">
                  <RefreshCcw class="animate-spin text-brand-pink-500 mb-2" :size="32" />
                  <p class="text-xs font-bold text-gray-400 uppercase tracking-widest">Cargando niños...</p>
                </div>

                <table v-else class="w-full text-left border-collapse">
                  <thead>
                    <tr class="text-[9px] font-black text-gray-600 uppercase tracking-widest border-b border-gray-100 bg-gray-50/50">
                      <th class="py-3 pl-4">DNI</th>
                      <th class="py-3 px-2">Nombres y Apellidos</th>
                      <th class="py-3 px-2">F. Nacimiento</th>
                      <th class="py-3 px-2">Edad</th>
                      <th class="py-3 px-2">H.C.</th>
                      <th class="py-3 px-2">Dirección</th>
                      <th class="py-3 px-2">Madre</th>
                      <th class="py-3 px-2">Celular</th>
                      <th class="py-3 px-2">EESS</th>
                      <th class="py-3 px-2 text-right">Estado</th>
                      <th class="py-3 pr-4 text-right">Acción</th>
                    </tr>
                  </thead>
                  <tbody class="text-[11px] text-gray-600 font-medium divide-y divide-gray-100 bg-white">
                    <tr 
                      v-for="child in item.children" 
                      :key="child.id"
                      @click="goToDetail(child.id, item.mes, item.anio)"
                      :class="[
                        'group cursor-pointer transition-colors border-l-4',
                        child.es_nuevo ? 'bg-cyan-50/70 hover:bg-cyan-100/70 border-cyan-500' : 'hover:bg-brand-pink-50/20 border-transparent'
                      ]"
                    >
                      <td class="py-3 pl-4 font-mono font-bold text-gray-900 group-hover:text-brand-pink-600 transition-colors whitespace-nowrap">
                        <div class="flex flex-col gap-1">
                          <div class="flex items-center gap-2">
                            {{ child.dni }}
                            <span v-if="child.es_nuevo" class="px-2 py-0.5 bg-cyan-500 text-white text-[8px] font-black rounded-lg uppercase tracking-widest shadow-sm">NUEVO</span>
                          </div>
                          <span v-if="child.visitas_count > 1" class="text-[7px] font-black text-indigo-400 uppercase tracking-widest">
                            {{ child.visitas_count }} VISITAS EN ESTE MES
                          </span>
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
                          <span class="text-gray-900 font-bold text-[10px]">{{ child.dni_madre || '---' }}</span>
                          <span class="text-gray-500 text-[9px] truncate max-w-[100px]" :title="child.nombre_madre">{{ child.nombre_madre }}</span>
                        </div>
                      </td>
                      <td class="py-3 px-2 font-mono text-gray-500 whitespace-nowrap">
                        {{ child.celular_madre || '---' }}
                      </td>
                      <td class="py-3 px-2 text-[10px] max-w-[120px] truncate leading-tight" :title="child.establecimiento_asignado">
                        {{ child.establecimiento_asignado || '---' }}
                      </td>
                      <td class="py-3 pr-4 text-right">
                        <span :class="[
                          'px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-wider',
                          child.estado.toLowerCase() === 'encontrado' ? 'bg-green-50 text-green-600' :
                          child.estado.toLowerCase() === 'pendiente' ? 'bg-amber-50 text-amber-600' :
                          'bg-red-50 text-red-600'
                        ]">
                          {{ child.estado }}
                        </span>
                      </td>
                      <td class="py-3 pr-4 text-right">
                        <button 
                          @click.stop="openDeleteChild(child)"
                          class="p-2 rounded-xl bg-red-50 text-red-500 hover:bg-red-500 hover:text-white transition-all shadow-sm"
                          title="Eliminar Niño"
                        >
                          <Trash2 :size="14" />
                        </button>
                      </td>
                    </tr>
                    
                    <tr v-if="item.children.length === 0 && !item.loadingDetails" class="border-none">
                      <td colspan="11" class="py-12 text-center text-gray-400 font-medium italic">
                        No se encontraron registros para tu búsqueda en este mes.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Pagination Controls -->
              <div v-if="item.hasMore || item.loadingDetails" class="p-6 bg-white border-t border-gray-100 flex justify-center">
                <button 
                  @click="fetchChildren(item)"
                  :disabled="item.loadingDetails"
                  class="flex items-center gap-3 px-10 h-14 bg-gray-900 text-white rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-black transition-all disabled:opacity-50 shadow-xl shadow-gray-200"
                >
                  <RefreshCcw v-if="item.loadingDetails" class="animate-spin" :size="16" />
                  <Users v-else :size="16" />
                  {{ item.loadingDetails ? 'Cargando más...' : `Cargar más niños (${(item.totalChildren || item.total) - item.children.length} restantes)` }}
                </button>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>
    <!-- Custom Confirmation Modal -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showDeleteModal && reportToDelete" class="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/60 backdrop-blur-sm">
          <div class="bg-white rounded-[40px] max-w-md w-full p-10 shadow-2xl space-y-8 animate-in zoom-in-95 duration-300">
            <div class="flex flex-col items-center text-center space-y-6">
              <div class="w-20 h-20 bg-red-50 text-red-500 rounded-3xl flex items-center justify-center shadow-inner">
                <Trash2 :size="40" />
              </div>
              <div class="space-y-4">
                <h2 class="text-2xl font-black text-gray-900 leading-tight">¿Estás segura de eliminar todo el reporte de <span class="text-red-500">{{ reportToDelete.month }}</span>?</h2>
                <p class="text-gray-500 font-medium">Esta acción borrará todas las visitas y también a los niños que solo pertenecen a este reporte. Esta acción no se puede deshacer.</p>
              </div>
            </div>
            
            <div class="space-y-4">
              <div class="space-y-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Confirma con tu contraseña</label>
                <div class="relative">
                  <Lock class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-300" :size="18" />
                  <input 
                    v-model="deletePassword"
                    type="password"
                    placeholder="Escribe tu contraseña aquí..."
                    class="w-full h-14 pl-12 pr-4 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-red-200 transition-all"
                    @keyup.enter="confirmDelete"
                  />
                </div>
                <transition name="fade">
                  <p v-if="deleteError" class="text-[10px] font-bold text-red-500 pl-1">{{ deleteError }}</p>
                </transition>
              </div>

              <div class="flex flex-col gap-4">
                <button 
                  @click="confirmDelete"
                  class="h-16 w-full bg-red-600 text-white rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-black transition-all shadow-lg active:scale-95"
                >
                  Confirmar Eliminación
                </button>
                <button 
                  @click="showDeleteModal = false"
                  class="h-16 w-full bg-gray-50 text-gray-400 rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-gray-100 hover:text-gray-900 transition-colors active:scale-95"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      </transition>
      <!-- Modal Confirmar Eliminación Niños -->
      <transition name="fade">
        <div v-if="showConfirmDeleteChild" class="fixed inset-0 z-[110] flex items-center justify-center p-6 bg-black/60 backdrop-blur-sm">
          <div class="bg-white rounded-[40px] max-w-md w-full p-10 shadow-2xl space-y-8 animate-in zoom-in-95 duration-300">
            <div class="text-center space-y-4">
              <div class="bg-red-50 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6 border-4 border-white shadow-xl">
                <Trash2 class="text-red-500" :size="32" />
              </div>
              <h2 class="text-2xl font-black text-gray-900 leading-tight">¿Eliminar registro de niño?</h2>
              <p class="text-gray-500 font-medium">Estás a punto de borrar a <span class="text-red-500 font-bold">{{ childToDelete?.nombres }}</span>. Se eliminarán todas sus visitas asociadas permanentemente.</p>
            </div>
            
            <div class="flex flex-col gap-4">
              <button 
                @click="confirmDeleteChild"
                :disabled="isDeletingChild"
                class="h-16 w-full bg-red-600 text-white rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-black transition-all shadow-lg active:scale-95 disabled:opacity-50"
              >
                {{ isDeletingChild ? 'ELIMINANDO...' : 'SI, ELIMINAR NIÑO' }}
              </button>
              <button 
                @click="showConfirmDeleteChild = false"
                class="h-16 w-full bg-gray-50 text-gray-400 rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-gray-100 transition-colors active:scale-95"
              >
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      </transition>

      <!-- Modal Agregar Nuevo Niño -->
      <transition name="fade">
        <div v-if="showAddChildModal" class="fixed inset-0 z-[110] flex items-center justify-center p-6 bg-black/60 backdrop-blur-sm">
          <div class="bg-white rounded-[40px] max-w-2xl w-full p-10 shadow-2xl space-y-8 animate-in zoom-in-95 duration-300 max-h-[90vh] overflow-y-auto custom-scrollbar">
            <div class="flex items-center justify-between border-b border-gray-100 pb-6">
              <h2 class="text-2xl font-black text-gray-900 tracking-tight">Crear Nuevo Registro de Niño</h2>
              <button @click="showAddChildModal = false" class="text-gray-400 hover:text-gray-900 transition-colors"><X :size="24" /></button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Datos Básicos -->
              <div class="space-y-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">DNI del Niño *</label>
                <input v-model="newChild.dni_nino" placeholder="Ej: 71234567" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all" />
              </div>
              <div class="space-y-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Nombre Completo *</label>
                <input v-model="newChild.nombres" placeholder="Nombres y Apellidos" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all" />
              </div>
              <div class="space-y-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Fecha de Nacimiento</label>
                <input v-model="newChild.fecha_nacimiento" type="date" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all font-mono" />
              </div>
              <div class="space-y-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Dirección</label>
                <input v-model="newChild.direccion" placeholder="Ej: Av. Principal 123" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all" />
              </div>

              <div class="space-y-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Rango de Edad</label>
                <select v-model="newChild.rango_edad" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all appearance-none cursor-pointer">
                  <option value="">Selecciona rango...</option>
                  <option v-for="opt in RANGO_EDAD_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
                </select>
              </div>

              <!-- Madre -->
              <div class="space-y-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">DNI Madre</label>
                <input v-model="newChild.dni_madre" placeholder="DNI Madre" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all" />
              </div>
              <div class="space-y-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Nombre Madre</label>
                <input v-model="newChild.nombre_madre" placeholder="Nombre completo de la madre" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all" />
              </div>
              <div class="space-y-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Celular Madre</label>
                <input v-model="newChild.celular_madre" placeholder="Ej: 999 999 999" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all" />
              </div>

              <!-- Administrativo -->
              <div class="space-y-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Historia Clínica Nº</label>
                <input v-model="newChild.historia_clinica" placeholder="Ej: 12345" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all" />
              </div>
              <div class="space-y-2 md:col-span-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Establecimiento Asignado</label>
                <select v-model="newChild.establecimiento_asignado" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all appearance-none cursor-pointer">
                  <option value="">Selecciona EESS...</option>
                  <option v-for="opt in (establishmentList.length > 0 ? establishmentList : BASE_EESS_LIST)" :key="opt" :value="opt">{{ opt }}</option>
                </select>
              </div>

              <!-- Periodo de Asignación -->
              <div class="md:col-span-2 border-t border-gray-100 pt-6">
                <h3 class="text-xs font-black text-brand-pink-500 uppercase tracking-widest mb-4">¿En qué reporte mensual deseas asignarlo?</h3>
                <div class="grid grid-cols-2 gap-6">
                  <div class="space-y-2">
                    <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Mes</label>
                    <select v-model="newChild.mes_inicio" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 appearance-none cursor-pointer">
                      <option v-for="m in 12" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
                    </select>
                  </div>
                  <div class="space-y-2">
                    <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Año</label>
                    <select v-model="newChild.anio_inicio" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 appearance-none cursor-pointer">
                      <option :value="2025">2025</option>
                      <option :value="2026">2026</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div class="pt-6 flex flex-col gap-4">
              <button 
                @click="handleCreateChild"
                :disabled="isCreatingChild"
                class="h-16 w-full bg-black text-white rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-gray-800 transition-all shadow-xl active:scale-95 disabled:opacity-50"
              >
                <Loader2 v-if="isCreatingChild" class="animate-spin" :size="20" />
                <span v-else>GUARDAR Y ASIGNAR AL REPORTE</span>
              </button>
              <button 
                @click="showAddChildModal = false"
                class="h-16 w-full bg-gray-50 text-gray-400 rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-gray-100 hover:text-gray-900 transition-colors active:scale-95"
              >
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>
