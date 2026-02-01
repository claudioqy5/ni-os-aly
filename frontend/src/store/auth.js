import { defineStore } from 'pinia'
import apiClient from '../api/client'

export const useAuthStore = defineStore('auth', {
    state: () => {
        let savedUser = null
        try {
            savedUser = JSON.parse(sessionStorage.getItem('user'))
            // Si el objeto guardado no tiene el campo 'rol' (sesión antigua), lo ignoramos
            if (savedUser && !savedUser.rol) savedUser = null
        } catch (e) {
            savedUser = null
        }

        return {
            user: savedUser,
            token: sessionStorage.getItem('token') || null,
            loading: false,
            error: null
        }
    },
    getters: {
        isAuthenticated: (state) => !!state.token
    },
    actions: {
        async login(usuario, password) {
            this.loading = true
            this.error = null
            try {
                // OAuth2PasswordRequestForm espera x-www-form-urlencoded
                const params = new URLSearchParams()
                params.append('username', usuario)
                params.append('password', password)

                const response = await apiClient.post('/auth/login', params, {
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                })

                const { access_token, user } = response.data

                this.user = user
                this.token = access_token
                sessionStorage.setItem('token', access_token)
                sessionStorage.setItem('user', JSON.stringify(user))

                return true
            } catch (err) {
                console.error('Login error:', err)
                this.error = err.response?.data?.detail || 'Error al iniciar sesión. Verifique sus credenciales.'
                return false
            } finally {
                this.loading = false
            }
        },
        async logout() {
            try {
                await apiClient.post('/auth/logout')
            } catch (e) {
                console.warn('Logout session clear skip')
            }
            this.user = null
            this.token = null
            sessionStorage.removeItem('token')
            sessionStorage.removeItem('user')
            window.location.href = '/login'
        }
    }
})
