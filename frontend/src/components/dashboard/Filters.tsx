import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Filtros } from "@/types";
import { Search, RotateCcw } from "lucide-react";

interface FiltersProps {
  filtros: Filtros | null;
  onFilterChange: (filters: {
    tipo_contratacion?: string[];
    entidad_compradora?: string[];
    dias_apertura?: number;
    busqueda?: string;
  }) => void;
  loading: boolean;
}

const Filters = ({ filtros, onFilterChange, loading }: FiltersProps) => {
  const [selectedTipos, setSelectedTipos] = useState<string[]>([]);
  const [selectedEntidades, setSelectedEntidades] = useState<string[]>([]);
  const [diasApertura, setDiasApertura] = useState<string>("");
  const [busqueda, setBusqueda] = useState("");

  const extractOptions = (data: any, fieldName: string): Array<{value: string, count: number}> => {
    if (!data) return [];
    
    if (Array.isArray(data)) {
      return data
        .map((item: any) => {
          if (typeof item === 'object' && item !== null) {
            return {
              value: item[fieldName] || '',
              count: item.cantidad || 0
            };
          }
          return { value: item, count: 0 };
        })
        .filter(item => item.value !== '');
    }
    
    return [];
  };

  const tiposContratacion = extractOptions(filtros?.tipos_contratacion, 'tipo_contratacion');
  const entidadesCompradoras = extractOptions(filtros?.top_entidades, 'entidad_compradora');

  const handleTipoChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedOptions = Array.from(e.target.selectedOptions, option => option.value);
    const filteredOptions = selectedOptions.filter(opt => opt !== 'all');
    setSelectedTipos(filteredOptions);
    applyFilters(filteredOptions, selectedEntidades, diasApertura);
  };

  const handleEntidadChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedOptions = Array.from(e.target.selectedOptions, option => option.value);
    const filteredOptions = selectedOptions.filter(opt => opt !== 'all');
    setSelectedEntidades(filteredOptions);
    applyFilters(selectedTipos, filteredOptions, diasApertura);
  };

  const handleDiasAperturaChange = (value: string) => {
    setDiasApertura(value);
    applyFilters(selectedTipos, selectedEntidades, value);
  };

  const handleBusquedaChange = (value: string) => {
    setBusqueda(value);
    applyFilters(selectedTipos, selectedEntidades, diasApertura, value);
  };

  const applyFilters = (tipos: string[], entidades: string[], dias: string, search: string = busqueda) => {
    const filters: any = {};
    
    if (tipos.length > 0) {
      filters.tipo_contratacion = tipos;
    }
    
    if (entidades.length > 0) {
      filters.entidad_compradora = entidades;
    }
    
    if (dias && !isNaN(parseInt(dias))) {
      filters.dias_apertura = parseInt(dias);
    }
    
    if (search) {
      filters.busqueda = search;
    }
    
    onFilterChange(filters);
  };

  const handleReset = () => {
    setSelectedTipos([]);
    setSelectedEntidades([]);
    setDiasApertura("");
    setBusqueda("");
    onFilterChange({});
  };

  if (loading || !filtros) {
    return (
      <Card className="card-shadow mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-10 bg-muted animate-pulse rounded"></div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="card-shadow mb-8">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-5 w-5" />
          Filtros
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Filtro de Entidades */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Entidad Compradora</label>
            <select
              multiple
              className="w-full min-h-[100px] p-2 border rounded-md text-sm"
              value={selectedEntidades}
              onChange={handleEntidadChange}
            >
              <option value="all" disabled className="font-semibold">-- Seleccionar --</option>
              {entidadesCompradoras.slice(0, 30).map((entidad, index) => (
                <option key={`entidad-${index}`} value={entidad.value}>
                  {entidad.value.length > 50 ? 
                    `${entidad.value.substring(0, 50)}...` : 
                    entidad.value} ({entidad.count})
                </option>
              ))}
            </select>
            {selectedEntidades.length > 0 && (
              <div className="text-xs text-muted-foreground">
                {selectedEntidades.length} seleccionada(s)
              </div>
            )}
            <div className="text-xs text-gray-500">
              Ctrl/Cmd + Click para selección múltiple
            </div>
          </div>

          {/* Filtro de Tipos de Contratación */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Tipo de Contratación</label>
            <select
              multiple
              className="w-full min-h-[100px] p-2 border rounded-md text-sm"
              value={selectedTipos}
              onChange={handleTipoChange}
            >
              <option value="all" disabled className="font-semibold">-- Seleccionar --</option>
              {tiposContratacion.slice(0, 20).map((tipo, index) => (
                <option key={`tipo-${index}`} value={tipo.value}>
                  {tipo.value} ({tipo.count})
                </option>
              ))}
            </select>
            {selectedTipos.length > 0 && (
              <div className="text-xs text-muted-foreground">
                {selectedTipos.length} seleccionado(s)
              </div>
            )}
            <div className="text-xs text-gray-500">
              Ctrl/Cmd + Click para selección múltiple
            </div>
          </div>

          {/* Filtro de Días para Apertura */}
          <div className="space-y-2">
            <label htmlFor="dias-apertura" className="text-sm font-medium">
              Días para Apertura
            </label>
            <Input
              id="dias-apertura"
              type="number"
              placeholder="Ej: 30"
              value={diasApertura}
              onChange={(e) => handleDiasAperturaChange(e.target.value)}
              min="1"
            />
            <div className="text-xs text-gray-500">
              Licitaciones que abren en los próximos X días
            </div>
          </div>

          {/* Búsqueda y Reset */}
          <div className="space-y-2">
            <label htmlFor="busqueda" className="text-sm font-medium">Buscar</label>
            <Input
              id="busqueda"
              placeholder="Buscar..."
              value={busqueda}
              onChange={(e) => handleBusquedaChange(e.target.value)}
            />
            <Button
              variant="outline"
              onClick={handleReset}
              className="w-full flex items-center gap-2 mt-2"
            >
              <RotateCcw className="h-4 w-4" />
              Reset
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default Filters;
