import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Filtros } from "@/lib/api";
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
    fuente: "",
    tipo_contratacion: "",
    entidad_compradora: "",
    estado: "",
    busqueda: "",
  });

  const handleFilterChange = (key: string, value: string) => {
    const newFilters = { ...selectedFilters, [key]: value };
    setSelectedFilters(newFilters);
    
    // Convert empty strings to undefined for API
    const apiFilters = Object.fromEntries(
      Object.entries(newFilters).map(([k, v]) => [k, v || undefined])
    );
    
    onFilterChange(apiFilters);
  };

  const handleReset = () => {
    const resetFilters = {
      fuente: "",
      tipo_contratacion: "",
      entidad_compradora: "",
      estado: "",
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
              <SelectItem value="">Todas las fuentes</SelectItem>
              {(filtros.fuentes || []).map((fuente) => (
                <SelectItem key={fuente} value={fuente}>
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
              <SelectItem value="">Todos los tipos</SelectItem>
              {(filtros.tipos_contratacion || []).slice(0, 20).map((tipo) => (
                <SelectItem key={tipo} value={tipo}>
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
              <SelectItem value="">Todas las entidades</SelectItem>
              {(filtros.entidades_compradoras || []).slice(0, 50).map((entidad) => (
                <SelectItem key={entidad} value={entidad}>
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
              <SelectItem value="">Todos los estados</SelectItem>
              {(filtros.estados || []).map((estado) => (
                <SelectItem key={estado} value={estado}>
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