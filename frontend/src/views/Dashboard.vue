<script setup>
import { ref, onMounted } from 'vue'
import { FileUp, Users, UserPlus, RefreshCcw, Clock, Download, Package, Calendar, X, CheckCircle, AlertCircle, Info, ChevronRight, FileSpreadsheet } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import apiClient from '../api/client'

const auth = useAuthStore()
const router = useRouter()
const loadingStats = ref(true)

// Estadísticas reales
const mainStats = ref([
  { id: 1, name: 'Base Total Niños', value: '0', icon: Users, color: 'text-blue-600', bg: 'bg-blue-50', key: 'total_ninos' },
])

const visitStats = ref([
  { id: 1, name: 'Total Encontrados', value: '0', icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50', key: 'encontrados' },
  { id: 2, name: 'Total No Encontrados', value: '0', icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50', key: 'no_encontrados' },
])

const monthlyStats = ref([
  { id: 1, name: 'Nuevos', value: '0', icon: UserPlus, color: 'text-indigo-600', bg: 'bg-indigo-50', key: 'nuevos' },
  { id: 2, name: 'Existentes', value: '0', icon: RefreshCcw, color: 'text-orange-600', bg: 'bg-orange-50', key: 'existentes' },
  { id: 3, name: 'Total en Reporte', value: '0', icon: FileSpreadsheet, color: 'text-emerald-600', bg: 'bg-emerald-50', key: 'total_mes' },
])

const currentMonthName = ref('---')

onMounted(async () => {
  if (auth.user?.rol === 'admin') {
    router.push('/usuarios')
    return
  }
  await fetchStats()
})

const fetchStats = async () => {
  loadingStats.value = true
  try {
    const { data } = await apiClient.get('/ninos/stats')
    console.log('Stats received:', data)
    // Update main
    mainStats.value.forEach(s => {
      if (data.global[s.key] !== undefined) s.value = data.global[s.key].toString()
    })
    // Update visits
    visitStats.value.forEach(s => {
      if (data.global[s.key] !== undefined) s.value = data.global[s.key].toString()
    })
    // Update monthly
    monthlyStats.value.forEach(s => {
      if (data.mensual[s.key] !== undefined) s.value = data.mensual[s.key].toString()
    })
    currentMonthName.value = data.mensual.mes
  } catch (err) {
    console.error('Error fetching stats:', err)
  } finally {
    loadingStats.value = false
  }
}

const isUploading = ref(false)
const uploadStatus = ref(null)
const previewRows = ref([])
const showPreview = ref(false)
const selectedFile = ref(null)
const selectedMonth = ref(new Date().getMonth() + 1)
const selectedYear = ref(new Date().getFullYear())

// Variables para feedback de carga
const showSuccessModal = ref(false)
const showErrorModal = ref(false)
const errorMessage = ref('')
const uploadResults = ref({ nuevos: 0, repetidos: 0, total: 0 })

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    selectedFile.value = file
    handlePreview(file)
  }
}

const handlePreview = async (file) => {
  isUploading.value = true
  uploadStatus.value = 'Analizando archivo...'
  
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await apiClient.post('/excel/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    previewRows.value = response.data.registros
    showPreview.value = true
    uploadStatus.value = null
  } catch (err) {
    console.error('Preview error:', err)
    const detail = err.response?.data?.detail
    errorMessage.value = Array.isArray(detail) 
      ? detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join('\n') 
      : (detail || "Error al analizar el archivo. Verifique el formato e intente de nuevo.")
    showErrorModal.value = true
    uploadStatus.value = null
  } finally {
    isUploading.value = false
  }
}

const cancelPreview = () => {
  showPreview.value = false
  previewRows.value = []
  selectedFile.value = null
  uploadStatus.value = null
}

const confirmUpload = async () => {
  if (!selectedFile.value) return
  
  isUploading.value = true
  uploadStatus.value = 'Guardando datos en la base de datos...'
  
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('mes', selectedMonth.value)
  formData.append('anio', selectedYear.value)

  try {
    const response = await apiClient.post('/excel/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    console.log('Upload response:', response.data)
    
    // Extraer datos con fallback a 0
    const total = response.data.total_registros || 0
    const n = response.data.nuevos || 0
    const e = response.data.existentes || 0
    
    uploadResults.value = { nuevos: n, existentes: e, total: total }
    
    showPreview.value = false
    previewRows.value = []
    selectedFile.value = null
    uploadStatus.value = null
    showSuccessModal.value = true
    
    // Pequeño delay antes de refrescar estadísticas para asegurar persistencia DB
    setTimeout(fetchStats, 500)
  } catch (err) {
    console.error('Upload error:', err)
    const detail = err.response?.data?.detail
    errorMessage.value = Array.isArray(detail) 
      ? detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join('\n') 
      : (detail || "No se pudo procesar el archivo. Verifique el formato e intente de nuevo.")
    showErrorModal.value = true
    uploadStatus.value = null
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div class="space-y-6 max-w-[1600px] mx-auto">
    <!-- Header Minimal -->
    <div class="flex items-center justify-between border-b border-gray-100 pb-4">
      <div>
        <h1 class="text-3xl font-black text-gray-900 tracking-tight">Panel de Control</h1>
        <p class="text-sm text-gray-400 font-bold uppercase tracking-widest">{{ auth.user?.nombre || auth.user?.username || 'Gestión Personalizada' }}</p>
      </div>
      <div class="flex items-center gap-3 bg-white px-4 py-2 rounded-2xl shadow-sm border border-gray-50">
        <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
        <span class="text-xs font-black text-gray-500 uppercase tracking-widest">Sistema En Línea</span>
      </div>
    </div>

    <!-- Main Dashboard Grid (Balanced Two-Column Layout) -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
      
      <!-- 1. Left Column: Stats & Upload (6/12) -->
      <div class="flex flex-col gap-6">
        
        <!-- Stats Section -->
        <div class="space-y-6">
          <div class="space-y-3">
            <div class="flex items-center gap-2 px-1">
              <Package class="text-gray-400" :size="14" />
              <h2 class="text-[10px] font-black uppercase tracking-widest text-gray-400">Estadísticas Globales</h2>
            </div>
            
            <div v-if="loadingStats" class="space-y-3">
              <div class="card-minimal p-5 h-[104px] bg-gray-50 animate-pulse border-b-4 border-gray-200"></div>
            </div>
            <div v-else v-for="stat in mainStats" :key="'global-'+stat.id" class="card-minimal p-5 flex items-center gap-5 bg-white border-b-4 border-blue-400 shadow-sm transition-all hover:translate-y-[-2px]">
              <div :class="[stat.bg, stat.color, 'p-4 rounded-2xl']">
                <component :is="stat.icon" :size="32" />
              </div>
              <div>
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">{{ stat.name }}</p>
                <p class="text-4xl font-black text-gray-900 tracking-tighter">{{ stat.value }}</p>
              </div>
            </div>
          </div>

          <!-- Monthly Grouped Section -->
          <div class="space-y-3 pt-2">
            <div class="flex items-center justify-between px-1 border-l-2 border-indigo-400 pl-3">
              <div class="flex flex-col">
                <h2 class="text-[10px] font-black uppercase tracking-widest text-gray-900">Reporte Mensual</h2>
                <span class="text-[9px] font-bold text-indigo-500 uppercase tracking-widest flex items-center gap-1">
                   <Calendar :size="10" /> {{ currentMonthName }}
                </span>
              </div>
              <span class="text-[8px] font-black text-gray-300 uppercase tracking-widest">Datos del último Excel</span>
            </div>
            
            <div v-if="loadingStats" class="grid grid-cols-3 gap-3">
              <div v-for="i in 3" :key="i" class="card-minimal p-3 h-[88px] bg-gray-50 animate-pulse border-b-4 border-gray-200"></div>
            </div>
            <div v-else class="grid grid-cols-3 gap-3">
              <!-- Monthly Metrics Grouped -->
              <div v-for="stat in monthlyStats" :key="'monthly-'+stat.id" class="card-minimal p-3 flex flex-col items-center text-center gap-2 bg-white border-b-4 shadow-sm transition-all hover:translate-y-[-1px]" :class="stat.id === 1 ? 'border-indigo-400' : (stat.id === 2 ? 'border-orange-400' : 'border-emerald-400')">
                <div :class="[stat.bg, stat.color, 'p-2 rounded-xl']">
                  <component :is="stat.icon" :size="20" />
                </div>
                <div>
                  <p class="text-[8px] font-black text-gray-400 uppercase tracking-widest mb-0.5">{{ stat.name }}</p>
                  <p class="text-xl font-black text-gray-900 tracking-tighter">{{ stat.value }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Upload Zone (Reduced size) -->
        <div class="space-y-4 flex-1 flex flex-col">
          <div class="flex items-center gap-2 px-1">
            <FileUp class="text-gray-400" :size="16" />
            <h2 class="text-xs font-black uppercase tracking-widest text-gray-400">Panel de Importación</h2>
          </div>
          <div class="card-minimal p-8 flex flex-col items-center text-center justify-center relative border-dashed border-2 border-gray-100 bg-gray-50/50 flex-1 min-h-[300px] transition-all group hover:border-indigo-200">
            <input 
              type="file" 
              accept=".xlsx, .xls, .xlsm"
              @change="handleFileUpload"
              class="absolute inset-0 opacity-0 cursor-pointer z-10"
              :disabled="isUploading"
            />
            <div class="bg-white p-5 rounded-2xl shadow-sm mb-4 transition-transform group-hover:scale-110 duration-300">
              <FileUp class="text-indigo-600" :size="40" />
            </div>
            <h2 class="text-lg font-black text-gray-900 mb-1">Importar Reporte Mensual</h2>
            <p class="text-xs text-gray-500 max-w-xs mb-8 font-medium leading-relaxed">
              Sube el archivo Excel del MINSA para actualizar la base de datos automáticamente.
            </p>
            
            <div v-if="isUploading" class="flex items-center gap-3 text-xs font-black text-indigo-600">
              <RefreshCcw class="animate-spin" :size="16" /> {{ uploadStatus }}
            </div>
            <div v-else-if="uploadStatus" class="bg-black text-white px-6 py-2 rounded-xl text-[9px] font-black uppercase tracking-widest shadow-lg">
              {{ uploadStatus }}
            </div>
            <div v-else class="text-[9px] font-black uppercase tracking-widest text-gray-400 border border-gray-100 px-4 py-2 rounded-xl bg-white shadow-sm">
              Click o Arrastra (.xlsx, .xls)
            </div>
          </div>
        </div>
      </div>

      <!-- 2. Right Column: Guide (6/12) -->
      <div class="space-y-4">
        <div class="flex items-center gap-2 px-1">
          <Info class="text-gray-400" :size="16" />
          <h2 class="text-xs font-black uppercase tracking-widest text-gray-400">Guía de Formato</h2>
        </div>
        <div class="card-minimal p-8 bg-white border-l-4 border-amber-400 h-[calc(100%-32px)] flex flex-col shadow-sm">
          <div class="mb-6">
            <h3 class="text-lg font-black text-gray-900 uppercase tracking-tight mb-2">Columnas Requeridas</h3>
            <p class="text-xs text-gray-500 font-medium italic leading-relaxed">
              Asegúrese de que el archivo contenga las siguientes cabeceras:
            </p>
          </div>
          
          <div class="flex-1 grid grid-cols-2 gap-2 overflow-y-auto pr-2 custom-scroll items-start">
            <div v-for="col in [
              'DNI', 'NOMBRES COMPLETOS', 'FECHA NACIMIENTO', 'DIRECCION', 
              'RANGO EDAD', 'DNI MADRE', 'NOMBRE MADRE', 'CELULAR MADRE',
              'HISTORIA CLINICA', 'ESTABLECIMIENTO ASIGNADO', 'ESTADO VISITA',
              'FECHA', 'OBSERVACIONES', 'ACTOR SOCIAL', 'ESTABLECIMIENTO ATENCION'
            ]" :key="col" class="flex items-center justify-between p-3 bg-gray-50/80 rounded-2xl border border-gray-50 hover:bg-amber-50/50 transition-colors group">
              <span class="text-[9px] font-black text-gray-700 uppercase tracking-tighter group-hover:text-amber-700 transition-colors truncate" :title="col">{{ col }}</span>
              <CheckCircle class="text-amber-300 flex-shrink-0" :size="12" />
            </div>
          </div>
          
          <div class="mt-8 p-5 bg-amber-50/50 rounded-2xl border border-amber-100/50 shadow-sm">
             <p class="text-[10px] text-amber-900 font-bold italic leading-snug">
               * El sistema autocompleta los campos vacíos usando el historial.
             </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Preview Modal unchanged ... -->
    <Teleport to="body">
      <div v-if="showPreview" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
        <div class="bg-white rounded-3xl shadow-2xl w-full max-w-[95vw] h-[90vh] flex flex-col overflow-hidden animate-fade-in border border-gray-100">
          <div class="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
            <div>
              <h3 class="text-xl font-bold text-gray-900">Vista Previa de Carga</h3>
              <p class="text-sm text-gray-600 font-bold flex items-center gap-2">
                <span class="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-lg text-xs">{{ previewRows.length }}</span>
                Niños únicos detectados para ingresar
              </p>
            </div>
            <button @click="cancelPreview" class="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400 hover:text-gray-600">
              <X :size="24" />
            </button>
          </div>
          
          <div class="overflow-auto flex-1 p-0">
            <table class="w-full text-left border-collapse whitespace-nowrap">
              <thead class="sticky top-0 bg-white z-10 shadow-sm border-b border-gray-100">
                <tr class="text-[10px] font-extrabold text-gray-400 uppercase tracking-widest bg-gray-50/50">
                  <th class="py-3 pl-6 w-12 text-center">#</th>
                  <th class="py-3 px-4">DNI Niño</th>
                  <th class="py-3 px-4">Nombres y Apellidos</th>
                  <th class="py-3 px-4">F. Nacimiento</th>
                  <th class="py-3 px-4">EESS Asignado</th>
                  <th class="py-3 px-4">Actor Social</th>
                  <th class="py-3 px-4">Atención</th>
                  <th class="py-3 px-4">Observaciones</th>
                  <th class="py-3 pr-6 text-right">Estado</th>
                </tr>
              </thead>
              <tbody class="text-[11px] text-gray-600 font-medium divide-y divide-gray-50">
                <tr v-for="(row, idx) in previewRows" :key="idx" class="hover:bg-indigo-50/20 transition-colors">
                  <td class="py-2.5 pl-6 text-center font-bold text-gray-300">{{ idx + 1 }}</td>
                  <td class="py-2.5 px-4 font-mono font-bold text-gray-700">{{ row.dni_nino }}</td>
                  <td class="py-2.5 px-4 text-gray-900 font-bold uppercase">{{ row.nombres }}</td>
                  <td class="py-2.5 px-4 text-gray-500">{{ row.fecha_nacimiento }}</td>
                  <td class="py-2.5 px-4 text-gray-500 truncate max-w-[150px]" :title="row.establecimiento_asignado">{{ row.establecimiento_asignado }}</td>
                  <td class="py-2.5 px-4 text-gray-500 uppercase">{{ row.actor_social || '---' }}</td>
                  <td class="py-2.5 px-4 text-gray-500 truncate max-w-[120px]" :title="row.establecimiento_atencion">{{ row.establecimiento_atencion || '---' }}</td>
                  <td class="py-2.5 px-4 text-gray-500 truncate max-w-[150px]" :title="row.observacion">{{ row.observacion || '---' }}</td>
                  <td class="py-2.5 pr-6 text-right">
                    <span :class="[
                      'px-2 py-1 rounded-md text-[9px] font-black uppercase tracking-wider', 
                      row.estado === 'ENCONTRADO' ? 'bg-green-50 text-green-600' : 
                      (row.estado === 'NO ENCONTRADO' ? 'bg-red-50 text-red-600' : 'bg-gray-100 text-gray-400')
                    ]">
                      {{ row.estado }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <div class="p-5 border-t border-gray-100 bg-gray-50/50 flex flex-col sm:flex-row justify-between items-center gap-4">
            <div class="flex items-center gap-3">
              <div class="flex flex-col gap-0.5">
                <label class="text-[9px] font-black uppercase tracking-widest text-gray-400">Mes del Reporte</label>
                <select v-model="selectedMonth" class="bg-white border border-gray-200 rounded-xl px-4 py-2 text-xs font-bold focus:ring-2 focus:ring-indigo-200 outline-none">
                  <option v-for="m in 12" :key="m" :value="m">{{ new Date(0, m - 1).toLocaleString('es-PE', { month: 'long' }) }}</option>
                </select>
              </div>
              <div class="flex flex-col gap-0.5">
                <label class="text-[9px] font-black uppercase tracking-widest text-gray-400">Año</label>
                <select v-model="selectedYear" class="bg-white border border-gray-200 rounded-xl px-4 py-2 text-xs font-bold focus:ring-2 focus:ring-indigo-200 outline-none">
                  <option v-for="y in 5" :key="y" :value="2024 + y - 1">{{ 2024 + y - 1 }}</option>
                </select>
              </div>
            </div>

            <div class="flex gap-2 w-full sm:w-auto justify-end">
              <button @click="cancelPreview" class="px-5 py-2.5 rounded-xl font-bold text-gray-500 hover:bg-gray-100 text-xs transition-colors">
                Cancelar
              </button>
              <button @click="confirmUpload" class="h-12 px-8 bg-black text-white rounded-xl text-xs font-black uppercase tracking-widest hover:bg-gray-800 transition-all flex items-center gap-2 shadow-lg shadow-gray-200 active:scale-95" :disabled="isUploading || previewRows.length === 0">
                <RefreshCcw v-if="isUploading" class="animate-spin" :size="14"/>
                <FileUp v-else :size="14"/>
                {{ isUploading ? 'Cargando...' : 'Iniciar Carga' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Modal de Éxito -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showSuccessModal" class="fixed inset-0 z-[120] flex items-center justify-center p-6 bg-black/60 backdrop-blur-sm">
          <div class="bg-white rounded-[40px] max-w-sm w-full p-10 shadow-2xl space-y-8 animate-in zoom-in-95 duration-300 text-center">
            <div class="bg-green-50 w-24 h-24 rounded-full flex items-center justify-center mx-auto border-4 border-white shadow-xl">
              <CheckCircle class="text-green-500" :size="48" />
            </div>
            <div class="space-y-2">
              <h2 class="text-2xl font-black text-gray-900 tracking-tight">¡Carga Exitosa!</h2>
              <p class="text-gray-500 font-medium">El reporte se ha procesado correctamente.</p>
            </div>
            <div class="grid grid-cols-2 gap-3 bg-gray-50 p-4 rounded-3xl">
              <div class="text-center">
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Nuevos</p>
                <p class="text-xl font-black text-indigo-600">{{ uploadResults.nuevos }}</p>
              </div>
              <div class="text-center">
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Existentes</p>
                <p class="text-xl font-black text-gray-900">{{ uploadResults.existentes }}</p>
              </div>
            </div>
            <button 
              @click="showSuccessModal = false"
              class="h-16 w-full bg-black text-white rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-gray-800 transition-all shadow-xl active:scale-95"
            >
              ENTENDIDO
            </button>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Modal de Error -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showErrorModal" class="fixed inset-0 z-[120] flex items-center justify-center p-6 bg-black/60 backdrop-blur-sm">
          <div class="bg-white rounded-[40px] max-w-sm w-full p-10 shadow-2xl space-y-8 animate-in zoom-in-95 duration-300 text-center">
            <div class="bg-red-50 w-24 h-24 rounded-full flex items-center justify-center mx-auto border-4 border-white shadow-xl">
              <AlertCircle class="text-red-500" :size="48" />
            </div>
            <div class="space-y-2">
              <h2 class="text-2xl font-black text-gray-900 tracking-tight">Error de Carga</h2>
              <div class="max-h-[200px] overflow-y-auto custom-scroll px-2">
                <p class="text-gray-500 font-medium text-sm whitespace-pre-wrap">{{ errorMessage }}</p>
              </div>
            </div>
            <button 
              @click="showErrorModal = false"
              class="h-16 w-full bg-red-600 text-white rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-black transition-all shadow-xl active:scale-95"
            >
              REINTENTAR
            </button>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>
