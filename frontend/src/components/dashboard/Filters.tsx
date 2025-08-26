import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Filtros } from "@/types";
import { Search, RotateCcw, ChevronDown, ChevronUp } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

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
  const [showTipos, setShowTipos] = useState(false);
  const [showEntidades, setShowEntidades] = useState(false);

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

  const handleTipoToggle = (tipo: string) => {
    const newTipos = selectedTipos.includes(tipo)
      ? selectedTipos.filter(t => t !== tipo)
      : [...selectedTipos, tipo];
    setSelectedTipos(newTipos);
    applyFilters(newTipos, selectedEntidades, diasApertura);
  };

  const handleEntidadToggle = (entidad: string) => {
    const newEntidades = selectedEntidades.includes(entidad)
      ? selectedEntidades.filter(e => e !== entidad)
      : [...selectedEntidades, entidad];
    setSelectedEntidades(newEntidades);
    applyFilters(selectedTipos, newEntidades, diasApertura);
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
            <div className="flex items-center justify-between">
              <Label>Entidad Compradora</Label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowEntidades(!showEntidades)}
              >
                {showEntidades ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
            {showEntidades && (
              <ScrollArea className="h-48 w-full rounded-md border p-4">
                <div className="space-y-2">
                  {entidadesCompradoras.slice(0, 30).map((entidad, index) => (
                    <div key={`entidad-${index}`} className="flex items-center space-x-2">
                      <Checkbox
                        id={`entidad-${index}`}
                        checked={selectedEntidades.includes(entidad.value)}
                        onCheckedChange={() => handleEntidadToggle(entidad.value)}
                      />
                      <Label
                        htmlFor={`entidad-${index}`}
                        className="text-sm font-normal cursor-pointer"
                      >
                        {entidad.value.length > 40 ? 
                          `${entidad.value.substring(0, 40)}...` : 
                          entidad.value} ({entidad.count})
                      </Label>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
            {selectedEntidades.length > 0 && (
              <div className="text-xs text-muted-foreground">
                {selectedEntidades.length} seleccionadas
              </div>
            )}
          </div>

          {/* Filtro de Tipos de Contratación */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Tipo de Contratación</Label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowTipos(!showTipos)}
              >
                {showTipos ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
            {showTipos && (
              <ScrollArea className="h-48 w-full rounded-md border p-4">
                <div className="space-y-2">
                  {tiposContratacion.slice(0, 20).map((tipo, index) => (
                    <div key={`tipo-${index}`} className="flex items-center space-x-2">
                      <Checkbox
                        id={`tipo-${index}`}
                        checked={selectedTipos.includes(tipo.value)}
                        onCheckedChange={() => handleTipoToggle(tipo.value)}
                      />
                      <Label
                        htmlFor={`tipo-${index}`}
                        className="text-sm font-normal cursor-pointer"
                      >
                        {tipo.value} ({tipo.count})
                      </Label>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
            {selectedTipos.length > 0 && (
              <div className="text-xs text-muted-foreground">
                {selectedTipos.length} seleccionados
              </div>
            )}
          </div>

          {/* Filtro de Días para Apertura */}
          <div className="space-y-2">
            <Label htmlFor="dias-apertura">Días para Apertura</Label>
            <Input
              id="dias-apertura"
              type="number"
              placeholder="Ej: 30"
              value={diasApertura}
              onChange={(e) => handleDiasAperturaChange(e.target.value)}
              min="1"
            />
            <div className="text-xs text-muted-foreground">
              Licitaciones que abren en los próximos X días
            </div>
          </div>

          {/* Búsqueda y Reset */}
          <div className="space-y-2">
            <Label htmlFor="busqueda">Buscar</Label>
            <Input
              id="busqueda"
              placeholder="Buscar..."
              value={busqueda}
              onChange={(e) => handleBusquedaChange(e.target.value)}
            />
            <Button
              variant="outline"
              onClick={handleReset}
              className="w-full flex items-center gap-2"
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
