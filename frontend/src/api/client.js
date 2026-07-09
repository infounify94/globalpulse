import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 60000,
})

// Attach response interceptor for global error handling
api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('API Error:', err.message)
    return Promise.reject(err)
  }
)

export default api
