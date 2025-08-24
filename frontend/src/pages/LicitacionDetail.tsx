import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  ExternalLink, 
  Building2, 
  Calendar, 
  DollarSign,
  FileText,
  Tag,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { Licitacion } from '../types';
import { apiService } from '../services/api';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const LicitacionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [licitacion, setLicitacion] = useState<Licitacion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLicitacion = async () => {
      if (!id) return;
      
      try {
        setLoading(true);
        setError(null);
        const data = await apiService.getLicitacionDetail(parseInt(id));
        setLicitacion(data);
      } catch (err) {
        console.error('Error fetching licitacion detail:', err);
        setError('Error al cargar los detalles de la licitación.');
      } finally {
        setLoading(false);
      }
    };

    fetchLicitacion();
  }, [id]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'PPP', { locale: es });
    } catch {
      return dateString;
    }
  };

  const formatDateTime = (dateString: string) => {
    try {
      return format(new Date(dateString), 'PPp', { locale: es });
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <Loader2 className="h-8 w-8 animate-spin mr-3" />
        <span>Cargando detalles...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error">
        <AlertCircle className="h-5 w-5 mr-2 inline" />
        {error}
      </div>
    );
  }

  if (!licitacion) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600">Licitación no encontrada.</p>
        <Link to="/licitaciones" className="btn btn-primary mt-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Volver a Licitaciones
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link 
          to="/licitaciones" 
          className="btn btn-outline"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Volver
        </Link>
        
        {licitacion.url_original && (
          <a
            href={licitacion.url_original}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Ver Original
          </a>
        )}
      </div>

      {/* Main Information */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                {licitacion.titulo}
              </h1>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <span className="flex items-center">
                  <FileText className="h-4 w-4 mr-1" />
                  {licitacion.numero_procedimiento}
                </span>
                <span className="flex items-center">
                  <Tag className="h-4 w-4 mr-1" />
                  {licitacion.fuente}
                </span>
              </div>
            </div>
            
            {licitacion.estado && (
              <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${
                licitacion.estado === 'ACTIVA' || licitacion.estado === 'ABIERTA' 
                  ? 'bg-green-100 text-green-800'
                  : licitacion.estado === 'CERRADA' || licitacion.estado === 'FINALIZADA'
                  ? 'bg-gray-100 text-gray-800'
                  : 'bg-blue-100 text-blue-800'
              }`}>
                {licitacion.estado}
              </span>
            )}
          </div>
        </div>
        
        <div className="card-body">
          {licitacion.descripcion && (
            <div className="mb-6">
              <h3 className="font-semibold text-gray-900 mb-2">Descripción</h3>
              <p className="text-gray-700 leading-relaxed">
                {licitacion.descripcion}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Entity Information */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center">
              <Building2 className="h-5 w-5 mr-2 text-blue-600" />
              <h3 className="font-semibold">Información de Entidad</h3>
            </div>
          </div>
          <div className="card-body space-y-4">
            {licitacion.entidad_compradora && (
              <div>
                <label className="text-sm font-medium text-gray-600">Entidad Compradora</label>
                <p className="mt-1 text-gray-900">{licitacion.entidad_compradora}</p>
              </div>
            )}
            
            {licitacion.unidad_compradora && (
              <div>
                <label className="text-sm font-medium text-gray-600">Unidad Compradora</label>
                <p className="mt-1 text-gray-900">{licitacion.unidad_compradora}</p>
              </div>
            )}
            
            {licitacion.tipo_procedimiento && (
              <div>
                <label className="text-sm font-medium text-gray-600">Tipo de Procedimiento</label>
                <p className="mt-1 text-gray-900">{licitacion.tipo_procedimiento}</p>
              </div>
            )}
            
            {licitacion.tipo_contratacion && (
              <div>
                <label className="text-sm font-medium text-gray-600">Tipo de Contratación</label>
                <p className="mt-1 text-gray-900">{licitacion.tipo_contratacion}</p>
              </div>
            )}
          </div>
        </div>

        {/* Dates and Money */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center">
              <Calendar className="h-5 w-5 mr-2 text-green-600" />
              <h3 className="font-semibold">Fechas y Montos</h3>
            </div>
          </div>
          <div className="card-body space-y-4">
            {licitacion.fecha_publicacion && (
              <div>
                <label className="text-sm font-medium text-gray-600">Fecha de Publicación</label>
                <p className="mt-1 text-gray-900">{formatDate(licitacion.fecha_publicacion)}</p>
              </div>
            )}
            
            {licitacion.fecha_apertura && (
              <div>
                <label className="text-sm font-medium text-gray-600">Fecha de Apertura</label>
                <p className="mt-1 text-gray-900">{formatDate(licitacion.fecha_apertura)}</p>
              </div>
            )}
            
            {licitacion.fecha_fallo && (
              <div>
                <label className="text-sm font-medium text-gray-600">Fecha de Fallo</label>
                <p className="mt-1 text-gray-900">{formatDate(licitacion.fecha_fallo)}</p>
              </div>
            )}
            
            {licitacion.monto_estimado && (
              <div>
                <label className="text-sm font-medium text-gray-600">Monto Estimado</label>
                <p className="mt-1 text-gray-900 text-lg font-semibold text-green-600">
                  {formatCurrency(licitacion.monto_estimado)}
                  {licitacion.moneda && licitacion.moneda !== 'MXN' && (
                    <span className="text-sm text-gray-500 ml-2">({licitacion.moneda})</span>
                  )}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Technical Information */}
      <div className="card">
        <div className="card-header">
          <h3 className="font-semibold">Información Técnica</h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div>
              <label className="text-sm font-medium text-gray-600">ID del Sistema</label>
              <p className="mt-1 text-gray-900">{licitacion.id}</p>
            </div>
            
            <div>
              <label className="text-sm font-medium text-gray-600">Fuente de Datos</label>
              <p className="mt-1 text-gray-900">{licitacion.fuente}</p>
            </div>
            
            {licitacion.fecha_captura && (
              <div>
                <label className="text-sm font-medium text-gray-600">Fecha de Captura</label>
                <p className="mt-1 text-gray-900">{formatDateTime(licitacion.fecha_captura)}</p>
              </div>
            )}
            
            {licitacion.hash_contenido && (
              <div className="md:col-span-2 lg:col-span-3">
                <label className="text-sm font-medium text-gray-600">Hash de Contenido</label>
                <p className="mt-1 text-gray-900 font-mono text-xs break-all">
                  {licitacion.hash_contenido}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Raw Data */}
      {licitacion.datos_originales && (
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold">Datos Originales</h3>
          </div>
          <div className="card-body">
            <div className="bg-gray-50 rounded p-4 overflow-x-auto">
              <pre className="text-xs text-gray-700">
                {JSON.stringify(licitacion.datos_originales, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LicitacionDetail;