import axios from 'axios';
import {
  Licitacion,
  LicitacionesResponse,
  Statistics,
  Filtros,
  SearchFilters,
  AnalisisContratacion,
  AnalisisDependencia,
  AnalisisFuente,
  AnalisisTemporal
} from '../types';

// Configure axios base URL - use proxy in development, direct in production
const baseURL = import.meta.env?.DEV ? '/api' : 'http://localhost:8000';

const api = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for debugging
api.interceptors.request.use(request => {
  console.log('API Request:', request.method?.toUpperCase(), request.url);
  return request;
});

// Add response interceptor for error handling
api.interceptors.response.use(
  response => {
    console.log('API Response:', response.status, response.config.url);
    return response;
  },
  error => {
    console.error('API Error:', error.response?.status, error.config?.url, error.message);
    return Promise.reject(error);
  }
);

export const apiService = {
  // Basic info
  async getApiInfo() {
    const response = await api.get('/');
    return response.data;
  },

  // Statistics
  async getStatistics(): Promise<Statistics> {
    const response = await api.get('/stats');
    return response.data;
  },

  // Licitaciones with filters
  async getLicitaciones(filters: SearchFilters = {}): Promise<LicitacionesResponse> {
    const params = new URLSearchParams();
    
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, value.toString());
      }
    });

    const response = await api.get(`/licitaciones?${params}`);
    return response.data;
  },

  // Get single licitacion detail
  async getLicitacionDetail(id: number): Promise<Licitacion> {
    const response = await api.get(`/detalle/${id}`);
    return response.data;
  },

  // Get available filters
  async getFilters(): Promise<Filtros> {
    const response = await api.get('/filtros');
    return response.data;
  },

  // Quick search for autocomplete
  async quickSearch(query: string, limit: number = 10) {
    const response = await api.get('/busqueda-rapida', {
      params: { q: query, limit }
    });
    return response.data;
  },

  // Analysis endpoints
  async getAnalisisPorTipoContratacion(): Promise<AnalisisContratacion[]> {
    const response = await api.get('/analisis/por-tipo-contratacion');
    return response.data;
  },

  async getAnalisisPorDependencia(limit: number = 20): Promise<AnalisisDependencia[]> {
    const response = await api.get('/analisis/por-dependencia', {
      params: { limit }
    });
    return response.data;
  },

  async getAnalisisPorFuente(): Promise<AnalisisFuente[]> {
    const response = await api.get('/analisis/por-fuente');
    return response.data;
  },

  async getAnalisisTemporal(granularidad: 'dia' | 'semana' | 'mes' | 'año' = 'mes'): Promise<AnalisisTemporal[]> {
    const response = await api.get('/analisis/temporal', {
      params: { granularidad }
    });
    return response.data;
  }
};

export default apiService;