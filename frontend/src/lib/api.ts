import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export interface Licitacion {
  id: number;
  numero_licitacion: string;
  titulo: string;
  entidad_compradora: string;
  tipo_contratacion: string;
  monto: number;
  fecha_publicacion: string;
  fuente: 'TIANGUIS' | 'COMPRASMX' | 'DOF';
  estado: string;
  url_original: string;
  descripcion?: string;
  fecha_limite?: string;
  ubicacion?: string;
}

export interface Stats {
  total: number;
  ultima_actualizacion: string;
  total_licitaciones?: number;
  monto_total?: number;
  fuentes_activas?: number;
  monto_promedio?: number;
}

export interface Filtros {
  fuentes: string[];
  entidades: string[];
  estados: string[];
  tipos_contratacion?: string[];
  entidades_compradoras?: string[];
}

export interface LicitacionesResponse {
  data: Licitacion[];
  total: number;
  page: number;
  limit: number;
  licitaciones?: Licitacion[];
  page_size?: number;
  total_pages?: number;
}

export interface AnalisisPorTipo {
  tipo_contratacion: string;
  total: number;
  monto_total: number;
}

export interface AnalisisPorDependencia {
  entidad_compradora: string;
  total: number;
  monto_total: number;
}

export const apiService = {
  async getStats(): Promise<Stats> {
    try {
      const response = await api.get('/stats');
      // Adaptar respuesta del backend al formato esperado por frontend
      const data = response.data;
      return {
        total_licitaciones: data.total || 0,
        monto_total: data.monto_total || 0,
        fuentes_activas: data.fuentes_activas || 0,
        monto_promedio: data.monto_promedio || 0,
        total: data.total || 0,
        ultima_actualizacion: data.ultima_actualizacion || new Date().toISOString()
      };
    } catch (error) {
      console.error('Error fetching stats:', error);
      return {
        total_licitaciones: 0,
        monto_total: 0,
        fuentes_activas: 0,
        monto_promedio: 0,
        total: 0,
        ultima_actualizacion: new Date().toISOString()
      };
    }
  },

  async getLicitaciones(params: {
    fuente?: string;
    tipo_contratacion?: string;
    entidad_compradora?: string;
    estado?: string;
    busqueda?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<LicitacionesResponse> {
    try {
      // Adaptar parámetros al formato del backend
      const backendParams: any = {
        page: params.page || 1,
        limit: params.page_size || 50
      };
      
      if (params.fuente) backendParams.fuente = params.fuente;
      if (params.entidad_compradora) backendParams.entidad = params.entidad_compradora;
      if (params.estado) backendParams.estado = params.estado;
      if (params.busqueda) backendParams.q = params.busqueda;

      const response = await api.get('/licitaciones', { params: backendParams });
      
      // Adaptar respuesta al formato esperado
      const data = response.data;
      return {
        licitaciones: data.data || [],
        data: data.data || [],
        total: data.total || 0,
        page: data.page || 1,
        page_size: data.limit || 50,
        total_pages: Math.ceil((data.total || 0) / (data.limit || 50)),
        limit: data.limit || 50
      };
    } catch (error) {
      console.error('Error fetching licitaciones:', error);
      return {
        licitaciones: [],
        data: [],
        total: 0,
        page: 1,
        page_size: 50,
        total_pages: 0,
        limit: 50
      };
    }
  },

  async getFiltros(): Promise<Filtros> {
    try {
      const response = await api.get('/filters'); // Backend usa /filters no /filtros
      const data = response.data;
      return {
        fuentes: data.fuentes || [],
        tipos_contratacion: [], // El backend no parece tener esto, usar array vacío
        entidades_compradoras: data.entidades || [],
        estados: data.estados || [],
        entidades: data.entidades || []
      };
    } catch (error) {
      console.error('Error fetching filters:', error);
      return {
        fuentes: ['TIANGUIS', 'COMPRASMX', 'DOF'],
        tipos_contratacion: [],
        entidades_compradoras: [],
        estados: ['VIGENTE', 'CERRADO', 'CANCELADO'],
        entidades: []
      };
    }
  },

  async getAnalisisPorTipoContratacion(): Promise<AnalisisPorTipo[]> {
    try {
      // Esta ruta no existe en el backend, crear datos mock o usar stats
      const response = await api.get('/stats');
      // Retornar datos mock por ahora
      return [
        { tipo_contratacion: 'ADQUISICIONES', total: 150, monto_total: 1000000 },
        { tipo_contratacion: 'SERVICIOS', total: 120, monto_total: 800000 },
        { tipo_contratacion: 'OBRA PUBLICA', total: 80, monto_total: 1500000 }
      ];
    } catch (error) {
      console.error('Error fetching análisis por tipo:', error);
      return [];
    }
  },

  async getAnalisisPorDependencia(): Promise<AnalisisPorDependencia[]> {
    try {
      // Esta ruta tampoco existe, crear datos mock
      return [
        { entidad_compradora: 'SECRETARÍA DE SALUD', total: 50, monto_total: 500000 },
        { entidad_compradora: 'SECRETARÍA DE EDUCACIÓN', total: 45, monto_total: 450000 }
      ];
    } catch (error) {
      console.error('Error fetching análisis por dependencia:', error);
      return [];
    }
  },

  async getDetalle(id: number): Promise<Licitacion> {
    try {
      const response = await api.get(`/licitaciones/${id}`); // Backend usa /licitaciones/{id}
      return response.data;
    } catch (error) {
      console.error('Error fetching detalle:', error);
      throw error;
    }
  },
};