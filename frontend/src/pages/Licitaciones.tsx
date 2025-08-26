import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, 
  Filter, 
  ChevronLeft, 
  ChevronRight,
  AlertCircle,
  Loader2,
  Eye
} from 'lucide-react';
import { LicitacionesResponse, Filtros, SearchFilters } from '../types';
import { apiService } from '../services/api';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const Licitaciones: React.FC = () => {
  const navigate = useNavigate();
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
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin mr-3" />
        <span>Cargando licitaciones...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
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
          <h1 className="text-2xl font-bold text-gray-900">Dashboard de Licitaciones</h1>
          <p className="text-gray-600 mt-1">
            {data?.pagination.total ? `${data.pagination.total} licitaciones encontradas` : 'Sin resultados'}
          </p>
        </div>
        
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="mt-4 md:mt-0 inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
        >
          <Filter className="h-4 w-4 mr-2" />
          {showFilters ? 'Ocultar Filtros' : 'Mostrar Filtros'}
        </button>
      </div>

      {/* Search and Filters */}
      <div className="bg-white shadow rounded-lg">
        <div className="p-6">
          {/* Search bar */}
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar por título, descripción o número de procedimiento..."
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                value={searchFilters.busqueda || ''}
                onChange={(e) => handleFilterChange('busqueda', e.target.value)}
              />
            </div>
          </div>

          {/* Filters - Solo los marcados con asterisco */}
          {showFilters && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Entidad Compradora * */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Entidad Compradora *
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
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

              {/* Tipo de Procedimiento * */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo de Procedimiento *
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                  value={searchFilters.tipo_procedimiento || ''}
                  onChange={(e) => handleFilterChange('tipo_procedimiento', e.target.value)}
                >
                  <option value="">Todos los tipos</option>
                  {filtros?.tipos_procedimiento?.map((tipo) => (
                    <option key={tipo.tipo_procedimiento} value={tipo.tipo_procedimiento}>
                      {tipo.tipo_procedimiento} ({tipo.cantidad})
                    </option>
                  ))}
                </select>
              </div>

              {/* Tipo de Contratación * */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo de Contratación *
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
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

              {/* Fecha Publicación Desde * */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fecha Publicación (Desde) *
                </label>
                <input
                  type="date"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                  value={searchFilters.fecha_publicacion_inicio || ''}
                  onChange={(e) => handleFilterChange('fecha_publicacion_inicio', e.target.value)}
                />
              </div>

              {/* Fecha Apertura * */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fecha Apertura *
                </label>
                <input
                  type="date"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                  value={searchFilters.fecha_apertura || ''}
                  onChange={(e) => handleFilterChange('fecha_apertura', e.target.value)}
                />
              </div>

              {/* Fuente * */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fuente *
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
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
            </div>
          )}
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Número Procedimiento
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Título
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Entidad Compradora
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo Procedimiento
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo Contratación
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fecha Publicación
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fecha Apertura
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fuente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data?.data?.map((licitacion) => (
                <tr 
                  key={licitacion.id} 
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/licitaciones/${licitacion.id}`)}
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {licitacion.numero_procedimiento || 'N/A'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    <div className="max-w-xs">
                      <div className="font-medium truncate">
                        {licitacion.titulo || 'Sin título'}
                      </div>
                      {licitacion.descripcion && (
                        <div className="text-xs text-gray-500 truncate mt-1">
                          {licitacion.descripcion}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    <div className="max-w-xs truncate">
                      {licitacion.entidad_compradora || 'N/A'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {licitacion.tipo_procedimiento || 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {licitacion.tipo_contratacion || 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {licitacion.fecha_publicacion ? 
                      formatDate(licitacion.fecha_publicacion) : 'N/A'
                    }
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {licitacion.fecha_apertura ? 
                      formatDate(licitacion.fecha_apertura) : 'N/A'
                    }
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                      {licitacion.fuente}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/licitaciones/${licitacion.id}`);
                      }}
                      className="text-blue-600 hover:text-blue-900"
                      title="Ver detalles"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data?.pagination && data.pagination.total_pages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Mostrando página <span className="font-medium">{data.pagination.page}</span> de{' '}
                <span className="font-medium">{data.pagination.total_pages}</span> 
                {' '}({data.pagination.total} resultados totales)
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handlePageChange(data.pagination.page - 1)}
                  disabled={data.pagination.page <= 1}
                  className="px-3 py-1 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                
                <span className="px-4 py-1 text-sm font-medium text-gray-700">
                  {data.pagination.page} / {data.pagination.total_pages}
                </span>
                
                <button
                  onClick={() => handlePageChange(data.pagination.page + 1)}
                  disabled={data.pagination.page >= data.pagination.total_pages}
                  className="px-3 py-1 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
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