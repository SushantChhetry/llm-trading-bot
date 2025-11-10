import { memo, useState, useMemo } from 'react';
import { 
  LineChart, 
  Line, 
  AreaChart,
  Area,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  ReferenceLine
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { formatCurrency, formatPercentage, getProfitColor } from '@/lib/utils';
import { usePnLData, usePortfolioSnapshots } from '@/contexts/TradingDataContext';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface PnLChartProps {
  className?: string;
}

type ChartView = 'value' | 'returns';

interface ChartDataPoint {
  timestamp: string;
  total_value: number;
  balance: number;
  positions_value: number;
  total_return: number;
  total_return_pct: number;
  unrealized_pnl: number;
  realized_pnl: number;
  total_fees: number;
  active_positions: number;
  trade_count: number;
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: ChartDataPoint;
  }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload || !payload.length || !label) return null;

  const data = payload[0].payload;
  const timestamp = new Date(label).toLocaleString('en-US', {
    timeZone: 'America/New_York',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="bg-card border rounded-lg p-3 shadow-lg min-w-[180px]">
      <p className="text-sm font-medium mb-2">{timestamp}</p>
      <div className="space-y-1">
        <p className="text-sm">
          <span className="text-muted-foreground">Value: </span>
          <span className="font-medium">{formatCurrency(data.total_value)}</span>
        </p>
        <p className="text-sm">
          <span className="text-muted-foreground">Return: </span>
          <span className={`font-medium ${getProfitColor(data.total_return_pct ?? 0)}`}>
            {formatCurrency(data.total_return)} ({formatPercentage(data.total_return_pct ?? 0)})
          </span>
        </p>
        {data.active_positions > 0 && (
          <p className="text-sm">
            <span className="text-muted-foreground">Positions: </span>
            <span className="font-medium">{data.active_positions}</span>
          </p>
        )}
      </div>
    </div>
  );
}

function PnLChartComponent({ className }: PnLChartProps) {
  const { pnlData: data } = usePnLData();
  const { snapshots } = usePortfolioSnapshots();
  const [view, setView] = useState<ChartView>('value');

  const chartData = useMemo<ChartDataPoint[]>(() => {
    if (snapshots && snapshots.length > 0) {
      return snapshots.map(snapshot => ({
        timestamp: snapshot.timestamp,
        total_value: snapshot.total_value ?? 0,
        balance: snapshot.balance ?? 0,
        positions_value: snapshot.positions_value ?? 0,
        total_return: snapshot.total_return ?? 0,
        total_return_pct: snapshot.total_return_pct ?? 0,
        unrealized_pnl: snapshot.unrealized_pnl ?? 0,
        realized_pnl: snapshot.realized_pnl ?? 0,
        total_fees: snapshot.total_fees ?? 0,
        active_positions: snapshot.active_positions ?? 0,
        trade_count: snapshot.total_trades ?? 0,
      }));
    }
    
    // Fallback to pnlData
    return (data || []).map(point => ({
      timestamp: point.timestamp,
      total_value: point.total_value ?? 0,
      balance: point.total_value ?? 0,
      positions_value: 0,
      total_return: point.total_return ?? 0,
      total_return_pct: point.total_return_pct ?? 0,
      unrealized_pnl: 0,
      realized_pnl: point.total_return ?? 0,
      total_fees: 0,
      active_positions: 0,
      trade_count: point.trade_count ?? 0,
    }));
  }, [snapshots, data]);

  const latestData = chartData[chartData.length - 1];
  const totalReturnPct = latestData?.total_return_pct ?? 0;
  const isPositive = totalReturnPct >= 0;
  const TrendIcon = isPositive ? TrendingUp : TrendingDown;

  // Profit target percentage for cash out
  const PROFIT_TARGET_PCT = 10.0;

  const chartConfig = {
    margin: { top: 5, right: 20, left: 20, bottom: 5 },
    data: chartData,
  };

  const renderChart = () => {
    if (view === 'value') {
      return (
        <AreaChart {...chartConfig}>
          <defs>
            <linearGradient id="valueGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={isPositive ? "#10b981" : "#ef4444"} stopOpacity={0.2}/>
              <stop offset="95%" stopColor={isPositive ? "#10b981" : "#ef4444"} stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(value) => new Date(value).toLocaleTimeString('en-US', {
              timeZone: 'America/New_York',
              hour: '2-digit',
              minute: '2-digit',
            })}
            className="text-xs text-muted-foreground"
          />
          <YAxis
            tickFormatter={(value) => formatCurrency(value)}
            className="text-xs text-muted-foreground"
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine 
            y={latestData?.balance ?? 0} 
            stroke="hsl(var(--muted-foreground))" 
            strokeDasharray="2 2" 
            strokeOpacity={0.5}
          />
          <Area
            type="monotone"
            dataKey="total_value"
            stroke={isPositive ? "#10b981" : "#ef4444"}
            strokeWidth={2}
            fill="url(#valueGradient)"
            dot={false}
            activeDot={{ r: 4 }}
          />
        </AreaChart>
      );
    }

    return (
      <LineChart {...chartConfig}>
        <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={(value) => new Date(value).toLocaleTimeString('en-US', {
            timeZone: 'America/New_York',
            hour: '2-digit',
            minute: '2-digit',
          })}
          className="text-xs text-muted-foreground"
        />
        <YAxis
          tickFormatter={(value) => `${value.toFixed(2)}%`}
          className="text-xs text-muted-foreground"
        />
        <Tooltip content={<CustomTooltip />} />
        {/* Zero line */}
        <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="2 2" strokeOpacity={0.5} />
        {/* 10% Profit Target Line */}
        <ReferenceLine 
          y={PROFIT_TARGET_PCT} 
          stroke="#10b981" 
          strokeDasharray="4 4" 
          strokeWidth={2}
          strokeOpacity={0.7}
          label={{ 
            value: `${PROFIT_TARGET_PCT}% Target`, 
            position: "right",
            fill: "#10b981",
            fontSize: 12,
            fontWeight: 500
          }}
        />
        <Line
          type="monotone"
          dataKey="total_return_pct"
          stroke={isPositive ? "#10b981" : "#ef4444"}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    );
  };

  if (chartData.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendIcon className="h-5 w-5" />
            Portfolio Performance
          </CardTitle>
          <CardDescription>
            Real-time portfolio tracking over time
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-80 text-muted-foreground">
            No data available
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendIcon className={`h-5 w-5 ${getProfitColor(totalReturnPct)}`} />
            <CardTitle>Portfolio Performance</CardTitle>
            <span className={`text-sm font-normal ${getProfitColor(totalReturnPct)}`}>
              {formatPercentage(totalReturnPct)}
            </span>
          </div>
          <div className="flex gap-1 rounded-md border p-1">
            <button
              onClick={() => setView('value')}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                view === 'value'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Value
            </button>
            <button
              onClick={() => setView('returns')}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                view === 'returns'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Returns
            </button>
          </div>
        </div>
        <CardDescription>
          {view === 'value' ? 'Total portfolio value over time' : 'Percentage returns over time'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            {renderChart()}
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

export const PnLChart = memo(PnLChartComponent, (prevProps, nextProps) => {
  return prevProps.className === nextProps.className;
});
