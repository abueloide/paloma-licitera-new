import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Search, 
  Filter, 
  ChevronLeft, 
  ChevronRight,
  ExternalLink,
  AlertCircle,
  Loader2,
  Eye
} from 'lucide-react';
import { LicitacionesResponse, Filtros, SearchFilters } from '../types';
import { apiService } from '../services/api';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const Licitaciones: React.FC = () => {
  const [data, setData] = useState<LicitacionesResponse | null>(null);
  const [filtros, setFiltros] = useState<Filtros | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  const [searchFilters, setSearchFilters] = useState<SearchFilters>({
    page: 1,
    page_size: 20
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [licitacionesData, filtrosData] = await Promise.all([
          apiService.getLicitaciones(searchFilters),
          apiService.getFilters()
        ]);
        setData(licitacionesData);
        setFiltros(filtrosData);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Error al cargar los datos. Verifique que el servidor backend esté ejecutándose.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [searchFilters]);

  const handleFilterChange = (key: keyof SearchFilters, value: string | number) => {
    setSearchFilters(prev => ({
      ...prev,
      [key]: value || undefined,
      page: 1 // Reset to first page when filtering
    }));
  };

  const handlePageChange = (newPage: number) => {
    setSearchFilters(prev => ({
      ...prev,
      page: newPage
    }));
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'dd/MM/yyyy', { locale: es });
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <Loader2 className="h-8 w-8 animate-spin mr-3" />
        <span>Cargando licitaciones...</span>
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Licitaciones</h1>
          <p className="text-gray-600 mt-1">
            {data?.pagination.total ? `${data.pagination.total} licitaciones encontradas` : 'Sin resultados'}
          </p>
        </div>
        
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="btn btn-outline mt-4 md:mt-0"
        >
          <Filter className="h-4 w-4 mr-2" />
          {showFilters ? 'Ocultar Filtros' : 'Mostrar Filtros'}
        </button>
      </div>

      {/* Search and Filters */}
      <div className="card">
        <div className="card-body">
          {/* Search bar */}
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar por título, descripción o número de procedimiento..."
                className="form-input pl-10"
                value={searchFilters.busqueda || ''}
                onChange={(e) => handleFilterChange('busqueda', e.target.value)}
              />
            </div>
          </div>

          {/* Filters */}
          {showFilters && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Fuente */}
              <div>
                <label className="form-label">Fuente</label>
                <select
                  className="form-select"
                  value={searchFilters.fuente || ''}
                  onChange={(e) => handleFilterChange('fuente', e.target.value)}
                >
                  <option value="">Todas las fuentes</option>
                  {filtros?.fuentes?.map((fuente) => (
                    <option key={fuente.fuente} value={fuente.fuente}>
                      {fuente.fuente} ({fuente.cantidad})
                    </option>
                  ))}
                </select>
              </div>

              {/* Estado */}
              <div>
                <label className="form-label">Estado</label>
                <select
                  className="form-select"
                  value={searchFilters.estado || ''}
                  onChange={(e) => handleFilterChange('estado', e.target.value)}
                >
                  <option value="">Todos los estados</option>
                  {filtros?.estados?.map((estado) => (
                    <option key={estado.estado} value={estado.estado}>
                      {estado.estado} ({estado.cantidad})
                    </option>
                  ))}
                </select>
              </div>

              {/* Tipo de Contratación */}
              <div>
                <label className="form-label">Tipo de Contratación</label>
                <select
                  className="form-select"
                  value={searchFilters.tipo_contratacion || ''}
                  onChange={(e) => handleFilterChange('tipo_contratacion', e.target.value)}
                >
                  <option value="">Todos los tipos</option>
                  {filtros?.tipos_contratacion?.map((tipo) => (
                    <option key={tipo.tipo_contratacion} value={tipo.tipo_contratacion}>
                      {tipo.tipo_contratacion} ({tipo.cantidad})
                    </option>
                  ))}
                </select>
              </div>

              {/* Entidad Compradora */}
              <div>
                <label className="form-label">Entidad Compradora</label>
                <select
                  className="form-select"
                  value={searchFilters.entidad_compradora || ''}
                  onChange={(e) => handleFilterChange('entidad_compradora', e.target.value)}
                >
                  <option value="">Todas las entidades</option>
                  {filtros?.top_entidades?.slice(0, 20).map((entidad) => (
                    <option key={entidad.entidad_compradora} value={entidad.entidad_compradora}>
                      {entidad.entidad_compradora} ({entidad.cantidad})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Results Table */}
      <div className="card">
        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>Número</th>
                <th>Título</th>
                <th>Entidad</th>
                <th>Tipo</th>
                <th>Estado</th>
                <th>Fecha Pub.</th>
                <th>Monto</th>
                <th>Fuente</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {data?.data?.map((licitacion) => (
                <tr key={licitacion.id}>
                  <td className="font-medium text-sm">
                    {licitacion.numero_procedimiento}
                  </td>
                  <td>
                    <div className="max-w-xs">
                      <div className="font-medium text-sm truncate">
                        {licitacion.titulo}
                      </div>
                      {licitacion.descripcion && (
                        <div className="text-xs text-gray-500 truncate">
                          {licitacion.descripcion}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="text-sm">
                    <div className="max-w-xs truncate">
                      {licitacion.entidad_compradora || 'N/A'}
                    </div>
                  </td>
                  <td className="text-sm">
                    {licitacion.tipo_contratacion || 'N/A'}
                  </td>
                  <td>
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                      licitacion.estado === 'ACTIVA' || licitacion.estado === 'ABIERTA' 
                        ? 'bg-green-100 text-green-800'
                        : licitacion.estado === 'CERRADA' || licitacion.estado === 'FINALIZADA'
                        ? 'bg-gray-100 text-gray-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}>
                      {licitacion.estado || 'N/A'}
                    </span>
                  </td>
                  <td className="text-sm">
                    {licitacion.fecha_publicacion ? 
                      formatDate(licitacion.fecha_publicacion) : 'N/A'
                    }
                  </td>
                  <td className="text-sm">
                    {licitacion.monto_estimado ? 
                      formatCurrency(licitacion.monto_estimado) : 'N/A'
                    }
                  </td>
                  <td>
                    <span className="inline-flex px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                      {licitacion.fuente}
                    </span>
                  </td>
                  <td>
                    <div className="flex space-x-2">
                      <Link
                        to={`/licitaciones/${licitacion.id}`}
                        className="text-blue-600 hover:text-blue-800"
                        title="Ver detalles"
                      >
                        <Eye className="h-4 w-4" />
                      </Link>
                      {licitacion.url_original && (
                        <a
                          href={licitacion.url_original}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-gray-600 hover:text-gray-800"
                          title="Ver original"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data?.pagination && data.pagination.total_pages > 1 && (
          <div className="px-6 py-4 border-t">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Página {data.pagination.page} de {data.pagination.total_pages} 
                ({data.pagination.total} resultados)
              </div>
              
              <div className="flex space-x-2">
                <button
                  onClick={() => handlePageChange(data.pagination.page - 1)}
                  disabled={data.pagination.page <= 1}
                  className="btn btn-outline disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                
                <span className="px-3 py-2 text-sm">
                  {data.pagination.page}
                </span>
                
                <button
                  onClick={() => handlePageChange(data.pagination.page + 1)}
                  disabled={data.pagination.page >= data.pagination.total_pages}
                  className="btn btn-outline disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Licitaciones;