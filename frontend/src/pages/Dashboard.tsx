import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  FileText, 
  Building2, 
  TrendingUp, 
  Calendar,
  AlertCircle,
  Loader2,
  BarChart3
} from 'lucide-react';
import { Statistics } from '../types';
import { apiService } from '../services/api';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiService.getStatistics();
        setStats(data);
      } catch (err) {
        console.error('Error fetching statistics:', err);
        setError('Error al cargar las estadísticas. Verifique que el servidor backend esté ejecutándose en http://localhost:8000');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
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
        <span>Cargando estadísticas...</span>
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

  if (!stats) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600">No se pudieron cargar las estadísticas.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Dashboard de Licitaciones
        </h1>
        <p className="text-gray-600">
          Monitoreo en tiempo real de procesos de licitación gubernamental
        </p>
      </div>

      {/* Main Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Licitaciones */}
        <div className="stat-card">
          <div className="flex items-center">
            <FileText className="h-8 w-8 text-blue-600 mr-3" />
            <div>
              <div className="stat-number text-blue-600">
                {formatNumber(stats.total)}
              </div>
              <div className="stat-label">Total Licitaciones</div>
            </div>
          </div>
        </div>

        {/* Monto Total */}
        <div className="stat-card">
          <div className="flex items-center">
            <TrendingUp className="h-8 w-8 text-green-600 mr-3" />
            <div>
              <div className="stat-number text-green-600">
                {stats.montos?.monto_total ? formatCurrency(stats.montos.monto_total) : 'N/A'}
              </div>
              <div className="stat-label">Monto Total</div>
            </div>
          </div>
        </div>

        {/* Entidades */}
        <div className="stat-card">
          <div className="flex items-center">
            <Building2 className="h-8 w-8 text-purple-600 mr-3" />
            <div>
              <div className="stat-number text-purple-600">
                {stats.por_fuente?.length || 0}
              </div>
              <div className="stat-label">Fuentes Activas</div>
            </div>
          </div>
        </div>

        {/* Promedio */}
        <div className="stat-card">
          <div className="flex items-center">
            <Calendar className="h-8 w-8 text-orange-600 mr-3" />
            <div>
              <div className="stat-number text-orange-600">
                {stats.montos?.monto_promedio ? formatCurrency(stats.montos.monto_promedio) : 'N/A'}
              </div>
              <div className="stat-label">Monto Promedio</div>
            </div>
          </div>
        </div>
      </div>

      {/* Charts and Tables Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Por Fuente */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold">Licitaciones por Fuente</h3>
          </div>
          <div className="card-body">
            <div className="space-y-3">
              {stats.por_fuente?.slice(0, 5).map((fuente) => (
                <div key={fuente.fuente} className="flex items-center justify-between">
                  <span className="text-sm font-medium">{fuente.fuente}</span>
                  <div className="flex items-center">
                    <div 
                      className="bg-blue-200 h-2 rounded mr-3"
                      style={{ 
                        width: `${(fuente.cantidad / stats.total) * 100}px`,
                        minWidth: '20px'
                      }}
                    />
                    <span className="text-sm text-gray-600">
                      {formatNumber(fuente.cantidad)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Por Estado */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold">Licitaciones por Estado</h3>
          </div>
          <div className="card-body">
            <div className="space-y-3">
              {stats.por_estado?.slice(0, 5).map((estado) => (
                <div key={estado.estado} className="flex items-center justify-between">
                  <span className="text-sm font-medium">{estado.estado || 'Sin estado'}</span>
                  <div className="flex items-center">
                    <div 
                      className="bg-green-200 h-2 rounded mr-3"
                      style={{ 
                        width: `${(estado.cantidad / stats.total) * 100}px`,
                        minWidth: '20px'
                      }}
                    />
                    <span className="text-sm text-gray-600">
                      {formatNumber(estado.cantidad)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Updates */}
      <div className="card">
        <div className="card-header">
          <h3 className="font-semibold">Últimas Actualizaciones</h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stats.ultimas_actualizaciones?.map((update) => (
              <div key={update.fuente} className="bg-gray-50 p-4 rounded">
                <div className="font-medium text-sm">{update.fuente}</div>
                <div className="text-xs text-gray-600 mt-1">
                  {update.ultima_actualizacion ? 
                    format(new Date(update.ultima_actualizacion), 'PPp', { locale: es }) :
                    'No disponible'
                  }
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-4 justify-center">
        <Link 
          to="/licitaciones" 
          className="btn btn-primary"
        >
          <FileText className="h-4 w-4 mr-2" />
          Ver Todas las Licitaciones
        </Link>
        <Link 
          to="/analytics" 
          className="btn btn-secondary"
        >
          <BarChart3 className="h-4 w-4 mr-2" />
          Ver Análisis Detallado
        </Link>
      </div>
    </div>
  );
};

export default Dashboard;