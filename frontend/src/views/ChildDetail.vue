<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  ArrowLeft, Save, User, Activity, MapPin, 
  Calendar, FileText, Loader2, Heart, 
  ChevronDown, Clock, X, Edit2, Check, Trash2, Plus, Download, FileDown
} from 'lucide-vue-next'
import apiClient from '../api/client'

const props = defineProps({
  id: [String, Number],
  visitaId: [String, Number]
})

const router = useRouter()
const isSaving = ref(false)
const loading = ref(true)
const message = ref('')
const showFullDetails = ref(false)
const activeTab = ref('menor')
const route = useRoute()
const editingVisitaId = ref(null)
const showFilteredOnly = ref(!!(route.query.mes && route.query.anio))
const showAddVisitaModal = ref(false)
const showDeleteVisitaModal = ref(false)
const visitaToDelete = ref(null)
const isDeletingVisita = ref(null)

const isDownloadingPdf = ref(false)

const downloadPDF = async () => {
  isDownloadingPdf.value = true
  try {
    const response = await apiClient.get(`/ninos/${props.id}/pdf`, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `Historial_${child.value.dni_nino}.pdf`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (err) {
    console.error('Error downloading PDF:', err)
    alert('No se pudo generar el PDF en este momento')
  } finally {
    isDownloadingPdf.value = false
  }
}

const newVisita = ref({
  fecha_visita: new Date().toISOString().split('T')[0],
  estado: 'encontrado',
  observacion: '',
  establecimiento_atencion: '',
  actor_social: ''
})

const filterPeriod = computed(() => {
  if (route.query.mes && route.query.anio) {
    return {
      mes: parseInt(route.query.mes),
      anio: parseInt(route.query.anio),
      label: `${new Date(route.query.anio, route.query.mes - 1).toLocaleString('es-ES', { month: 'long' })} ${route.query.anio}`
    }
  }
  return null
})

const filteredVisitas = computed(() => {
  if (!child.value.visitas) return []
  if (!showFilteredOnly.value || !filterPeriod.value) {
    return child.value.visitas
  }
  
  return child.value.visitas.filter(v => {
    const d = new Date(v.fecha_visita + 'T00:00:00')
    return (d.getMonth() + 1) === filterPeriod.value.mes && d.getFullYear() === filterPeriod.value.anio
  })
})

const groupedVisitas = computed(() => {
  const groups = {}
  
  filteredVisitas.value.forEach(visita => {
    const d = new Date(visita.fecha_visita + 'T00:00:00')
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const label = d.toLocaleString('es-ES', { month: 'long', year: 'numeric' })
    
    if (!groups[key]) {
      groups[key] = { label, visits: [] }
    }
    groups[key].visits.push(visita)
  })
  
  return Object.keys(groups)
    .sort((a, b) => b.localeCompare(a))
    .map(key => ({
      ...groups[key],
      visits: groups[key].visits.sort((a, b) => new Date(b.fecha_visita) - new Date(a.fecha_visita))
    }))
})

const child = ref({
  id: props.id,
  dni_nino: '',
  nombres: '',
  fecha_nacimiento: '',
  direccion: '',
  dni_madre: '',
  nombre_madre: '',
  celular_madre: '',
  periodo: '---',
  actor_social: '' // Mantener temporalmente para la visita actual en el editor
})

// Variables temporales para edición inline
const inlineBuffer = ref({})

const allEessOptions = ref([])

const STATIC_EESS_LIST = [
  'CMI José Gálvez', 'CMI Tablada de Lurín', 'CMI Daniel Alcides Carrión',
  'CS Villa María del Triunfo', 'CS San Francisco de la Cruz', 'CS Nueva Esperanza',
  'CS Mariano Melgar', 'CS José Carlos Mariátegui', 'CS Micaela Bastidas',
  'CSMC Yuyay Wasi', 'CSMC Nuevo Milenio', 'CMI Juan Pablo II', 'CMI San José',
  'CMI Ollantay', 'CMI Manuel Barreto', 'CS San Juan de Miraflores',
  'CS Leoncio Prado', 'CS Jesús Poderoso', 'CS Pamplona Alta', 'CS Trébol Azul',
  'CS María Auxiliadora (No confundir con el hospital)', 'CS Laderas de Villa',
  'CSMC Javier Mariátegui Chiappe', 'CSMC San Juan de Miraflores', 'CSMC Cali',
  'CMI César López Silva (El Salvador)', 'CS Brisas de Pachacámac', 'CS Pastor Sevilla',
  'CS San Martín de Porres', 'CS Héroes del Cenepa', 'CS Lomo de Corvina',
  'CS Oasis de Villa', 'CSMC Villa El Salvador', 'CSMC San José', 'CMI Lurín',
  'CMI Portada de Manchay (Pachacámac)', 'CS Pachacámac (Cercado)',
  'CS Julio C. Tello (Lurín)', 'CS Punta Hermosa', 'CS Punta Negra',
  'CS San Bartolo', 'CS Santa María del Mar', 'CS Pucusana',
  'CS Huertos de Manchay', 'CSMC Lurín', 'CSMC Portada de Manchay',
  'CSMC Balnearios del Sur (Punta Hermosa)', 'CMI Virgen del Carmen (Chorrillos)',
  'CMI Buenos Aires de Villa', 'CS San Genaro de Villa', 'CS Delicias de Villa',
  'CS Chorrillos I y II', 'CS Barranco (Distrito de Barranco)',
  'CS Santiago de Surco (Surco Pueblo)', 'CS San Roque', 'CS Los Próceres',
  'CSMC Barranco', 'CSMC Chorrillos', 'CSMC Virgen del Carmen',
  'CSMC Víctor Fran (Surco)', 'CSMC Santiago de Surco', 'CS San Borja',
  'CS Surquillo', 'CS San Juan de Dios', 'CS Todos los Santos',
  'CS Casas Huertas', 'CSMC San Borja', 'CSMC Surquillo'
]

const fetchChildData = async () => {
  try {
    const { data } = await apiClient.get(`/ninos/${props.id}`)
    let targetVisita = null
    
    // Si hay un visitaId específico en la ruta
    if (props.visitaId && data.visitas) {
      targetVisita = data.visitas.find(v => String(v.id) === String(props.visitaId))
    }
    
    // Si no hay visitaId o no se encontró, tomar la más reciente
    if (!targetVisita && data.visitas && data.visitas.length > 0) {
      targetVisita = [...data.visitas].sort((a, b) => new Date(b.fecha_visita + 'T00:00:00') - new Date(a.fecha_visita + 'T00:00:00'))[0]
    }

    const estadoReal = targetVisita?.estado?.toLowerCase() === 'encontrado' ? 'Encontrado' : (targetVisita?.estado ? 'No Encontrado' : 'Pendiente')
    
    child.value = { 
      ...data, 
      estado: estadoReal,
      observacion: targetVisita?.observacion || '',
      establecimiento_atencion: targetVisita?.establecimiento_atencion || '',
      actor_social: targetVisita?.actor_social || '',
      fecha_visita: targetVisita?.fecha_visita || '',
      periodo: targetVisita ? `${new Date(targetVisita.fecha_visita + 'T00:00:00').getMonth() + 1}/${new Date(targetVisita.fecha_visita + 'T00:00:00').getFullYear()}` : 'Sin periodo',
      current_visita_obj: targetVisita
    }
  } catch (err) {
    console.error('Error fetching child data:', err)
    message.value = 'Error al cargar los datos del niño'
  } finally {
    loading.value = false
  }
}

const fetchAllEess = async () => {
  try {
    const { data } = await apiClient.get('/visitas/eess/all')
    allEessOptions.value = data
  } catch (err) {
    console.error(err)
  }
}

onMounted(() => {
  fetchChildData()
  fetchAllEess()
})

const startInlineEdit = (visita) => {
    editingVisitaId.value = visita.id
    inlineBuffer.value = { ...visita }
    // Convertir estado para el select
    inlineBuffer.value.estado = visita.estado?.toLowerCase() === 'encontrado' ? 'encontrado' : 'no encontrado'
}

const cancelInlineEdit = () => {
    editingVisitaId.value = null
    inlineBuffer.value = {}
}

const saveInlineVisita = async (id) => {
    try {
        await apiClient.put(`/visitas/${id}`, {
            nino_id: props.id,
            estado: inlineBuffer.value.estado,
            observacion: inlineBuffer.value.observacion,
            establecimiento_atencion: inlineBuffer.value.establecimiento_atencion,
            actor_social: inlineBuffer.value.actor_social,
            fecha_visita: inlineBuffer.value.fecha_visita
        })
        message.value = 'Visita actualizada'
        editingVisitaId.value = null
        await fetchChildData()
        setTimeout(() => message.value = '', 3000)
    } catch (err) {
        message.value = 'Error al actualizar visita'
    }
}

const deleteVisita = (visita) => {
  visitaToDelete.value = visita
  showDeleteVisitaModal.value = true
}

const confirmDeleteVisita = async () => {
  if (!visitaToDelete.value) return
  
  const id = visitaToDelete.value.id
  isDeletingVisita.value = id
  try {
    await apiClient.delete(`/visitas/${id}`)
    message.value = 'Visita eliminada con éxito'
    showDeleteVisitaModal.value = false
    await fetchChildData()
    setTimeout(() => message.value = '', 3000)
  } catch (err) {
    console.error(err)
    message.value = 'Error al eliminar la visita'
  } finally {
    isDeletingVisita.value = null
    visitaToDelete.value = null
  }
}

const saveNewVisita = async () => {
  if (!newVisita.value.fecha_visita) {
    alert('La fecha de visita es obligatoria')
    return
  }

  isSaving.value = true
  try {
    await apiClient.post('/visitas/', {
      ...newVisita.value,
      nino_id: props.id
    })
    message.value = 'Nueva visita registrada'
    showAddVisitaModal.value = false
    await fetchChildData()
    // Resetear form
    newVisita.value = {
      fecha_visita: new Date().toISOString().split('T')[0],
      estado: 'encontrado',
      observacion: '',
      establecimiento_atencion: '',
      actor_social: ''
    }
    setTimeout(() => message.value = '', 3000)
  } catch (err) {
    console.error(err)
    message.value = 'Error al registrar la visita'
  } finally {
    isSaving.value = false
  }
}

const handleSave = async () => {
  isSaving.value = true
  message.value = ''
  try {
    // 1. Actualizar datos del niño
    await apiClient.put(`/ninos/${props.id}`, {
      dni_nino: child.value.dni_nino,
      nombres: child.value.nombres,
      fecha_nacimiento: child.value.fecha_nacimiento,
      direccion: child.value.direccion,
      dni_madre: child.value.dni_madre,
      nombre_madre: child.value.nombre_madre,
      celular_madre: child.value.celular_madre,
      rango_edad: child.value.rango_edad,
      historia_clinica: child.value.historia_clinica,
      establecimiento_asignado: child.value.establecimiento_asignado,
    })

    message.value = 'Datos actualizados con éxito'
    setTimeout(() => message.value = '', 3000)
  } catch (err) {
    message.value = 'Error al guardar los cambios'
  } finally {
    isSaving.value = false
  }
}

const toggleStatus = () => {
  child.value.estado = child.value.estado === 'Encontrado' ? 'No Encontrado' : 'Encontrado'
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
  <div class="child-detail-container">
    <div v-if="loading" class="flex items-center justify-center min-h-[60vh]">
        <Loader2 class="animate-spin text-brand-pink-500" :size="48" />
    </div>
    
    <div v-else class="max-w-6xl mx-auto space-y-10 pb-20 px-4 sm:px-6">
      <!-- Barra Superior -->
      <div class="flex items-center justify-between pt-4">
        <button @click="router.back()" class="flex items-center gap-3 text-gray-400 hover:text-black transition-all text-xs font-black uppercase tracking-widest">
          <ArrowLeft :size="18" /> Regresar
        </button>
        <transition name="fade">
          <div v-if="message" class="bg-black text-white px-6 py-2 rounded-full text-[10px] font-black uppercase tracking-widest shadow-xl">
            {{ message }}
          </div>
        </transition>
      </div>

      <!-- Card Principal con Datos Editables Inline -->
      <div class="group relative bg-white p-8 sm:p-10 rounded-[48px] shadow-xl shadow-gray-200/50 border border-gray-100 transition-all duration-500">
        <div class="flex flex-col md:flex-row items-center gap-8">
            <div class="w-32 h-32 bg-gray-50 rounded-[36px] flex items-center justify-center text-gray-300 shrink-0 shadow-inner relative overflow-hidden">
                <User :size="64" class="group-hover:text-brand-pink-500 transition-all duration-700" />
                <div class="absolute inset-0 bg-brand-pink-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </div>
            
            <div class="text-center md:text-left flex-grow space-y-4 w-full">
                <div class="space-y-4">
                    <div class="flex flex-wrap items-center justify-center md:justify-start gap-2">
                        <span :class="['px-5 py-2 rounded-full text-[9px] font-black uppercase tracking-widest border shadow-sm transition-all', child.estado === 'Encontrado' ? 'bg-green-50 text-green-600 border-green-100' : 'bg-red-50 text-red-600 border-red-100']">{{ child.estado }}</span>
                        <span class="text-gray-400 font-bold text-xs bg-gray-50/80 px-4 py-1.5 rounded-xl border border-gray-100">DNI {{ child.dni_nino }}</span>                        
                    </div>

                    <h1 class="w-full text-2xl sm:text-4xl lg:text-5xl font-black text-gray-900 tracking-tighter leading-none py-1 uppercase">{{ child.nombres }}</h1>

                    <div class="flex items-center justify-center md:justify-start gap-2 text-gray-400 text-[10px] font-bold uppercase tracking-widest">
                        <MapPin :size="14" class="text-brand-pink-400 shrink-0" />
                        <span>{{ child.establecimiento_asignado || 'Sin establecimiento asignado' }}</span>
                    </div>
                </div>
            </div>

            <div class="flex flex-col items-center gap-4 shrink-0">
                <div class="flex flex-wrap items-center justify-center gap-3">
                      <button @click="showFullDetails = !showFullDetails" class="h-16 px-10 rounded-3xl bg-black text-white text-[10px] font-black uppercase tracking-[0.2em] shadow-xl hover:scale-105 active:scale-95 transition-all">
                        {{ showFullDetails ? 'CERRAR FICHA' : 'EDITAR / VER MÁS' }}
                      </button>
                      
                      <!-- Botón de Descarga PDF -->
                      <button 
                        @click.stop="downloadPDF" 
                        :disabled="isDownloadingPdf"
                        class="h-16 w-16 flex items-center justify-center rounded-3xl bg-indigo-600 text-white shadow-xl hover:bg-indigo-700 active:scale-95 transition-all disabled:opacity-50"
                        title="Descargar Historial Clínico Completo (PDF)"
                      >
                        <Loader2 v-if="isDownloadingPdf" class="animate-spin" :size="20" />
                        <FileDown v-else :size="20" />
                      </button>
                </div>
                <div class="flex items-center gap-2 text-[8px] font-black text-gray-300 uppercase tracking-widest group-hover:text-gray-500 transition-colors">
                    PDF e Historial completo
                </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Contenido Expandible (Formularios detallados) -->
      <transition name="expand">
        <div v-if="showFullDetails" class="space-y-8 animate-in fade-in slide-in-from-top-4 duration-500">
          <div class="flex flex-wrap gap-2 justify-center lg:justify-start">
            <button v-for="tab in [{ id: 'menor', label: 'Datos del Menor', icon: User }, { id: 'madre', label: 'Datos de la Madre', icon: Heart }, { id: 'admin', label: 'Administrativo', icon: FileText }]" :key="tab.id" @click="activeTab = tab.id" :class="['flex items-center gap-3 px-6 py-3.5 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all', activeTab === tab.id ? 'bg-black text-white shadow-xl scale-105' : 'bg-white text-gray-400 hover:bg-gray-50 border border-gray-100']">
              <component :is="tab.icon" :size="14" /> {{ tab.label }}
            </button>
          </div>
          
          <div class="lg:col-span-8">

            <div v-if="activeTab === 'menor'" class="bg-white p-8 sm:p-10 rounded-[40px] border border-gray-100 space-y-8 shadow-sm">
                <h2 class="text-xs font-black uppercase tracking-[0.2em] text-gray-900 border-b pb-6 border-gray-100 flex items-center gap-3"><User :size="20" class="text-indigo-500" /> Datos del Menor</h2>
                <div class="space-y-6">
                    <div class="space-y-2">
                        <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Nombres y Apellidos del Niño</label>
                        <input v-model="child.nombres" class="w-full rounded-2xl border border-gray-100 focus:border-brand-pink-500 outline-none p-4 h-12 text-base font-bold bg-gray-50/10 uppercase" />
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <div class="space-y-2">
                            <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">DNI del Niño</label>
                            <input v-model="child.dni_nino" class="w-full rounded-2xl border border-gray-100 focus:border-brand-pink-500 outline-none p-4 h-12 text-base font-bold bg-gray-50/30" maxlength="15" />
                        </div>
                        <div class="space-y-2">
                            <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Fecha de Nacimiento</label>
                            <input v-model="child.fecha_nacimiento" type="date" class="w-full rounded-2xl border border-gray-100 focus:border-brand-pink-500 outline-none p-4 h-12 text-base font-bold bg-gray-50/30" />
                        </div>
                        <div class="space-y-2">
                            <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Rango de Edad</label>
                            <input v-model="child.rango_edad" class="w-full rounded-2xl border border-gray-100 focus:border-brand-pink-500 outline-none p-4 h-12 text-base font-bold bg-gray-50/30" />
                        </div>
                    </div>
                    <div class="space-y-2">
                        <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Dirección de Domicilio</label>
                        <input v-model="child.direccion" class="w-full rounded-2xl border border-gray-100 focus:border-brand-pink-500 outline-none p-4 h-12 text-base font-bold bg-gray-50/30" />
                    </div>

                    <!-- Botones de Acción -->
                    <div class="pt-4 flex justify-end gap-3">
                        <button @click="fetchChildData(); showFullDetails = false" :disabled="isSaving" class="h-16 px-10 rounded-3xl bg-gray-100 text-gray-500 text-[10px] font-black uppercase tracking-[0.2em] hover:bg-red-50 hover:text-red-500 transition-all flex items-center gap-3 disabled:opacity-50">
                            CANCELAR
                        </button>
                        <button @click="handleSave" :disabled="isSaving" class="h-16 px-10 rounded-3xl bg-green-600 text-white text-[10px] font-black uppercase tracking-[0.2em] shadow-xl shadow-green-200 hover:scale-105 active:scale-95 transition-all flex items-center gap-3 disabled:opacity-50">
                            <Loader2 v-if="isSaving" class="animate-spin" :size="16" />
                            <Save v-else :size="16" />
                            {{ isSaving ? 'GUARDANDO...' : 'GUARDAR CAMBIOS' }}
                        </button>
                    </div>
                </div>
            </div>

            <div v-if="activeTab === 'madre'" class="bg-white p-8 sm:p-10 rounded-[40px] border border-gray-100 space-y-8 shadow-sm">
                <h2 class="text-xs font-black uppercase tracking-[0.2em] text-gray-900 border-b pb-6 border-gray-100 flex items-center gap-3"><Heart :size="20" class="text-brand-pink-500" /> Datos de la Madre</h2>
                <div class="space-y-6">
                    <div class="space-y-2">
                        <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Nombre y Apellidos</label>
                        <input v-model="child.nombre_madre" class="w-full rounded-2xl border border-gray-100 focus:border-brand-pink-500 outline-none p-4 h-12 text-base font-bold bg-brand-pink-50/10" />
                    </div>
                    <div class="grid grid-cols-2 gap-8">
                        <div class="space-y-2">
                            <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">DNI Madre</label>
                            <input v-model="child.dni_madre" class="w-full rounded-2xl border border-gray-100 focus:border-brand-pink-500 outline-none p-4 h-12 text-base font-bold bg-brand-pink-50/10" maxlength="15" />
                        </div>
                        <div class="space-y-2">
                            <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Celular</label>
                            <input v-model="child.celular_madre" class="w-full rounded-2xl border border-gray-100 focus:border-brand-pink-500 outline-none p-4 h-12 text-base font-bold bg-brand-pink-50/10" />
                        </div>
                    </div>

                    <!-- Botones de Acción -->
                    <div class="pt-4 flex justify-end gap-3">
                        <button @click="fetchChildData(); showFullDetails = false" :disabled="isSaving" class="h-16 px-10 rounded-3xl bg-gray-100 text-gray-500 text-[10px] font-black uppercase tracking-[0.2em] hover:bg-red-50 hover:text-red-500 transition-all flex items-center gap-3 disabled:opacity-50">
                            CANCELAR
                        </button>
                        <button @click="handleSave" :disabled="isSaving" class="h-16 px-10 rounded-3xl bg-green-600 text-white text-[10px] font-black uppercase tracking-[0.2em] shadow-xl shadow-green-200 hover:scale-105 active:scale-95 transition-all flex items-center gap-3 disabled:opacity-50">
                            <Loader2 v-if="isSaving" class="animate-spin" :size="16" />
                            <Save v-else :size="16" />
                            {{ isSaving ? 'GUARDANDO...' : 'GUARDAR CAMBIOS' }}
                        </button>
                    </div>
                </div>
            </div>

            <div v-if="activeTab === 'admin'" class="bg-white p-8 sm:p-10 rounded-[40px] border border-gray-100 space-y-8 shadow-sm">
                <div class="space-y-6">
                    <div class="space-y-2">
                        <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Establecimiento de Salud (EESS) Asignado</label>
                        <div class="relative">
                            <MapPin class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" :size="18" />
                            <select 
                                v-model="child.establecimiento_asignado"
                                class="w-full bg-gray-50 border-none rounded-2xl pl-12 pr-10 h-12 text-base font-bold text-gray-700 outline-none focus:ring-2 focus:ring-brand-pink-500 appearance-none cursor-pointer"
                            >
                                <option value="">Seleccionar EESS...</option>
                                <option v-for="opt in STATIC_EESS_LIST" :key="opt" :value="opt">{{ opt }}</option>
                            </select>
                            <ChevronDown class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" :size="18" />
                        </div>
                    </div>
                    <div class="space-y-2">
                        <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Historia Clínica Nº</label>
                        <input v-model="child.historia_clinica" class="w-full rounded-2xl border border-gray-100 focus:border-brand-pink-500 outline-none p-4 h-12 text-base font-bold bg-gray-50/30" />
                    </div>

                    <!-- Botones de Acción -->
                    <div class="pt-4 flex justify-end gap-3">
                        <button @click="fetchChildData(); showFullDetails = false" :disabled="isSaving" class="h-16 px-10 rounded-3xl bg-gray-100 text-gray-500 text-[10px] font-black uppercase tracking-[0.2em] hover:bg-red-50 hover:text-red-500 transition-all flex items-center gap-3 disabled:opacity-50">
                            CANCELAR
                        </button>
                        <button @click="handleSave" :disabled="isSaving" class="h-16 px-10 rounded-3xl bg-green-600 text-white text-[10px] font-black uppercase tracking-[0.2em] shadow-xl shadow-green-200 hover:scale-105 active:scale-95 transition-all flex items-center gap-3 disabled:opacity-50">
                            <Loader2 v-if="isSaving" class="animate-spin" :size="16" />
                            <Save v-else :size="16" />
                            {{ isSaving ? 'GUARDANDO...' : 'GUARDAR CAMBIOS' }}
                        </button>
                    </div>
                </div>
            </div>
          </div>
        </div>
      </transition>

      <!-- Historial de Seguimiento (EDITABLE INLINE) -->
      <div class="space-y-8 pt-10 border-t border-gray-100">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <h2 class="text-2xl font-black text-gray-900 tracking-tight flex items-center gap-3"><Clock class="text-brand-pink-500" :size="28" /> Historial de Seguimiento</h2>
            <span class="px-4 py-2 bg-gray-100 rounded-full text-[10px] font-black uppercase tracking-widest text-gray-500">{{ filteredVisitas?.length || 0 }} Registros</span>
          </div>
          <button @click="showAddVisitaModal = true" class="flex items-center gap-2 px-6 py-3 bg-black text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-brand-pink-600 transition-all shadow-lg active:scale-95">
            <Plus :size="14" /> Agregar Visita
          </button>
        </div>

        <div v-if="filterPeriod" class="animate-in slide-in-from-left duration-500">
           <div class="flex items-center justify-between p-6 bg-indigo-50 rounded-3xl border border-indigo-100 mb-4">
              <div class="flex items-center gap-4">
                <div class="bg-white p-3 rounded-2xl text-indigo-500 shadow-sm">
                  <Activity :size="20" />
                </div>
                <div>
                  <p class="text-[10px] font-black text-indigo-400 uppercase tracking-widest leading-none mb-1">Periodo Filtrado</p>
                  <p class="text-sm font-black text-indigo-900 leading-none capitalize">{{ filterPeriod.label }}</p>
                </div>
              </div>
              <button 
                @click="showFilteredOnly = !showFilteredOnly"
                class="px-6 py-2 bg-white text-indigo-600 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-indigo-600 hover:text-white transition-all shadow-sm active:scale-95"
              >
                {{ showFilteredOnly ? 'Ver Historial Completo' : 'Volver al Periodo' }}
              </button>
           </div>
        </div>

        <div v-if="groupedVisitas && groupedVisitas.length > 0" class="space-y-12">
          <div v-for="group in groupedVisitas" :key="group.label" class="space-y-8">
            <!-- Elegant Month Header -->
            <div class="flex items-center gap-6 px-4">
              <div class="h-px bg-gradient-to-r from-transparent via-gray-200 to-transparent flex-grow"></div>
              <div class="flex flex-col items-center">
                <span class="text-[10px] font-black text-brand-pink-500 uppercase tracking-[0.4em] leading-none mb-2">{{ group.label.split(' ')[0] }}</span>
                <span class="text-[11px] font-black text-gray-400 leading-none">{{ group.label.split(' ')[1] }}</span>
              </div>
              <div class="h-px bg-gradient-to-r from-transparent via-gray-200 to-transparent flex-grow"></div>
            </div>

            <div class="grid grid-cols-1 gap-6">
              <div v-for="visita in group.visits" :key="visita.id" 
                   :class="['group relative bg-white p-8 rounded-[40px] border shadow-sm transition-all duration-500', 
                            editingVisitaId === visita.id ? 'border-indigo-500 ring-8 ring-indigo-50' : 'border-gray-50 hover:border-brand-pink-100']">
            
            <div class="flex flex-col lg:flex-row gap-8">
                <!-- Fecha Izquierda -->
                <div class="flex flex-col items-center justify-center bg-gray-50 w-24 h-24 rounded-[32px] shrink-0 group-hover:bg-brand-pink-50 transition-colors">
                    <span class="text-3xl font-black text-gray-900 leading-none mb-1">{{ new Date(visita.fecha_visita + 'T00:00:00').getDate() }}</span>
                    <span class="text-xs font-black text-gray-600 uppercase leading-none">{{ new Date(visita.fecha_visita + 'T00:00:00').toLocaleString('es-PE', { month: 'short' }) }}</span>
                    <span class="text-[11px] font-black text-gray-500 leading-none mt-1">{{ new Date(visita.fecha_visita + 'T00:00:00').getFullYear() }}</span>
                </div>

                <!-- Contenido Editable -->
                <div class="flex-grow space-y-6">
                    <!-- Vista Normal -->
                    <div v-if="editingVisitaId !== visita.id" class="space-y-4">
                        <div class="flex flex-wrap items-center gap-3">
                            <span :class="['px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-widest border', visita.estado?.toLowerCase() === 'encontrado' ? 'bg-green-50 text-green-600 border-green-100' : 'bg-red-50 text-red-600 border-red-100']">{{ visita.estado }}</span>
                            <span class="flex items-center gap-2 text-[11px] font-bold text-gray-500 bg-gray-50 px-3 py-1.5 rounded-xl border border-gray-100"><Calendar :size="12" /> {{ formatDate(visita.fecha_visita) }}</span>
                            <span class="text-[11px] font-bold text-indigo-500 bg-indigo-50 px-3 py-1.5 rounded-xl flex items-center gap-2 border border-indigo-100"><Activity :size="12" /> {{ visita.establecimiento_atencion || 'Sin EESS' }}</span>
                            <span class="text-[11px] font-bold text-gray-500 bg-gray-50 px-3 py-1.5 rounded-xl border border-gray-100 flex items-center gap-2"><User :size="12" class="text-brand-pink-400" /> {{ visita.actor_social || 'Sin Actor Social' }}</span>
                        </div>
                        <p v-if="visita.observacion" class="text-sm text-gray-600 font-medium leading-relaxed italic bg-gray-50/30 p-4 rounded-[24px] border border-dashed border-gray-100 shadow-inner">"{{ visita.observacion }}"</p>
                    </div>

                    <!-- Vista Edición Inline -->
                    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in duration-300">
                        <div class="space-y-4">
                            <div class="grid grid-cols-2 gap-4">
                                <div class="space-y-1">
                                    <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Estado</label>
                                    <select v-model="inlineBuffer.estado" class="w-full h-12 px-4 rounded-xl border border-gray-200 text-xs font-bold uppercase focus:ring-4 focus:ring-indigo-50">
                                        <option value="encontrado">Encontrado</option>
                                        <option value="no encontrado">No Encontrado</option>
                                    </select>
                                </div>
                                <div class="space-y-1">
                                    <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Fecha</label>
                                    <input v-model="inlineBuffer.fecha_visita" type="date" class="w-full h-12 px-4 rounded-xl border border-gray-200 text-xs font-bold focus:ring-4 focus:ring-indigo-50" />
                                </div>
                            </div>
                            <div class="space-y-1">
                                <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Actor Social</label>
                                <input v-model="inlineBuffer.actor_social" class="w-full h-12 px-4 rounded-xl border border-gray-200 text-xs font-bold focus:ring-4 focus:ring-indigo-50" />
                            </div>
                            <div class="space-y-1">
                                <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">EESS de Atención</label>
                                <div class="relative">
                                    <MapPin class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="14" />
                                        <select 
                                        v-model="inlineBuffer.establecimiento_atencion"
                                        class="w-full bg-gray-50 border-none rounded-xl pl-9 pr-10 h-12 text-xs font-bold text-gray-700 outline-none focus:ring-2 focus:ring-indigo-500 appearance-none cursor-pointer"
                                    >
                                        <option value="">Seleccionar EESS...</option>
                                        <option v-for="opt in STATIC_EESS_LIST" :key="opt" :value="opt">{{ opt }}</option>
                                    </select>
                                    <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" :size="14" />
                                </div>
                            </div>
                        </div>
                        <div class="space-y-1">
                            <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1">Observaciones</label>
                            <textarea v-model="inlineBuffer.observacion" rows="3" class="w-full p-4 rounded-xl border border-gray-200 text-xs font-medium focus:ring-4 focus:ring-indigo-50" placeholder="Escribe aquí..."></textarea>
                        </div>
                    </div>
                </div>

                <!-- Botones de Acción -->
                <div class="shrink-0 flex items-center lg:flex-col justify-center gap-3">
                    <div v-if="editingVisitaId !== visita.id" class="flex flex-col gap-2">
                         <button @click="startInlineEdit(visita)" class="flex items-center gap-2 px-6 py-3 rounded-2xl bg-gray-50 text-gray-500 text-[10px] font-black uppercase hover:bg-black hover:text-white transition-all">
                            <Edit2 :size="14" /> Editar
                         </button>
                         <button @click="deleteVisita(visita)" :disabled="isDeletingVisita === visita.id" class="flex items-center gap-2 px-6 py-3 rounded-2xl bg-red-50 text-red-400 text-[10px] font-black uppercase hover:bg-red-500 hover:text-white transition-all disabled:opacity-50">
                            <Loader2 v-if="isDeletingVisita === visita.id" class="animate-spin" :size="14" />
                            <Trash2 v-else :size="14" /> Borrar
                         </button>
                    </div>
                    <div v-else class="flex flex-col gap-2">
                        <button @click="saveInlineVisita(visita.id)" class="flex items-center justify-center gap-2 w-full px-6 py-3 rounded-2xl bg-green-600 text-white text-[10px] font-black uppercase hover:bg-green-700 shadow-lg transition-all">
                            <Check :size="16" /> Guardar
                        </button>
                        <button @click="cancelInlineEdit" class="flex items-center justify-center gap-2 w-full px-6 py-3 rounded-2xl bg-gray-100 text-gray-400 text-[10px] font-black uppercase hover:bg-red-50 hover:text-red-500 transition-all">
                            <X :size="16" /> Cancelar
                        </button>
                    </div>
                </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <datalist id="all-eess">
        <option v-for="opt in STATIC_EESS_LIST" :key="opt" :value="opt" />
      </datalist>
    </div>

    <!-- Modal Agregar Visita -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showAddVisitaModal" class="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/60 backdrop-blur-sm">
          <div class="bg-white rounded-[40px] max-w-2xl w-full p-10 shadow-2xl space-y-8 animate-in zoom-in-95 duration-300">
            <div class="flex items-center justify-between border-b border-gray-100 pb-6">
              <h2 class="text-2xl font-black text-gray-900 tracking-tight">Agregar Nueva Visita</h2>
              <button @click="showAddVisitaModal = false" class="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400">
                <X :size="24" />
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div class="space-y-4">
                <div class="space-y-2">
                  <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Fecha de la Visita</label>
                  <input v-model="newVisita.fecha_visita" type="date" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all" />
                </div>
                <div class="space-y-2">
                  <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Estado</label>
                  <select v-model="newVisita.estado" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 appearance-none cursor-pointer">
                    <option value="encontrado">Encontrado</option>
                    <option value="no encontrado">No Encontrado</option>
                    <option value="pendiente">Pendiente</option>
                  </select>
                </div>
              </div>
              <div class="space-y-4">
                <div class="space-y-2">
                  <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Actor Social</label>
                  <input v-model="newVisita.actor_social" placeholder="Nombre del actor social..." class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 transition-all" />
                </div>
                <div class="space-y-2">
                  <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">EESS de Atención</label>
                  <select v-model="newVisita.establecimiento_atencion" class="w-full h-14 px-5 bg-gray-50 border-none rounded-2xl text-sm font-bold focus:ring-2 focus:ring-brand-pink-500 appearance-none cursor-pointer">
                    <option value="">Seleccionar EESS...</option>
                    <option v-for="opt in STATIC_EESS_LIST" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="space-y-2">
              <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest pl-1">Observaciones</label>
              <textarea v-model="newVisita.observacion" rows="3" class="w-full p-5 bg-gray-50 border-none rounded-2xl text-sm font-medium focus:ring-2 focus:ring-brand-pink-500 transition-all" placeholder="Escribe aquí cualquier detalle importante..."></textarea>
            </div>

            <div class="flex flex-col sm:flex-row gap-4 pt-4">
              <button @click="saveNewVisita" :disabled="isSaving" class="h-16 flex-grow bg-black text-white rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-brand-pink-600 transition-all shadow-xl active:scale-95 disabled:opacity-50">
                {{ isSaving ? 'Registrando...' : 'Registrar Visita' }}
              </button>
              <button @click="showAddVisitaModal = false" class="h-16 px-10 bg-gray-50 text-gray-400 rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-gray-100 hover:text-gray-900 transition-colors">
                Cancelar
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Modal Confirmación Eliminar Visita -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showDeleteVisitaModal && visitaToDelete" class="fixed inset-0 z-[110] flex items-center justify-center p-6 bg-black/60 backdrop-blur-sm">
          <div class="bg-white rounded-[40px] max-w-md w-full p-10 shadow-2xl space-y-8 animate-in zoom-in-95 duration-300">
            <div class="flex flex-col items-center text-center space-y-6">
              <div class="w-20 h-20 bg-red-50 text-red-500 rounded-3xl flex items-center justify-center shadow-inner">
                <Trash2 :size="40" />
              </div>
              <div class="space-y-4">
                <h2 class="text-2xl font-black text-gray-900 leading-tight">¿Eliminar esta visita?</h2>
                <div class="p-4 bg-gray-50 rounded-2xl border border-gray-100 space-y-1">
                   <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Fecha de la visita</p>
                   <p class="text-sm font-bold text-gray-700">{{ formatDate(visitaToDelete.fecha_visita) }}</p>
                </div>
                <p class="text-gray-500 font-medium text-sm px-2">Esta acción borrará este registro de atención permanentemente. No se puede deshacer.</p>
              </div>
            </div>
            
            <div class="flex flex-col gap-4">
              <button 
                @click="confirmDeleteVisita"
                :disabled="isDeletingVisita === visitaToDelete.id"
                class="h-16 w-full bg-red-600 text-white rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-black transition-all shadow-lg active:scale-95 disabled:opacity-50"
              >
                {{ isDeletingVisita === visitaToDelete.id ? 'Eliminando...' : 'Confirmar Eliminación' }}
              </button>
              <button 
                @click="showDeleteVisitaModal = false"
                class="h-16 w-full bg-gray-50 text-gray-400 rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-gray-100 hover:text-gray-900 transition-colors active:scale-95"
              >
                No, Mantener Registro
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<style scoped>
.expand-enter-active, .expand-leave-active {
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  max-height: 2000px;
  opacity: 1;
  overflow: hidden;
}
.expand-enter-from, .expand-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-20px);
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.5s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
