import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { AnalisisPorTipo } from "@/lib/api";

interface ChartsProps {
  tiposData: AnalisisPorTipo[];
  temporalData?: Array<{ mes: string; cantidad: number; acumulado: number }>;
  loading: boolean;
}

const Charts = ({ tiposData, temporalData, loading }: ChartsProps) => {
  // Colores para el gráfico de pie de tipos de contratación
  const COLORS = [
    '#3b82f6', // blue-500
    '#a855f7', // purple-500
    '#059669', // green-600
    '#f59e0b', // amber-500
    '#ef4444', // red-500
    '#10b981', // emerald-500
    '#6366f1', // indigo-500
    '#ec4899', // pink-500
    '#14b8a6', // teal-500
    '#f97316', // orange-500
  ];

  // Preparar datos para el gráfico de pie (distribución por tipo de contratación)
  const pieData = tiposData.slice(0, 10).map((tipo, index) => ({
    name: tipo.tipo_contratacion || 'Sin tipo',
    value: tipo.cantidad || tipo.total || 0,
    color: COLORS[index % COLORS.length]
  }));

  // Formatear datos temporales para mostrar mes corto
  const formatMonth = (mes: string) => {
    const [year, month] = mes.split('-');
    const monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                       'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    return monthNames[parseInt(month) - 1] + ' ' + year.substring(2);
  };

  const lineData = temporalData?.map(item => ({
    mes: formatMonth(item.mes),
    cantidad: item.cantidad,
    acumulado: item.acumulado
  })) || [];

  if (loading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card className="card-shadow">
          <CardHeader>
            <CardTitle>Distribución por Tipo de Contratación</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 bg-muted animate-pulse rounded"></div>
          </CardContent>
        </Card>
        <Card className="card-shadow">
          <CardHeader>
            <CardTitle>Licitaciones Acumuladas del Año</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 bg-muted animate-pulse rounded"></div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      {/* Distribución por Tipo de Contratación */}
      <Card className="card-shadow">
        <CardHeader>
          <CardTitle>Distribución por Tipo de Contratación</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => {
                  const shortName = name.length > 20 ? `${name.substring(0, 20)}...` : name;
                  return `${shortName} ${(percent * 100).toFixed(0)}%`;
                }}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                formatter={(value: any) => [value.toLocaleString(), 'Licitaciones']}
                contentStyle={{ fontSize: '12px' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Licitaciones Acumuladas del Año */}
      <Card className="card-shadow">
        <CardHeader>
          <CardTitle>Licitaciones Acumuladas del Año (Por Fecha de Publicación)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={lineData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="mes"
                fontSize={12}
              />
              <YAxis fontSize={12} />
              <Tooltip 
                formatter={(value: any, name: string) => [
                  value.toLocaleString(),
                  name === 'cantidad' ? 'Nuevas' : 'Total Acumulado'
                ]}
                labelFormatter={(label) => `Mes: ${label}`}
                contentStyle={{ fontSize: '12px' }}
              />
              <Line 
                type="monotone" 
                dataKey="cantidad" 
                stroke="#a855f7" 
                name="cantidad"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
              <Line 
                type="monotone" 
                dataKey="acumulado" 
                stroke="#3b82f6" 
                name="acumulado"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
};

export default Charts;
