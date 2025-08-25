import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ChevronLeft, ChevronRight, Eye } from "lucide-react";
import { Licitacion, LicitacionesResponse } from "@/lib/api";
import { formatMoney, formatDate, getBadgeColor, getEstadoBadgeColor } from "@/lib/formatters";

interface DataTableProps {
  data: LicitacionesResponse | null;
  loading: boolean;
  onPageChange: (page: number) => void;
  onViewDetails: (licitacion: Licitacion) => void;
}

const DataTable = ({ data, loading, onPageChange, onViewDetails }: DataTableProps) => {
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

  if (!data || data.licitaciones.length === 0) {
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

  const { licitaciones, total, page, total_pages } = data;

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
                <TableHead>Número</TableHead>
                <TableHead>Título</TableHead>
                <TableHead>Entidad</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Monto</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead>Fuente</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {licitaciones.map((licitacion) => (
                <TableRow key={licitacion.id}>
                  <TableCell className="font-mono text-sm">
                    {licitacion.numero_licitacion}
                  </TableCell>
                  <TableCell className="max-w-xs">
                    <div className="truncate" title={licitacion.titulo}>
                      {licitacion.titulo}
                    </div>
                  </TableCell>
                  <TableCell className="max-w-xs">
                    <div className="truncate" title={licitacion.entidad_compradora}>
                      {licitacion.entidad_compradora}
                    </div>
                  </TableCell>
                  <TableCell className="max-w-xs">
                    <div className="truncate" title={licitacion.tipo_contratacion}>
                      {licitacion.tipo_contratacion}
                    </div>
                  </TableCell>
                  <TableCell className="money-text">
                    {formatMoney(licitacion.monto)}
                  </TableCell>
                  <TableCell>
                    {formatDate(licitacion.fecha_publicacion)}
                  </TableCell>
                  <TableCell>
                    <Badge className={getBadgeColor(licitacion.fuente)}>
                      {licitacion.fuente}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge 
                      variant="secondary" 
                      className={getEstadoBadgeColor(licitacion.estado)}
                    >
                      {licitacion.estado}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onViewDetails(licitacion)}
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
            Mostrando {(page - 1) * 50 + 1} - {Math.min(page * 50, total)} de {total.toLocaleString()} registros
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