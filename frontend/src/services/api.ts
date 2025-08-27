import axios from 'axios';
import {
  Licitacion,
  LicitacionesResponse,
  Statistics,
  Filtros,
  FiltrosGeograficos,
  SearchFilters,
  AnalisisContratacion,
  AnalisisDependencia,
  AnalisisFuente,
  AnalisisTemporal,
  AnalisisEstado,
  AnalisisGeografico
} from '../types';

// Configure axios base URL - use proxy in development, direct in production
const baseURL = import.meta.env.DEV ? '/api' : 'http://localhost:8000';

const api = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for debugging
api.interceptors.request.use(
  request => {
    console.log('API Request:', request.method?.toUpperCase(), request.url);
    return request;
  },
  error => {
    console.error('Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  response => {
    console.log('API Response:', response.status, response.config.url);
    return response;
  },
  error => {
    console.error('API Error:', {
      status: error.response?.status,
      url: error.config?.url,
      message: error.message,
      data: error.response?.data
    });
    
    // Enhanced error message for common issues
    if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
      error.userMessage = 'No se puede conectar al servidor. Verifique que el backend esté ejecutándose en http://localhost:8000';
    } else if (error.response?.status >= 500) {
      error.userMessage = 'Error interno del servidor. Por favor, intente nuevamente.';
    } else if (error.response?.status === 404) {
      error.userMessage = 'Recurso no encontrado.';
    } else if (error.response?.status >= 400) {
      error.userMessage = error.response?.data?.detail || 'Error en la solicitud.';
    } else {
      error.userMessage = 'Error de conexión. Verifique su conexión a internet.';
    }
    
    return Promise.reject(error);
  }
);

export const apiService = {
  // Basic info
  async getApiInfo() {
    try {
      const response = await api.get('/');
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Statistics
  async getStatistics(): Promise<Statistics> {
    try {
      const response = await api.get('/stats');
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Top entidad
  async getTopEntidad() {
    try {
      const response = await api.get('/top-entidad');
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Top tipo contratación
  async getTopTipoContratacion() {
    try {
      const response = await api.get('/top-tipo-contratacion');
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Licitaciones with filters
  async getLicitaciones(filters: SearchFilters = {}): Promise<LicitacionesResponse> {
    try {
      const params = new URLSearchParams();
      
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (Array.isArray(value)) {
            // For array parameters, add each value separately
            value.forEach(v => params.append(key, v.toString()));
          } else if (value !== '') {
            params.append(key, value.toString());
          }
        }
      });

      const response = await api.get(`/licitaciones?${params}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Get single licitacion detail
  async getLicitacionDetail(id: number): Promise<Licitacion> {
    try {
      const response = await api.get(`/detalle/${id}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Get available filters
  async getFilters(): Promise<Filtros> {
    try {
      const response = await api.get('/filtros');
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Get geographic filters (NEW)
  async getFiltrosGeograficos(): Promise<FiltrosGeograficos> {
    try {
      const response = await api.get('/filtros-geograficos');
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Quick search for autocomplete
  async quickSearch(query: string, limit: number = 10) {
    try {
      const response = await api.get('/busqueda-rapida', {
        params: { q: query, limit }
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Analysis endpoints
  async getAnalisisPorTipoContratacion(): Promise<AnalisisContratacion[]> {
    try {
      const response = await api.get('/analisis/por-tipo-contratacion');
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  async getAnalisisPorDependencia(limit: number = 20, entidad_federativa?: string): Promise<AnalisisDependencia[]> {
    try {
      const params: any = { limit };
      if (entidad_federativa) {
        params.entidad_federativa = entidad_federativa;
      }
      const response = await api.get('/analisis/por-dependencia', { params });
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  async getAnalisisPorFuente(): Promise<AnalisisFuente[]> {
    try {
      const response = await api.get('/analisis/por-fuente');
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Análisis por estado (NEW)
  async getAnalisisPorEstado(): Promise<AnalisisEstado[]> {
    try {
      const response = await api.get('/analisis/por-estado');
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Análisis geográfico (NEW)
  async getAnalisisGeografico(entidad_federativa?: string): Promise<AnalisisGeografico> {
    try {
      const params = entidad_federativa ? { entidad_federativa } : {};
      const response = await api.get('/analisis/geografico', { params });
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  async getAnalisisTemporal(
    granularidad: 'dia' | 'semana' | 'mes' | 'año' = 'mes',
    entidad_federativa?: string
  ): Promise<AnalisisTemporal[]> {
    try {
      const params: any = { granularidad };
      if (entidad_federativa) {
        params.entidad_federativa = entidad_federativa;
      }
      const response = await api.get('/analisis/temporal', { params });
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  },

  // Análisis temporal acumulado
  async getAnalisisTemporalAcumulado() {
    try {
      const response = await api.get('/analisis/temporal-acumulado');
      return response.data;
    } catch (error: any) {
      throw new Error(error.userMessage || error.message);
    }
  }
};

export default apiService;
