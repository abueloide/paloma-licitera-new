import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  PieChart, 
  TrendingUp,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { 
  AnalisisContratacion, 
  AnalisisDependencia, 
  AnalisisFuente 
} from '../types';
import { apiService } from '../services/api';

const Analytics: React.FC = () => {
  const [analisisContratacion, setAnalisisContratacion] = useState<AnalisisContratacion[]>([]);
  const [analisisDependencia, setAnalisisDependencia] = useState<AnalisisDependencia[]>([]);
  const [analisisFuente, setAnalisisFuente] = useState<AnalisisFuente[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalysisData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const [contratacionData, dependenciaData, fuenteData] = await Promise.all([
          apiService.getAnalisisPorTipoContratacion(),
          apiService.getAnalisisPorDependencia(10),
          apiService.getAnalisisPorFuente()
        ]);

        setAnalisisContratacion(contratacionData);
        setAnalisisDependencia(dependenciaData);
        setAnalisisFuente(fuenteData);
      } catch (err) {
        console.error('Error fetching analysis data:', err);
        setError('Error al cargar los datos de análisis. Verifique que el servidor backend esté ejecutándose.');
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysisData();
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('es-MX').format(num);
  };

  if (loading) {
    return (
      <div className="loading">
        <Loader2 className="h-8 w-8 animate-spin mr-3" />
        <span>Cargando análisis...</span>
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
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Análisis de Licitaciones
        </h1>
        <p className="text-gray-600">
          Análisis detallado y estadísticas avanzadas
        </p>
      </div>

      {/* Análisis por Fuente */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center">
            <BarChart3 className="h-5 w-5 mr-2 text-blue-600" />
            <h3 className="font-semibold">Análisis por Fuente de Datos</h3>
          </div>
        </div>
        <div className="card-body">
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Fuente</th>
                  <th>Total</th>
                  <th>Entidades</th>
                  <th>Con Monto</th>
                  <th>Monto Total</th>
                  <th>Promedio</th>
                  <th>Última Actualización</th>
                </tr>
              </thead>
              <tbody>
                {analisisFuente.map((fuente) => (
                  <tr key={fuente.fuente}>
                    <td className="font-medium">{fuente.fuente}</td>
                    <td>{formatNumber(fuente.total_licitaciones)}</td>
                    <td>{formatNumber(fuente.entidades_unicas)}</td>
                    <td>{formatNumber(fuente.con_monto)}</td>
                    <td>{fuente.monto_total ? formatCurrency(fuente.monto_total) : 'N/A'}</td>
                    <td>{fuente.monto_promedio ? formatCurrency(fuente.monto_promedio) : 'N/A'}</td>
                    <td className="text-sm">
                      {fuente.ultima_actualizacion ? 
                        new Date(fuente.ultima_actualizacion).toLocaleString('es-MX') : 'N/A'
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Grid con dos columnas para los otros análisis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Análisis por Tipo de Contratación */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center">
              <PieChart className="h-5 w-5 mr-2 text-green-600" />
              <h3 className="font-semibold">Por Tipo de Contratación</h3>
            </div>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              {analisisContratacion.slice(0, 8).map((tipo, index) => (
                <div key={tipo.tipo_contratacion} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium truncate mr-2">
                      {tipo.tipo_contratacion || 'Sin especificar'}
                    </span>
                    <span className="text-sm text-gray-600">
                      {formatNumber(tipo.cantidad)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-green-600 h-2 rounded-full"
                      style={{ 
                        width: `${Math.min((tipo.cantidad / analisisContratacion[0]?.cantidad) * 100, 100)}%` 
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Monto: {tipo.monto_total ? formatCurrency(tipo.monto_total) : 'N/A'}</span>
                    <span>Promedio: {tipo.monto_promedio ? formatCurrency(tipo.monto_promedio) : 'N/A'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Top Dependencias */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center">
              <TrendingUp className="h-5 w-5 mr-2 text-purple-600" />
              <h3 className="font-semibold">Top Entidades Compradoras</h3>
            </div>
          </div>
          <div className="card-body">
            <div className="space-y-3">
              {analisisDependencia.map((dep, index) => (
                <div key={dep.entidad_compradora} className="border-b border-gray-100 pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0 mr-3">
                      <div className="text-sm font-medium truncate">
                        {dep.entidad_compradora}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {formatNumber(dep.cantidad_licitaciones)} licitaciones
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium">
                        {dep.monto_total ? formatCurrency(dep.monto_total) : 'N/A'}
                      </div>
                      <div className="text-xs text-gray-500">
                        #{index + 1}
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-600">
                    <div>Tipos: {dep.tipos_contratacion}</div>
                    <div>Procedimientos: {dep.tipos_procedimiento}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Resumen de Métricas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="stat-card">
          <div className="text-center">
            <div className="stat-number text-blue-600">
              {analisisFuente.reduce((sum, f) => sum + f.total_licitaciones, 0).toLocaleString('es-MX')}
            </div>
            <div className="stat-label">Total Licitaciones</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="text-center">
            <div className="stat-number text-green-600">
              {analisisFuente.reduce((sum, f) => sum + f.entidades_unicas, 0)}
            </div>
            <div className="stat-label">Entidades Únicas</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="text-center">
            <div className="stat-number text-purple-600">
              {analisisContratacion.length}
            </div>
            <div className="stat-label">Tipos de Contratación</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="text-center">
            <div className="stat-number text-orange-600">
              {analisisFuente.reduce((sum, f) => sum + f.con_monto, 0).toLocaleString('es-MX')}
            </div>
            <div className="stat-label">Con Monto Estimado</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;