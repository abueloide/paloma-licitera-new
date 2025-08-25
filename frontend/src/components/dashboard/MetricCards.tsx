import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMoney, formatNumber } from "@/lib/formatters";
import { Stats } from "@/lib/api";
import { FileText, DollarSign, Database, TrendingUp } from "lucide-react";

interface MetricCardsProps {
  stats: Stats | null;
  loading: boolean;
}

const MetricCards = ({ stats, loading }: MetricCardsProps) => {
  const metrics = [
    {
      title: "Total Licitaciones",
      value: stats ? formatNumber(stats.total_licitaciones) : "0",
      icon: FileText,
      color: "text-blue-600",
    },
    {
      title: "Monto Total",
      value: stats ? formatMoney(stats.monto_total) : "$0",
      icon: DollarSign,
      color: "text-green-600",
    },
    {
      title: "Fuentes Activas",
      value: stats ? stats.fuentes_activas.toString() : "0",
      icon: Database,
      color: "text-purple-600",
    },
    {
      title: "Monto Promedio",
      value: stats ? formatMoney(stats.monto_promedio) : "$0",
      icon: TrendingUp,
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
            <div className="text-2xl font-bold">
              {loading ? (
                <div className="h-8 bg-muted animate-pulse rounded"></div>
              ) : (
                metric.value
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default MetricCards;