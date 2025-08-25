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
  total_licitaciones: number;
  monto_total: number;
  fuentes_activas: number;
  monto_promedio: number;
}

export interface Filtros {
  fuentes: string[];
  tipos_contratacion: string[];
  entidades_compradoras: string[];
  estados: string[];
}

export interface LicitacionesResponse {
  licitaciones: Licitacion[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
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
    const response = await api.get('/stats');
    return response.data;
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
    const response = await api.get('/licitaciones', { params });
    return response.data;
  },

  async getFiltros(): Promise<Filtros> {
    const response = await api.get('/filtros');
    return response.data;
  },

  async getAnalisisPorTipoContratacion(): Promise<AnalisisPorTipo[]> {
    const response = await api.get('/analisis/por-tipo-contratacion');
    return response.data;
  },

  async getAnalisisPorDependencia(): Promise<AnalisisPorDependencia[]> {
    const response = await api.get('/analisis/por-dependencia');
    return response.data;
  },

  async getDetalle(id: number): Promise<Licitacion> {
    const response = await api.get(`/detalle/${id}`);
    return response.data;
  },
};