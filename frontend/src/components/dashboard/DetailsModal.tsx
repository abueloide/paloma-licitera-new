import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, X } from "lucide-react";
import { Licitacion } from "@/lib/api";
import { formatMoney, formatDate, getBadgeColor, getEstadoBadgeColor } from "@/lib/formatters";

interface DetailsModalProps {
  licitacion: Licitacion | null;
  open: boolean;
  onClose: () => void;
}

const DetailsModal = ({ licitacion, open, onClose }: DetailsModalProps) => {
  if (!licitacion) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader className="flex flex-row items-center justify-between">
          <DialogTitle className="text-xl font-bold pr-8">
            Detalle de Licitación
          </DialogTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-6 w-6 rounded-full"
          >
            <X className="h-4 w-4" />
          </Button>
        </DialogHeader>

        <div className="space-y-6">
          {/* Header info */}
          <div className="flex flex-wrap gap-4 items-center">
            <Badge className={getBadgeColor(licitacion.fuente)}>
              {licitacion.fuente}
            </Badge>
            <Badge 
              variant="secondary" 
              className={getEstadoBadgeColor(licitacion.estado)}
            >
              {licitacion.estado}
            </Badge>
            <div className="text-sm text-muted-foreground">
              ID: {licitacion.id}
            </div>
          </div>

          {/* Main details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  Número de Licitación
                </label>
                <p className="font-mono text-sm mt-1">{licitacion.numero_licitacion}</p>
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  Título
                </label>
                <p className="mt-1">{licitacion.titulo}</p>
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  Entidad Compradora
                </label>
                <p className="mt-1">{licitacion.entidad_compradora}</p>
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  Tipo de Contratación
                </label>
                <p className="mt-1">{licitacion.tipo_contratacion}</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  Monto
                </label>
                <p className="text-2xl font-bold text-green-600 mt-1">
                  {formatMoney(licitacion.monto)}
                </p>
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  Fecha de Publicación
                </label>
                <p className="mt-1">{formatDate(licitacion.fecha_publicacion)}</p>
              </div>

              {licitacion.fecha_limite && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Fecha Límite
                  </label>
                  <p className="mt-1">{formatDate(licitacion.fecha_limite)}</p>
                </div>
              )}

              {licitacion.ubicacion && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Ubicación
                  </label>
                  <p className="mt-1">{licitacion.ubicacion}</p>
                </div>
              )}
            </div>
          </div>

          {/* Description */}
          {licitacion.descripcion && (
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                Descripción
              </label>
              <p className="mt-1 text-sm leading-relaxed">{licitacion.descripcion}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-4 pt-4 border-t">
            {licitacion.url_original && (
              <Button
                variant="outline"
                onClick={() => window.open(licitacion.url_original, '_blank')}
                className="flex items-center gap-2"
              >
                <ExternalLink className="h-4 w-4" />
                Ver Original
              </Button>
            )}
            <Button onClick={onClose}>
              Cerrar
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default DetailsModal;