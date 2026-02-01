import axios from 'axios'

const apiClient = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true, // Habilitar envío de cookies HttpOnly
})

// Interceptores para manejar el token en cada petición
apiClient.interceptors.request.use((config) => {
    const token = sessionStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// Interceptores para manejar errores globales (ej: 401 si el token expira)
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        // Solo redirigir si el error es 401 Y no proviene de la ruta de login
        // Si proviene de login, permitimos que el componente Login.vue maneje el error
        if (error.response?.status === 401 && !error.config.url.includes('/auth/login')) {
            sessionStorage.removeItem('token')
            sessionStorage.removeItem('user')
            window.location.href = '/login'
        }
        return Promise.reject(error)
    }
)

export default apiClient
