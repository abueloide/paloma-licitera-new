export interface Licitacion {
  id: number;
  numero_procedimiento: string;
  titulo: string;
  descripcion?: string;
  entidad_compradora?: string;
  unidad_compradora?: string;
  tipo_procedimiento?: string;
  tipo_contratacion?: string;
  estado?: string;
  fecha_publicacion?: string;
  fecha_apertura?: string;
  fecha_fallo?: string;
  monto_estimado?: number;
  moneda?: string;
  fuente: string;
  url_original?: string;
  fecha_captura?: string;
  hash_contenido?: string;
  datos_originales?: any;
}

export interface LicitacionesResponse {
  data: Licitacion[];
  pagination: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

export interface Statistics {
  total: number;
  por_fuente: Array<{ fuente: string; cantidad: number }>;
  por_estado: Array<{ estado: string; cantidad: number }>;
  por_tipo_contratacion: Array<{ tipo_contratacion: string; cantidad: number }>;
  montos: {
    monto_total: number;
    monto_promedio: number;
    monto_maximo: number;
    monto_minimo: number;
  };
  ultimas_actualizaciones: Array<{ fuente: string; ultima_actualizacion: string }>;
  fecha_consulta: string;
}

export interface Filtros {
  fuentes: Array<{ fuente: string; cantidad: number }>;
  estados: Array<{ estado: string; cantidad: number }>;
  tipos_contratacion: Array<{ tipo_contratacion: string; cantidad: number }>;
  tipos_procedimiento: Array<{ tipo_procedimiento: string; cantidad: number }>;
  top_entidades: Array<{ entidad_compradora: string; cantidad: number }>;
}

export interface SearchFilters {
  fuente?: string;
  estado?: string;
  tipo_contratacion?: string;
  tipo_procedimiento?: string;
  entidad_compradora?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  monto_min?: number;
  monto_max?: number;
  busqueda?: string;
  page?: number;
  page_size?: number;
}

export interface AnalisisContratacion {
  tipo_contratacion: string;
  cantidad: number;
  monto_total: number;
  monto_promedio: number;
  monto_maximo: number;
  monto_minimo: number;
  entidades_unicas: number;
}

export interface AnalisisDependencia {
  entidad_compradora: string;
  cantidad_licitaciones: number;
  monto_total: number;
  monto_promedio: number;
  tipos_contratacion: number;
  tipos_procedimiento: number;
  primera_licitacion: string;
  ultima_licitacion: string;
}

export interface AnalisisFuente {
  fuente: string;
  total_licitaciones: number;
  entidades_unicas: number;
  tipos_contratacion: number;
  con_monto: number;
  monto_total: number;
  monto_promedio: number;
  fecha_mas_antigua: string;
  fecha_mas_reciente: string;
  ultima_actualizacion: string;
}

export interface AnalisisTemporal {
  periodo: string;
  cantidad: number;
  monto_total: number;
  entidades_unicas: number;
  fuentes: number;
}