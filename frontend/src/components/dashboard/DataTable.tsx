import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ChevronLeft, ChevronRight, Eye, ExternalLink } from "lucide-react";
import { LicitacionesResponse } from "@/types";

interface DataTableProps {
  data: LicitacionesResponse | null;
  loading: boolean;
  onPageChange: (page: number) => void;
}

const DataTable = ({ data, loading, onPageChange }: DataTableProps) => {
  const navigate = useNavigate();

  const handleViewDetails = (licitacionId: number) => {
    navigate(`/licitacion/${licitacionId}`);
  };

  if (loading) {
    return (
      <Card className="card-shadow">
        <CardHeader>
          <CardTitle>Licitaciones</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 bg-muted animate-pulse rounded"></div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || !data.data || data.data.length === 0) {
    return (
      <Card className="card-shadow">
        <CardHeader>
          <CardTitle>Licitaciones</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            No se encontraron licitaciones con los filtros seleccionados.
          </div>
        </CardContent>
      </Card>
    );
  }

  const { data: licitaciones, pagination } = data;
  const { total = 0, page = 1, total_pages = 1 } = pagination || {};

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('es-MX', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
    } catch {
      return 'N/A';
    }
  };

  const getFuenteColor = (fuente: string) => {
    switch(fuente) {
      case 'TIANGUIS': return 'bg-blue-100 text-blue-800';
      case 'COMPRASMX': return 'bg-purple-100 text-purple-800';
      case 'DOF': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Card className="card-shadow">
      <CardHeader>
        <CardTitle>
          Licitaciones ({total.toLocaleString()} registros)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[150px]">Número Procedimiento</TableHead>
                <TableHead className="min-w-[300px]">Título</TableHead>
                <TableHead className="min-w-[200px]">Entidad Compradora</TableHead>
                <TableHead className="min-w-[150px]">Tipo Procedimiento</TableHead>
                <TableHead className="min-w-[150px]">Tipo Contratación</TableHead>
                <TableHead>Fecha Publicación</TableHead>
                <TableHead>Fecha Apertura</TableHead>
                <TableHead>Fuente</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {licitaciones.map((licitacion) => (
                <TableRow key={licitacion.id} className="hover:bg-muted/50 cursor-pointer">
                  <TableCell className="font-mono text-sm">
                    {licitacion.numero_procedimiento || 'N/A'}
                  </TableCell>
                  <TableCell>
                    <div className="max-w-xs truncate" title={licitacion.titulo || ''}>
                      {licitacion.titulo || 'Sin título'}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="max-w-xs truncate" title={licitacion.entidad_compradora || ''}>
                      {licitacion.entidad_compradora || 'Sin especificar'}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      {licitacion.tipo_procedimiento || 'N/A'}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      {licitacion.tipo_contratacion || 'N/A'}
                    </div>
                  </TableCell>
                  <TableCell>
                    {formatDate(licitacion.fecha_publicacion)}
                  </TableCell>
                  <TableCell>
                    {formatDate(licitacion.fecha_apertura)}
                  </TableCell>
                  <TableCell>
                    <Badge className={getFuenteColor(licitacion.fuente || '')}>
                      {licitacion.fuente || 'N/A'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleViewDetails(licitacion.id);
                      }}
                      className="flex items-center gap-1"
                    >
                      <Eye className="h-3 w-3" />
                      Ver
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between mt-6">
          <div className="text-sm text-muted-foreground">
            Mostrando {Math.max((page - 1) * 50 + 1, 1)} - {Math.min(page * 50, total)} de {total.toLocaleString()} registros
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
              Anterior
            </Button>
            <span className="text-sm">
              Página {page} de {total_pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page + 1)}
              disabled={page >= total_pages}
            >
              Siguiente
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default DataTable;