import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Filtros } from "@/types";
import { Search, RotateCcw } from "lucide-react";

interface FiltersProps {
  filtros: Filtros | null;
  onFilterChange: (filters: {
    fuente?: string;
    tipo_contratacion?: string;
    entidad_compradora?: string;
    estado?: string;
    busqueda?: string;
  }) => void;
  loading: boolean;
}

const Filters = ({ filtros, onFilterChange, loading }: FiltersProps) => {
  const [selectedFilters, setSelectedFilters] = useState({
    fuente: "all",
    tipo_contratacion: "all",
    entidad_compradora: "all",
    estado: "all",
    busqueda: "",
  });

  const handleFilterChange = (key: string, value: string) => {
    const newFilters = { ...selectedFilters, [key]: value };
    setSelectedFilters(newFilters);
    
    // Convert "all" to undefined for API
    const apiFilters = Object.fromEntries(
      Object.entries(newFilters).map(([k, v]) => [
        k, 
        v === "all" || v === "" ? undefined : v
      ])
    );
    
    onFilterChange(apiFilters);
  };

  const handleReset = () => {
    const resetFilters = {
      fuente: "all",
      tipo_contratacion: "all",
      entidad_compradora: "all",
      estado: "all",
      busqueda: "",
    };
    setSelectedFilters(resetFilters);
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
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-10 bg-muted animate-pulse rounded"></div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Helper function to extract values from different data formats
  const extractOptions = (data: any, fieldName: string): string[] => {
    if (!data) return [];
    
    if (Array.isArray(data)) {
      // If it's already an array of strings
      if (typeof data[0] === 'string') {
        return data.filter(item => item && item !== '');
      }
      // If it's an array of objects, extract the key names
      if (typeof data[0] === 'object' && data[0] !== null) {
        return data
          .map((item: any) => {
            // Look for the field that matches the fieldName
            if (item[fieldName]) return item[fieldName];
            // Fallback to the first string field
            const firstStringValue = Object.values(item).find(v => typeof v === 'string' && v !== '');
            return firstStringValue;
          })
          .filter((item: any) => item && item !== '');
      }
    }
    
    return [];
  };

  const fuentes = extractOptions(filtros.fuentes, 'fuente');
  const tiposContratacion = extractOptions(filtros.tipos_contratacion, 'tipo_contratacion');
  const entidadesCompradoras = extractOptions(filtros.top_entidades, 'entidad_compradora');
  const estados = extractOptions(filtros.estados, 'estado');

  return (
    <Card className="card-shadow mb-8">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-5 w-5" />
          Filtros
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <Select
            value={selectedFilters.fuente}
            onValueChange={(value) => handleFilterChange("fuente", value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Fuente" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las fuentes</SelectItem>
              {fuentes.map((fuente, index) => (
                <SelectItem key={`fuente-${index}-${fuente}`} value={fuente}>
                  {fuente}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={selectedFilters.tipo_contratacion}
            onValueChange={(value) => handleFilterChange("tipo_contratacion", value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Tipo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los tipos</SelectItem>
              {tiposContratacion.slice(0, 20).map((tipo, index) => (
                <SelectItem key={`tipo-${index}-${tipo}`} value={tipo}>
                  {tipo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={selectedFilters.entidad_compradora}
            onValueChange={(value) => handleFilterChange("entidad_compradora", value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Entidad" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las entidades</SelectItem>
              {entidadesCompradoras.slice(0, 50).map((entidad, index) => (
                <SelectItem key={`entidad-${index}-${entidad}`} value={entidad}>
                  {entidad.length > 30 ? `${entidad.substring(0, 30)}...` : entidad}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={selectedFilters.estado}
            onValueChange={(value) => handleFilterChange("estado", value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Estado" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los estados</SelectItem>
              {estados.map((estado, index) => (
                <SelectItem key={`estado-${index}-${estado}`} value={estado}>
                  {estado}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Input
            placeholder="Buscar..."
            value={selectedFilters.busqueda}
            onChange={(e) => handleFilterChange("busqueda", e.target.value)}
            className="md:col-span-1"
          />

          <Button
            variant="outline"
            onClick={handleReset}
            className="flex items-center gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            Reset
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default Filters;
