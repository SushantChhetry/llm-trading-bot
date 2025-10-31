import { memo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { formatCurrency, formatPercentage, getProfitColor } from '@/lib/utils';
import { PnLDataPoint } from '@/types/trading';

interface PnLChartProps {
  data: PnLDataPoint[];
  className?: string;
}

export const PnLChart = memo(function PnLChart({ data, className }: PnLChartProps) {
  const latestData = data?.[data.length - 1];
  const totalReturnPct = latestData?.total_return_pct ?? 0;
  const isPositive = totalReturnPct >= 0;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span>Portfolio Performance</span>
          <span className={`text-sm font-normal ${getProfitColor(totalReturnPct)}`}>
            {formatPercentage(totalReturnPct)}
          </span>
        </CardTitle>
        <CardDescription>
          Real-time P&L tracking over time
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis 
                dataKey="timestamp" 
                tickFormatter={(value) => new Date(value).toLocaleTimeString('en-US', {
                  timeZone: 'America/New_York', // EST/EDT
                  hour: '2-digit',
                  minute: '2-digit',
                })}
                className="text-xs"
              />
              <YAxis 
                tickFormatter={(value) => formatCurrency(value)}
                className="text-xs"
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload as PnLDataPoint;
                    const totalValue = data?.total_value ?? 0;
                    const totalReturn = data?.total_return ?? 0;
                    const totalReturnPct = data?.total_return_pct ?? 0;
                    const tradeCount = data?.trade_count ?? 0;
                    return (
                      <div className="bg-card border rounded-lg p-3 shadow-lg">
                        <p className="text-sm font-medium">
                          {new Date(label).toLocaleString('en-US', {
                            timeZone: 'America/New_York', // EST/EDT
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          })}
                        </p>
                        <p className="text-sm">
                          <span className="text-muted-foreground">Value: </span>
                          <span className="font-medium">{formatCurrency(totalValue)}</span>
                        </p>
                        <p className="text-sm">
                          <span className="text-muted-foreground">Return: </span>
                          <span className={`font-medium ${getProfitColor(totalReturnPct)}`}>
                            {formatCurrency(totalReturn)} ({formatPercentage(totalReturnPct)})
                          </span>
                        </p>
                        <p className="text-sm">
                          <span className="text-muted-foreground">Trades: </span>
                          <span className="font-medium">{tradeCount}</span>
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine y={0} stroke="#666" strokeDasharray="2 2" />
              <Line
                type="monotone"
                dataKey="total_value"
                stroke={isPositive ? "#10b981" : "#ef4444"}
                strokeWidth={2}
                dot={{ fill: isPositive ? "#10b981" : "#ef4444", strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, stroke: isPositive ? "#10b981" : "#ef4444", strokeWidth: 2 }}
                isAnimationActive={true}
                animationDuration={300}
                animationEasing="ease-in-out"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
});
