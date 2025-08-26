import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ArrowLeft, ExternalLink, Download, Calendar, Building, FileText } from "lucide-react";
import { apiService } from '@/services/api';

const LicitacionDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [licitacion, setLicitacion] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchDetail = async () => {
      if (!id) return;
      
      setLoading(true);
      try {
        const data = await apiService.getLicitacionDetail(parseInt(id));
        setLicitacion(data);
      } catch (err: any) {
        setError(err.message || 'Error al cargar los detalles');
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [id]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'No especificada';
    try {
      return new Date(dateString).toLocaleDateString('es-MX', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch {
      return 'No especificada';
    }
  };

  const formatMoney = (amount: number | null) => {
    if (!amount || amount === 0) return 'No especificado';
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getDOFUrl = (licitacion: any) => {
    if (licitacion.fuente !== 'DOF' || !licitacion.url_original) return null;
    
    // Determinar si es matutino o vespertino basándose en metadata o fecha
    const fecha = licitacion.fecha_publicacion;
    if (!fecha) return licitacion.url_original;
    
    const date = new Date(fecha);
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    
    // Por defecto usar matutino, pero esto podría mejorar con metadata adicional
    const edicion = licitacion.metadata?.edicion || 'matutina';
    
    return `https://www.dof.gob.mx/nota_to_pdf.php?fecha=${day}/${month}/${year}&edicion=${edicion}`;
  };

  if (loading) {
    return (
      <div className="container mx-auto p-8">
        <Card>
          <CardContent className="p-8">
            <div className="animate-pulse space-y-4">
              <div className="h-8 bg-muted rounded w-3/4"></div>
              <div className="h-4 bg-muted rounded w-1/2"></div>
              <div className="space-y-2">
                <div className="h-4 bg-muted rounded"></div>
                <div className="h-4 bg-muted rounded"></div>
                <div className="h-4 bg-muted rounded w-3/4"></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !licitacion) {
    return (
      <div className="container mx-auto p-8">
        <Card>
          <CardContent className="p-8">
            <div className="text-center">
              <p className="text-red-600 mb-4">{error || 'No se encontró la licitación'}</p>
              <Button onClick={() => navigate('/')}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver al Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const dofUrl = getDOFUrl(licitacion);

  return (
    <div className="container mx-auto p-8 max-w-6xl">
      <div className="mb-6">
        <Button variant="outline" onClick={() => navigate('/')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver al Dashboard
        </Button>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="text-2xl mb-2">{licitacion.titulo || 'Sin título'}</CardTitle>
              <CardDescription className="text-lg">
                {licitacion.numero_procedimiento || 'Sin número de procedimiento'}
              </CardDescription>
            </div>
            <Badge className="text-lg px-3 py-1">{licitacion.fuente}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {licitacion.descripcion && (
            <div className="mb-6">
              <h3 className="font-semibold mb-2">Descripción</h3>
              <p className="text-muted-foreground whitespace-pre-wrap">{licitacion.descripcion}</p>
            </div>
          )}

          <Separator className="my-6" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  <Building className="h-4 w-4" />
                  Información de la Entidad
                </h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Entidad Compradora:</span>
                    <p className="font-medium">{licitacion.entidad_compradora || 'No especificada'}</p>
                  </div>
                  {licitacion.unidad_compradora && (
                    <div>
                      <span className="text-muted-foreground">Unidad Compradora:</span>
                      <p className="font-medium">{licitacion.unidad_compradora}</p>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Tipo de Contratación
                </h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Tipo de Procedimiento:</span>
                    <p className="font-medium">{licitacion.tipo_procedimiento || 'No especificado'}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Tipo de Contratación:</span>
                    <p className="font-medium">{licitacion.tipo_contratacion || 'No especificado'}</p>
                  </div>
                  {licitacion.estado && (
                    <div>
                      <span className="text-muted-foreground">Estado:</span>
                      <p className="font-medium">{licitacion.estado}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Fechas Importantes
                </h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Fecha de Publicación:</span>
                    <p className="font-medium">{formatDate(licitacion.fecha_publicacion)}</p>
                  </div>
                  {licitacion.fecha_apertura && (
                    <div>
                      <span className="text-muted-foreground">Fecha de Apertura:</span>
                      <p className="font-medium">{formatDate(licitacion.fecha_apertura)}</p>
                    </div>
                  )}
                  {licitacion.fecha_fallo && (
                    <div>
                      <span className="text-muted-foreground">Fecha de Fallo:</span>
                      <p className="font-medium">{formatDate(licitacion.fecha_fallo)}</p>
                    </div>
                  )}
                </div>
              </div>

              {(licitacion.monto_estimado > 0 || licitacion.moneda) && (
                <div>
                  <h3 className="font-semibold mb-2">Información Económica</h3>
                  <div className="space-y-2 text-sm">
                    {licitacion.monto_estimado > 0 && (
                      <div>
                        <span className="text-muted-foreground">Monto Estimado:</span>
                        <p className="font-medium text-lg">{formatMoney(licitacion.monto_estimado)}</p>
                      </div>
                    )}
                    {licitacion.moneda && (
                      <div>
                        <span className="text-muted-foreground">Moneda:</span>
                        <p className="font-medium">{licitacion.moneda}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          <Separator className="my-6" />

          <div className="flex gap-4">
            {licitacion.url_original && (
              <Button variant="default" asChild>
                <a href={licitacion.url_original} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Ver en Sitio Original
                </a>
              </Button>
            )}
            
            {dofUrl && (
              <Button variant="outline" asChild>
                <a href={dofUrl} target="_blank" rel="noopener noreferrer">
                  <Download className="mr-2 h-4 w-4" />
                  Descargar PDF del DOF
                </a>
              </Button>
            )}
          </div>

          {licitacion.metadata && Object.keys(licitacion.metadata).length > 0 && (
            <>
              <Separator className="my-6" />
              <div>
                <h3 className="font-semibold mb-2">Información Adicional</h3>
                <div className="bg-muted p-4 rounded-lg">
                  <pre className="text-xs overflow-x-auto">
                    {JSON.stringify(licitacion.metadata, null, 2)}
                  </pre>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default LicitacionDetail;
