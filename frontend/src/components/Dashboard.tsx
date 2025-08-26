import { useState, useEffect, useCallback } from 'react';
import { toast } from '@/hooks/use-toast';
import { apiService } from '@/services/api';
import { 
  Statistics as Stats, 
  Filtros, 
  LicitacionesResponse, 
  AnalisisContratacion as AnalisisPorTipo
} from '@/types';

import Header from './dashboard/Header';
import MetricCards from './dashboard/MetricCards';
import Filters from './dashboard/Filters';
import Charts from './dashboard/Charts';
import DataTable from './dashboard/DataTable';

const Dashboard = () => {
  // State
  const [stats, setStats] = useState<Stats | null>(null);
  const [filtros, setFiltros] = useState<Filtros | null>(null);
  const [licitaciones, setLicitaciones] = useState<LicitacionesResponse | null>(null);
  const [tiposData, setTiposData] = useState<AnalisisPorTipo[]>([]);
  
  // Loading states
  const [statsLoading, setStatsLoading] = useState(true);
  const [filtrosLoading, setFiltrosLoading] = useState(true);
  const [licitacionesLoading, setLicitacionesLoading] = useState(true);
  const [chartsLoading, setChartsLoading] = useState(true);

  // Filters
  const [currentFilters, setCurrentFilters] = useState<{
    fuente?: string;
    tipo_contratacion?: string;
    entidad_compradora?: string;
    estado?: string;
    busqueda?: string;
  }>({});
  const [currentPage, setCurrentPage] = useState(1);

  // Fetch functions
  const fetchStats = useCallback(async () => {
    try {
      const data = await apiService.getStatistics();
      setStats(data);
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudieron cargar las estadísticas",
        variant: "destructive",
      });
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const fetchFiltros = useCallback(async () => {
    try {
      const data = await apiService.getFilters();
      setFiltros(data);
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudieron cargar los filtros",
        variant: "destructive",
      });
    } finally {
      setFiltrosLoading(false);
    }
  }, []);

  const fetchLicitaciones = useCallback(async () => {
    setLicitacionesLoading(true);
    try {
      const data = await apiService.getLicitaciones({
        ...currentFilters,
        page: currentPage,
        page_size: 50,
      });
      setLicitaciones(data);
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudieron cargar las licitaciones",
        variant: "destructive",
      });
    } finally {
      setLicitacionesLoading(false);
    }
  }, [currentFilters, currentPage]);

  const fetchChartsData = useCallback(async () => {
    try {
      const tiposAnalisis = await apiService.getAnalisisPorTipoContratacion();
      setTiposData(tiposAnalisis);
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudieron cargar los datos de gráficos",
        variant: "destructive",
      });
    } finally {
      setChartsLoading(false);
    }
  }, []);

  // Event handlers
  const handleFilterChange = (filters: typeof currentFilters) => {
    setCurrentFilters(filters);
    setCurrentPage(1); // Reset to first page when filters change
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // Effects
  useEffect(() => {
    fetchStats();
    fetchFiltros();
    fetchChartsData();
  }, [fetchStats, fetchFiltros, fetchChartsData]);

  useEffect(() => {
    fetchLicitaciones();
  }, [fetchLicitaciones]);

  // Auto-refresh stats every 5 minutes
  useEffect(() => {
    const interval = setInterval(fetchStats, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // Prepare charts data
  const fuentesData = stats
    ? [
        { 
          name: 'TIANGUIS', 
          value: stats.por_fuente?.find(f => f.fuente === 'TIANGUIS')?.cantidad || 0, 
          color: '#3b82f6' 
        },
        { 
          name: 'COMPRASMX', 
          value: stats.por_fuente?.find(f => f.fuente === 'COMPRASMX')?.cantidad || 0, 
          color: '#a855f7' 
        },
        { 
          name: 'DOF', 
          value: stats.por_fuente?.find(f => f.fuente === 'DOF')?.cantidad || 0, 
          color: '#059669' 
        },
      ]
    : [];

  return (
    <div className="min-h-screen p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        <Header />
        
        <MetricCards stats={stats} loading={statsLoading} />
        
        <Filters
          filtros={filtros}
          onFilterChange={handleFilterChange}
          loading={filtrosLoading}
        />
        
        <Charts
          fuentesData={fuentesData}
          tiposData={tiposData}
          loading={chartsLoading}
        />
        
        <DataTable
          data={licitaciones}
          loading={licitacionesLoading}
          onPageChange={handlePageChange}
        />
      </div>
    </div>
  );
};

export default Dashboard;