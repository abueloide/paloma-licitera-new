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
  entidad_federativa?: string;  // Nuevo campo
  municipio?: string;  // Nuevo campo
  fecha_publicacion?: string;
  fecha_apertura?: string;
  fecha_fallo?: string;
  fecha_junta_aclaraciones?: string;
  monto_estimado?: number;
  moneda?: string;
  proveedor_ganador?: string;
  caracter?: string;
  uuid_procedimiento?: string;
  fuente: string;
  url_original?: string;
  fecha_captura?: string;
  hash_contenido?: string;
  datos_originales?: any;
  datos_especificos?: DatosEspecificos;  // Nuevo campo
}

// Nuevo tipo para datos específicos
export interface DatosEspecificos {
  // Campos comunes
  procesado?: boolean;
  procesado_fecha?: string;
  
  // Para DOF
  titulo_limpio?: string;
  descripcion_completa?: string;
  fechas_parseadas?: {
    [key: string]: string;
  };
  ubicacion_extraida?: {
    localidad?: string;
    municipio?: string;
    estado?: string;
    ciudad?: string;
    direccion?: string;
  };
  info_tecnica?: {
    volumen_obra?: string;
    cantidad?: string;
    unidad?: string;
    especificaciones?: string;
    detalles_convocatoria?: string;
    visita_requerida?: boolean;
    caracter_procedimiento?: string;
  };
  
  // Para ComprasMX
  tipo_procedimiento?: string;
  caracter?: string;
  forma_procedimiento?: string;
  medio_utilizado?: string;
  codigo_contrato?: string;
  
  // Para Tianguis Digital (OCDS)
  ocds_data?: any;
  classification?: any;
  procuring_entity?: any;
  items?: any[];
  documents?: any[];
  milestones?: any[];
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
  por_entidad_federativa: Array<{ entidad_federativa: string; cantidad: number }>;  // Nuevo
  por_tipo_contratacion: Array<{ tipo_contratacion: string; cantidad: number }>;
  procesamiento: {  // Nuevo
    con_entidad: number;
    con_municipio: number;
    con_datos_especificos: number;
  };
  top_entidad?: { entidad_compradora: string; cantidad: number };
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

// Nuevo tipo para filtros geográficos
export interface FiltrosGeograficos {
  entidades_federativas: Array<{
    entidad_federativa: string;
    cantidad: number;
    municipios_unicos: number;
  }>;
  top_municipios: Array<{
    municipio: string;
    entidad_federativa: string;
    cantidad: number;
  }>;
  cobertura: {
    estados_con_datos: number;
    municipios_con_datos: number;
    licitaciones_con_estado: number;
    licitaciones_con_municipio: number;
    total_licitaciones: number;
  };
}

export interface SearchFilters {
  fuente?: string;
  estado?: string;
  entidad_federativa?: string;  // Nuevo campo
  municipio?: string;  // Nuevo campo
  tipo_contratacion?: string | string[];
  tipo_procedimiento?: string | string[];
  entidad_compradora?: string | string[];
  fecha_desde?: string;
  fecha_hasta?: string;
  monto_min?: number;
  monto_max?: number;
  dias_apertura?: number;
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
  estados_involucrados?: number;  // Nuevo campo
}

export interface AnalisisDependencia {
  entidad_compradora: string;
  cantidad_licitaciones: number;
  monto_total: number;
  monto_promedio: number;
  tipos_contratacion: number;
  tipos_procedimiento: number;
  estados_cobertura?: number;  // Nuevo campo
  primera_licitacion: string;
  ultima_licitacion: string;
}

export interface AnalisisFuente {
  fuente: string;
  total_licitaciones: number;
  entidades_unicas: number;
  tipos_contratacion: number;
  estados_cubiertos?: number;  // Nuevo campo
  municipios_cubiertos?: number;  // Nuevo campo
  con_estado?: number;  // Nuevo campo
  con_municipio?: number;  // Nuevo campo
  con_monto: number;
  monto_total: number;
  monto_promedio: number;
  fecha_mas_antigua: string;
  fecha_mas_reciente: string;
  ultima_actualizacion: string;
}

// Nuevo tipo para análisis por estado
export interface AnalisisEstado {
  entidad_federativa: string;
  total_licitaciones: number;
  entidades_unicas: number;
  tipos_contratacion: number;
  municipios_unicos: number;
  monto_total: number;
  monto_promedio: number;
  monto_maximo: number;
  primera_licitacion: string;
  ultima_licitacion: string;
  fuentes_datos: number;
}

// Nuevo tipo para análisis geográfico
export interface AnalisisGeografico {
  entidad_federativa?: string;
  resumen?: {
    total: number;
    municipios_totales: number;
    monto_total: number;
    monto_promedio: number;
  };
  municipios?: Array<{
    municipio: string;
    cantidad: number;
    monto_total: number;
    monto_promedio: number;
    entidades_unicas: number;
    tipos_contratacion: number;
  }>;
  distribucion_nacional?: Array<{
    entidad_federativa: string;
    cantidad: number;
    monto_total: number;
    monto_promedio: number;
    municipios_activos: number;
    porcentaje_nacional: number;
  }>;
}

export interface AnalisisTemporal {
  periodo: string;
  cantidad: number;
  monto_total: number;
  entidades_unicas: number;
  fuentes: number;
  estados_involucrados?: number;  // Nuevo campo
}
