<script setup>
import { ref, onMounted } from 'vue'
import { FileSpreadsheet, Calendar, CheckCircle, ArrowLeft, Clock, AlertCircle, Loader2 } from 'lucide-vue-next'
import apiClient from '../api/client'

const history = ref([])
const loading = ref(true)

const fetchHistory = async () => {
  try {
    const { data } = await apiClient.get('/excel/history')
    history.value = data
    
    // Si hay alguno procesando, reintentar en 5 segundos
    const isProcessing = data.some(item => item.estado === 'procesando')
    if (isProcessing) {
      setTimeout(fetchHistory, 5000)
    }
  } catch (err) {
    console.error('Error fetching history:', err)
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('es-PE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getMonthName = (month) => {
  const months = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ]
  return months[month - 1] || '---'
}

onMounted(fetchHistory)
</script>

<template>
  <div class="space-y-8 animate-fade-in-up">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 tracking-tight">Historial de Cargas</h1>
        <p class="text-gray-400 font-medium">Registro de archivos Excel procesados</p>
      </div>
      <router-link to="/" class="btn-secondary flex items-center gap-2">
        <ArrowLeft :size="20" /> Volver
      </router-link>
    </div>

    <!-- Table Card -->
    <div class="card-minimal overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse whitespace-nowrap">
          <thead>
            <tr class="text-xs font-black text-gray-600 uppercase tracking-widest border-b border-gray-100 bg-gray-50/50">
              <th class="py-4 pl-8">Archivo</th>
              <th class="py-4 px-4">Periodo</th>
              <th class="py-4 px-4">Fecha de Carga</th>
              <th class="py-4 px-4 text-center">Registros</th>
              <th class="py-4 pr-8 text-right">Estado</th>
            </tr>
          </thead>
          <tbody class="text-sm text-gray-600 font-medium divide-y divide-gray-50">
            <tr v-for="item in history" :key="item.id" class="hover:bg-brand-pink-50/20 transition-colors">
              <td class="py-4 pl-8">
                <div class="flex items-center gap-3">
                  <div class="p-2 bg-green-50 rounded-lg text-green-600">
                    <FileSpreadsheet :size="20" />
                  </div>
                  <span class="font-bold text-gray-900">{{ item.nombre_archivo }}</span>
                </div>
              </td>
              <td class="py-4 px-4">
                <span class="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-bold">
                  <Calendar :size="12" />
                  {{ getMonthName(item.mes) }} {{ item.anio }}
                </span>
              </td>
              <td class="py-4 px-4 font-mono text-gray-500">
                {{ formatDate(item.created_at) }}
              </td>
              <td class="py-4 px-4 text-center">
                <span class="font-bold text-gray-900">{{ item.total_registros }}</span>
              </td>
              <td class="py-4 pr-8 text-right">
                <div class="flex flex-col items-end">
                  <span v-if="item.estado === 'completado'" class="inline-flex items-center gap-1 text-green-600 font-bold text-xs uppercase tracking-wider">
                    <CheckCircle :size="14" /> Completado
                  </span>
                  <span v-else-if="item.estado === 'procesando'" class="inline-flex items-center gap-1 text-blue-600 font-bold text-xs uppercase tracking-wider">
                    <Loader2 :size="14" class="animate-spin" /> Procesando
                  </span>
                  <span v-else-if="item.estado === 'error'" class="inline-flex items-center gap-1 text-red-600 font-bold text-xs uppercase tracking-wider">
                    <AlertCircle :size="14" /> Error
                  </span>
                  <span v-else class="inline-flex items-center gap-1 text-gray-400 font-bold text-xs uppercase tracking-wider">
                    <Clock :size="14" /> Pendiente
                  </span>
                  <p v-if="item.mensaje_error" class="text-[10px] text-red-400 mt-1 max-w-[200px] whitespace-normal">
                    {{ item.mensaje_error }}
                  </p>
                </div>
              </td>
            </tr>
            
            <tr v-if="history.length === 0 && !loading">
              <td colspan="5" class="py-12 text-center text-gray-400">
                No hay historial de cargas disponible.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
