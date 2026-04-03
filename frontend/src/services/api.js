import axios from 'axios'

const API_BASE_URL = '/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth APIs
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (email, password) => {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  loginJson: (email, password) => api.post('/auth/login/json', { email, password }),
}

// User APIs
export const userAPI = {
  getProfile: () => api.get('/users/me'),
  updateProfile: (data) => api.put('/users/me/profile', data),
  updateDietaryPreferences: (data) => api.put('/users/me/dietary-preferences', data),
  updateBudget: (data) => api.put('/users/me/budget', data),
  updateMealConfig: (data) => api.put('/users/me/meals', data),
  getHealthMetrics: () => api.get('/users/me/health-metrics'),
  getMacroTargets: () => api.get('/users/me/macro-targets'),
}

// Menu APIs
export const menuAPI = {
  extractMenu: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/menu/extract', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  searchFood: (query) => api.get(`/menu/search?query=${query}`),
  listItems: (params) => api.get('/menu/items', { params }),
  getStats: () => api.get('/menu/stats'),
  getCategories: () => api.get('/menu/categories'),
  getCuisines: () => api.get('/menu/cuisines'),
}

// Meal Planning APIs
export const mealAPI = {
  generatePlan: (duration = '7') => api.post(`/meals/generate?duration=${duration}`),
  getTodayPlan: () => api.get('/meals/today'),
  findSubstitutes: (itemName, maxPrice) => 
    api.post('/meals/substitute', { item_name: itemName, max_price: maxPrice }),
  getRecommendations: (mealSlot, maxPrice) => 
    api.get('/meals/recommendations', { params: { meal_slot: mealSlot, max_price: maxPrice } }),
}

// Recommendation APIs
export const recommendationAPI = {
  getRecommendations: (mealSlot, limit = 10, exclude = null) => 
    api.get('/recommendations/', { params: { meal_slot: mealSlot, limit, exclude } }),
  submitFeedback: (data) => api.post('/recommendations/feedback', data),
  getSimilar: (itemName, limit = 5) => api.get(`/recommendations/similar/${itemName}?limit=${limit}`),
  getTrending: (limit = 10) => api.get(`/recommendations/trending?limit=${limit}`),
  getInsights: () => api.get('/recommendations/personalized-insights'),
}

export default api
