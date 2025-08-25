import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { AnalisisPorTipo } from "@/lib/api";
import { formatMoney } from "@/lib/formatters";

interface ChartsProps {
  fuentesData: Array<{ name: string; value: number; color: string }>;
  tiposData: AnalisisPorTipo[];
  loading: boolean;
}

const Charts = ({ fuentesData, tiposData, loading }: ChartsProps) => {
  const COLORS = {
    TIANGUIS: '#3b82f6',    // blue-500
    COMPRASMX: '#a855f7',   // purple-500
    DOF: '#059669',         // green-600
  };

  const top10Tipos = tiposData.slice(0, 10);

  if (loading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card className="card-shadow">
          <CardHeader>
            <CardTitle>Distribución por Fuente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 bg-muted animate-pulse rounded"></div>
          </CardContent>
        </Card>
        <Card className="card-shadow">
          <CardHeader>
            <CardTitle>Top 10 Tipos de Contratación</CardTitle>
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
      <Card className="card-shadow">
        <CardHeader>
          <CardTitle>Distribución por Fuente</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={fuentesData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {fuentesData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value: any) => [value.toLocaleString(), 'Licitaciones']} />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="card-shadow">
        <CardHeader>
          <CardTitle>Top 10 Tipos de Contratación</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={top10Tipos} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="tipo_contratacion" 
                angle={-45}
                textAnchor="end"
                height={100}
                fontSize={12}
                tickFormatter={(value) => value.length > 15 ? `${value.substring(0, 15)}...` : value}
              />
              <YAxis />
              <Tooltip 
                formatter={(value: any, name: string) => [
                  name === 'total' ? value.toLocaleString() : formatMoney(Number(value)),
                  name === 'total' ? 'Licitaciones' : 'Monto Total'
                ]}
                labelFormatter={(label) => `Tipo: ${label}`}
              />
              <Bar dataKey="total" fill="#a855f7" name="total" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
};

export default Charts;