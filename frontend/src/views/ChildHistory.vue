<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { 
  ArrowLeft, Save, User, Activity, MapPin, 
  Calendar, FileText, Loader2, Heart, 
  ChevronDown, Clock, X, Edit2, Check, FileDown
} from 'lucide-vue-next'
import apiClient from '../api/client'

const props = defineProps({
  id: [String, Number]
})

const router = useRouter()
const isSaving = ref(false)
const loading = ref(true)
const message = ref('')
const showFullDetails = ref(false)
const activeTab = ref('menor')
const editingVisitaId = ref(null)

const child = ref({
  id: props.id,
  dni_nino: '',
  nombres: '',
  fecha_nacimiento: '',
  direccion: '',
  dni_madre: '',
  nombre_madre: '',
  celular_madre: '',
  visitas: []
})

const inlineBuffer = ref({})
const allEessOptions = ref([])
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

const fetchChildData = async () => {
  try {
    const { data } = await apiClient.get(`/ninos/${props.id}`)
    child.value = data
  } catch (err) {
    console.error(err)
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

// Lógica de Agrupamiento por Mes
const groupedVisitas = computed(() => {
  if (!child.value.visitas) return {}
  
  const groups = {}
  
  // Ordenar todas las visitas por fecha descendente
  const sortedVisitas = [...child.value.visitas].sort((a, b) => 
    new Date(b.fecha_visita + 'T00:00:00') - new Date(a.fecha_visita + 'T00:00:00')
  )

  sortedVisitas.forEach(visita => {
    const date = new Date(visita.fecha_visita + 'T00:00:00')
    const monthName = date.toLocaleString('es-PE', { month: 'long' })
    const year = date.getFullYear()
    const key = `${monthName} ${year}`

    if (!groups[key]) {
      groups[key] = {
        label: key.toUpperCase(),
        visitas: []
      }
    }
    groups[key].visitas.push(visita)
  })

  return groups
})

const startInlineEdit = (visita) => {
    editingVisitaId.value = visita.id
    inlineBuffer.value = { ...visita }
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

const handleSave = async () => {
  isSaving.value = true
  message.value = ''
  try {
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
  <div class="child-history-container">
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

      <!-- Card Principal -->
      <div class="group relative bg-white p-8 sm:p-10 rounded-[48px] shadow-xl shadow-gray-200/50 border border-gray-100 transition-all duration-500">
        <div class="flex flex-col md:flex-row items-center gap-8">
            <div class="w-32 h-32 bg-gray-50 rounded-[36px] flex items-center justify-center text-gray-300 shrink-0 shadow-inner relative overflow-hidden">
                <User :size="64" class="group-hover:text-brand-pink-500 transition-all duration-700" />
            </div>
            
            <div class="text-center md:text-left flex-grow space-y-4 w-full">
                <div class="space-y-4">
                    <div class="flex flex-wrap items-center justify-center md:justify-start gap-2">
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

      <!-- Secciones de Edición (Tabs) -->
      <transition name="expand">
        <div v-if="showFullDetails" class="space-y-8 animate-in fade-in slide-in-from-top-4 duration-500">
          <div class="flex flex-wrap gap-2 justify-center lg:justify-start">
            <button v-for="tab in [{ id: 'menor', label: 'Datos del Menor', icon: User }, { id: 'madre', label: 'Datos de la Madre', icon: Heart }, { id: 'admin', label: 'Administrativo', icon: FileText }]" :key="tab.id" @click="activeTab = tab.id" :class="['flex items-center gap-3 px-6 py-3.5 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all', activeTab === tab.id ? 'bg-black text-white shadow-xl scale-105' : 'bg-white text-gray-400 hover:bg-gray-50 border border-gray-100']">
              <component :is="tab.icon" :size="14" /> {{ tab.label }}
            </button>
          </div>
          
          <div class="lg:col-span-8">
            <!-- Datos del Menor -->
            <div v-if="activeTab === 'menor'" class="bg-white p-8 sm:p-10 rounded-[40px] border border-gray-100 space-y-8 shadow-sm">
                <h2 class="text-xs font-black uppercase tracking-[0.2em] text-gray-900 border-b pb-6 border-gray-100 flex items-center gap-3"><User :size="20" class="text-indigo-500" /> Datos del Menor</h2>
                <div class="space-y-6">
                    <div class="space-y-2">
                        <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Nombres y Apellidos del Niño</label>
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
                    <div class="pt-4 flex justify-end gap-3">
                        <button @click="fetchChildData" :disabled="isSaving" class="h-16 px-10 rounded-3xl bg-gray-100 text-gray-500 text-[10px] font-black uppercase tracking-[0.2em] hover:bg-red-50 hover:text-red-500 transition-all flex items-center gap-3 disabled:opacity-50">CANCELAR</button>
                        <button @click="handleSave" :disabled="isSaving" class="h-16 px-10 rounded-3xl bg-green-600 text-white text-[10px] font-black uppercase tracking-[0.2em] shadow-xl shadow-green-200 hover:scale-105 active:scale-95 transition-all flex items-center gap-3 disabled:opacity-50">
                            <Loader2 v-if="isSaving" class="animate-spin" :size="16" />
                            <Save v-else :size="16" />
                            {{ isSaving ? 'GUARDANDO...' : 'GUARDAR CAMBIOS' }}
                        </button>
                    </div>
                </div>
            </div>

            <!-- Datos de la Madre -->
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
                    <div class="pt-4 flex justify-end gap-3">
                        <button @click="fetchChildData" :disabled="isSaving" class="h-16 px-10 rounded-3xl bg-gray-100 text-gray-500 text-[10px] font-black uppercase tracking-[0.2em] hover:bg-red-50 hover:text-red-500 transition-all flex items-center gap-3 disabled:opacity-50">CANCELAR</button>
                        <button @click="handleSave" :disabled="isSaving" class="h-16 px-10 rounded-3xl bg-green-600 text-white text-[10px] font-black uppercase tracking-[0.2em] shadow-xl shadow-green-200 hover:scale-105 active:scale-95 transition-all flex items-center gap-3 disabled:opacity-50">
                            <Loader2 v-if="isSaving" class="animate-spin" :size="16" />
                            <Save v-else :size="16" />
                            {{ isSaving ? 'GUARDANDO...' : 'GUARDAR CAMBIOS' }}
                        </button>
                    </div>
                </div>
            </div>

            <!-- Administrativo -->
            <div v-if="activeTab === 'admin'" class="bg-white p-8 sm:p-10 rounded-[40px] border border-gray-100 space-y-8 shadow-sm">
                <div class="space-y-6">
                    <div class="space-y-2">
                        <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Establecimiento de Salud (EESS) Asignado</label>
                        <div class="relative">
                            <MapPin class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" :size="18" />
                            <select v-model="child.establecimiento_asignado" class="w-full bg-gray-50 border-none rounded-2xl pl-12 pr-10 h-12 text-base font-bold text-gray-700 outline-none focus:ring-2 focus:ring-brand-pink-500 appearance-none cursor-pointer">
                                <option value="">Seleccionar EESS...</option>
                                <option v-for="opt in allEessOptions" :key="opt" :value="opt">{{ opt }}</option>
                            </select>
                            <ChevronDown class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" :size="18" />
                        </div>
                    </div>
                    <div class="space-y-2">
                        <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Historia Clínica Nº</label>
                        <input v-model="child.historia_clinica" class="w-full rounded-2xl border border-gray-100 focus:border-brand-pink-500 outline-none p-4 h-12 text-base font-bold bg-gray-50/30" />
                    </div>
                    <div class="pt-4 flex justify-end gap-3">
                        <button @click="fetchChildData" :disabled="isSaving" class="h-16 px-10 rounded-3xl bg-gray-100 text-gray-500 text-[10px] font-black uppercase tracking-[0.2em] hover:bg-red-50 hover:text-red-500 transition-all flex items-center gap-3 disabled:opacity-50">CANCELAR</button>
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

      <!-- Historial Grupal por Mes -->
      <div class="space-y-12 pt-10 border-t border-gray-100">
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-black text-gray-900 tracking-tight flex items-center gap-3"><Clock class="text-brand-pink-500" :size="28" /> Historial de Seguimiento</h2>
          <span class="px-4 py-2 bg-gray-100 rounded-full text-[10px] font-black uppercase tracking-widest text-gray-500">{{ child.visitas?.length || 0 }} Registros</span>
        </div>

        <div v-for="(group, monthKey) in groupedVisitas" :key="monthKey" class="space-y-6">
            <!-- Encabezado de Mes -->
            <div class="flex items-center gap-4">
                <div class="h-px bg-gray-100 flex-grow"></div>
                <h3 class="text-xs font-black text-gray-400 uppercase tracking-[0.3em] bg-white px-4 py-2 rounded-full border border-gray-100 shadow-sm">{{ group.label }}</h3>
                <div class="h-px bg-gray-100 flex-grow"></div>
            </div>

            <div class="grid grid-cols-1 gap-4">
                <div v-for="visita in group.visitas" :key="visita.id" 
                     :class="['group/item relative bg-white p-6 rounded-[32px] border shadow-sm transition-all duration-500', 
                              editingVisitaId === visita.id ? 'border-indigo-500 ring-4 ring-indigo-50' : 'border-gray-50 hover:border-brand-pink-100']">
                    
                    <div class="flex flex-col lg:flex-row gap-6">
                        <div class="flex flex-col items-center justify-center bg-gray-50 w-20 h-20 rounded-[24px] shrink-0 group-hover/item:bg-brand-pink-50 transition-colors">
                            <span class="text-2xl font-black text-gray-900 leading-none mb-1">{{ new Date(visita.fecha_visita + 'T00:00:00').getDate() }}</span>
                            <span class="text-[10px] font-black text-gray-400 uppercase leading-none">{{ new Date(visita.fecha_visita + 'T00:00:00').toLocaleString('es-PE', { weekday: 'short' }) }}</span>
                        </div>

                        <div class="flex-grow space-y-4">
                            <div v-if="editingVisitaId !== visita.id" class="space-y-3">
                                <div class="flex flex-wrap items-center gap-2">
                                    <span :class="['px-3 py-1 rounded-full text-[8px] font-black uppercase tracking-widest border', visita.estado?.toLowerCase() === 'encontrado' ? 'bg-green-50 text-green-600 border-green-100' : 'bg-red-50 text-red-600 border-red-100']">{{ visita.estado }}</span>
                                    <span class="text-[10px] font-bold text-gray-500 bg-gray-50 px-3 py-1 rounded-lg border border-gray-100 flex items-center gap-1.5"><Activity :size="10" /> {{ visita.establecimiento_atencion || 'Sin EESS' }}</span>
                                    <span class="text-[10px] font-bold text-gray-500 bg-gray-50 px-3 py-1 rounded-lg border border-gray-100 flex items-center gap-1.5"><User :size="10" class="text-brand-pink-400" /> {{ visita.actor_social || 'Sin Actor' }}</span>
                                </div>
                                <p v-if="visita.observacion" class="text-xs text-gray-500 font-medium italic border-l-2 border-gray-100 pl-3">"{{ visita.observacion }}"</p>
                            </div>

                            <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div class="space-y-3">
                                    <div class="grid grid-cols-2 gap-3">
                                        <div class="space-y-1">
                                            <label class="text-[8px] font-black text-gray-400 uppercase tracking-widest ml-1">Estado</label>
                                            <select v-model="inlineBuffer.estado" class="w-full h-10 px-3 rounded-xl border border-gray-200 text-xs font-bold uppercase focus:ring-2 focus:ring-indigo-100">
                                                <option value="encontrado">Encontrado</option>
                                                <option value="no encontrado">No Encontrado</option>
                                            </select>
                                        </div>
                                        <div class="space-y-1">
                                            <label class="text-[8px] font-black text-gray-400 uppercase tracking-widest ml-1">Fecha</label>
                                            <input v-model="inlineBuffer.fecha_visita" type="date" class="w-full h-10 px-3 rounded-xl border border-gray-200 text-xs font-bold focus:ring-2 focus:ring-indigo-100" />
                                        </div>
                                    </div>
                                    <div class="space-y-1">
                                        <label class="text-[8px] font-black text-gray-400 uppercase tracking-widest ml-1">Actor Social</label>
                                        <input v-model="inlineBuffer.actor_social" class="w-full h-10 px-3 rounded-xl border border-gray-200 text-xs font-bold focus:ring-2 focus:ring-indigo-100" />
                                    </div>
                                </div>
                                <div class="space-y-1">
                                    <label class="text-[8px] font-black text-gray-400 uppercase tracking-widest ml-1">Observaciones</label>
                                    <textarea v-model="inlineBuffer.observacion" rows="2" class="w-full p-3 rounded-xl border border-gray-200 text-xs font-medium focus:ring-2 focus:ring-indigo-100" placeholder="Escribe aquí..."></textarea>
                                </div>
                            </div>
                        </div>

                        <div class="shrink-0 flex items-center lg:flex-col justify-center gap-2">
                            <button v-if="editingVisitaId !== visita.id" @click="startInlineEdit(visita)" class="p-3 rounded-xl bg-gray-50 text-gray-400 hover:bg-black hover:text-white transition-all"><Edit2 :size="16" /></button>
                            <template v-else>
                                <button @click="saveInlineVisita(visita.id)" class="p-3 rounded-xl bg-green-500 text-white shadow-lg shadow-green-100 hover:bg-green-600 transition-all"><Check :size="16" /></button>
                                <button @click="cancelInlineEdit" class="p-3 rounded-xl bg-gray-100 text-gray-400 hover:bg-red-50 hover:text-red-500 transition-all"><X :size="16" /></button>
                            </template>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.expand-enter-active, .expand-leave-active { transition: all 0.5s ease; max-height: 1000px; opacity: 1; overflow: hidden; }
.expand-enter-from, .expand-leave-to { max-height: 0; opacity: 0; transform: translateY(-10px); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
