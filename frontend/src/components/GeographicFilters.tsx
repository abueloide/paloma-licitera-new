import React, { useEffect, useState } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { MapPin, Building2, Map } from 'lucide-react';
import { FiltrosGeograficos } from '@/types';
import apiService from '@/services/api';

interface GeographicFiltersProps {
  onFilterChange: (filters: {
    entidad_federativa?: string;
    municipio?: string;
  }) => void;
  selectedEstado?: string;
  selectedMunicipio?: string;
}

export function GeographicFilters({ 
  onFilterChange, 
  selectedEstado, 
  selectedMunicipio 
}: GeographicFiltersProps) {
  const [filtrosGeo, setFiltrosGeo] = useState<FiltrosGeograficos | null>(null);
  const [loading, setLoading] = useState(true);
  const [municipiosFiltrados, setMunicipiosFiltrados] = useState<typeof filtrosGeo.top_municipios>([]);

  useEffect(() => {
    loadFiltrosGeograficos();
  }, []);

  useEffect(() => {
    // Filtrar municipios cuando cambia el estado seleccionado
    if (filtrosGeo && selectedEstado) {
      const municipios = filtrosGeo.top_municipios.filter(
        m => m.entidad_federativa === selectedEstado
      );
      setMunicipiosFiltrados(municipios);
    } else {
      setMunicipiosFiltrados(filtrosGeo?.top_municipios || []);
    }
  }, [selectedEstado, filtrosGeo]);

  const loadFiltrosGeograficos = async () => {
    try {
      setLoading(true);
      const data = await apiService.getFiltrosGeograficos();
      setFiltrosGeo(data);
    } catch (error) {
      console.error('Error cargando filtros geográficos:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEstadoChange = (value: string) => {
    if (value === 'all') {
      onFilterChange({ entidad_federativa: undefined, municipio: undefined });
    } else {
      onFilterChange({ entidad_federativa: value, municipio: undefined });
    }
  };

  const handleMunicipioChange = (value: string) => {
    if (value === 'all') {
      onFilterChange({ entidad_federativa: selectedEstado, municipio: undefined });
    } else {
      onFilterChange({ entidad_federativa: selectedEstado, municipio: value });
    }
  };

  if (loading || !filtrosGeo) {
    return (
      <div className="space-y-4">
        <div className="animate-pulse">
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  const porcentajeCobertura = filtrosGeo.cobertura.total_licitaciones > 0
    ? ((filtrosGeo.cobertura.licitaciones_con_estado / filtrosGeo.cobertura.total_licitaciones) * 100).toFixed(1)
    : 0;

  return (
    <div className="space-y-4">
      {/* Estadísticas de cobertura */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Map className="h-5 w-5 text-blue-600" />
            <span className="text-sm font-medium text-blue-900">
              Cobertura Geográfica
            </span>
          </div>
          <span className="text-sm font-bold text-blue-600">
            {porcentajeCobertura}%
          </span>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-4 text-xs text-blue-800">
          <div>
            <span className="font-medium">{filtrosGeo.cobertura.estados_con_datos}</span> estados
          </div>
          <div>
            <span className="font-medium">{filtrosGeo.cobertura.municipios_con_datos}</span> municipios
          </div>
        </div>
      </div>

      {/* Filtro de Estado */}
      <div className="space-y-2">
        <Label htmlFor="estado-filter" className="flex items-center gap-2">
          <MapPin className="h-4 w-4" />
          Entidad Federativa
        </Label>
        <Select value={selectedEstado || 'all'} onValueChange={handleEstadoChange}>
          <SelectTrigger id="estado-filter">
            <SelectValue placeholder="Seleccionar estado..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los estados</SelectItem>
            {filtrosGeo.entidades_federativas.map(estado => (
              <SelectItem key={estado.entidad_federativa} value={estado.entidad_federativa}>
                <div className="flex justify-between items-center w-full">
                  <span>{estado.entidad_federativa}</span>
                  <span className="text-xs text-muted-foreground ml-2">
                    ({estado.cantidad.toLocaleString()} licitaciones)
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Filtro de Municipio (solo si hay un estado seleccionado) */}
      {selectedEstado && municipiosFiltrados.length > 0 && (
        <div className="space-y-2">
          <Label htmlFor="municipio-filter" className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Municipio
          </Label>
          <Select value={selectedMunicipio || 'all'} onValueChange={handleMunicipioChange}>
            <SelectTrigger id="municipio-filter">
              <SelectValue placeholder="Seleccionar municipio..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los municipios</SelectItem>
              {municipiosFiltrados.map(municipio => (
                <SelectItem key={municipio.municipio} value={municipio.municipio}>
                  <div className="flex justify-between items-center w-full">
                    <span>{municipio.municipio}</span>
                    <span className="text-xs text-muted-foreground ml-2">
                      ({municipio.cantidad} licitaciones)
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Información adicional */}
      {selectedEstado && (
        <div className="text-xs text-muted-foreground bg-gray-50 p-3 rounded">
          {filtrosGeo.entidades_federativas.find(e => e.entidad_federativa === selectedEstado) && (
            <div>
              <strong>{selectedEstado}</strong> tiene{' '}
              {filtrosGeo.entidades_federativas
                .find(e => e.entidad_federativa === selectedEstado)
                ?.municipios_unicos || 0}{' '}
              municipios con licitaciones registradas
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default GeographicFilters;
