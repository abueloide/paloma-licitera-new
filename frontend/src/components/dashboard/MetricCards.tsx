import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/formatters";
import { Stats } from "@/lib/api";
import { FileText, Building2, Database, Package } from "lucide-react";

interface MetricCardsProps {
  stats: Stats | null;
  loading: boolean;
}

const MetricCards = ({ stats, loading }: MetricCardsProps) => {
  const metrics = [
    {
      title: "Total Licitaciones",
      value: stats ? formatNumber(stats.total_licitaciones || stats.total || 0) : "0",
      icon: FileText,
      color: "text-blue-600",
    },
    {
      title: "Entidad con más licitaciones",
      value: stats?.top_entidad ? 
        `${stats.top_entidad.entidad_compradora} (${formatNumber(stats.top_entidad.cantidad)})` : 
        "Cargando...",
      icon: Building2,
      color: "text-green-600",
    },
    {
      title: "Fuentes Activas",
      value: stats ? (stats.fuentes_activas?.toString() || "3") : "0",
      icon: Database,
      color: "text-purple-600",
    },
    {
      title: "Tipo más frecuente",
      value: stats?.top_tipo_contratacion ? 
        `${stats.top_tipo_contratacion.tipo_contratacion} (${formatNumber(stats.top_tipo_contratacion.cantidad)})` : 
        "Cargando...",
      icon: Package,
      color: "text-orange-600",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {metrics.map((metric, index) => (
        <Card key={index} className="card-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {metric.title}
            </CardTitle>
            <metric.icon className={`h-5 w-5 ${metric.color}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-${index === 1 || index === 3 ? 'lg' : '2xl'} font-bold`}>
              {loading ? (
                <div className="h-8 bg-muted animate-pulse rounded"></div>
              ) : (
                <div className={index === 1 || index === 3 ? "text-sm" : ""}>
                  {metric.value}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default MetricCards;
