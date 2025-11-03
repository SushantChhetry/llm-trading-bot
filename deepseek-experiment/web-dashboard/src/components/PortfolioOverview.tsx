import { memo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { formatCurrency, formatPercentage, getProfitColor } from '@/lib/utils';
import { usePortfolioOverview } from '@/contexts/TradingDataContext';
import { TrendingUp, TrendingDown, DollarSign, Activity, Target, Zap } from 'lucide-react';

interface PortfolioOverviewProps {
  className?: string;
}

function PortfolioOverviewComponent({ className }: PortfolioOverviewProps) {
  const { portfolio, botStatus } = usePortfolioOverview();
  // Safely extract values with defaults to prevent NaN
  const totalValue = portfolio?.total_value ?? 0;
  const balance = portfolio?.balance ?? 0;
  const totalReturn = portfolio?.total_return ?? 0;
  const totalReturnPct = portfolio?.total_return_pct ?? 0;
  const openPositions = portfolio?.open_positions ?? 0;
  const positionsValue = portfolio?.positions_value ?? 0;
  const totalTrades = portfolio?.total_trades ?? 0;

  const isPositive = totalReturnPct >= 0;
  const TrendIcon = isPositive ? TrendingUp : TrendingDown;

  // Default bot status values
  const tradingMode = botStatus?.trading_mode ?? 'paper';
  const llmProvider = botStatus?.llm_provider ?? 'unknown';
  const exchange = botStatus?.exchange ?? 'unknown';
  const runInterval = botStatus?.run_interval_seconds ?? 0;
  const lastUpdate = botStatus?.last_update ?? new Date().toISOString();

  return (
    <div className={`grid gap-4 md:grid-cols-2 lg:grid-cols-4 ${className}`}>
      {/* Total Portfolio Value */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Value</CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatCurrency(totalValue)}</div>
          <p className="text-xs text-muted-foreground">
            Balance: {formatCurrency(balance)}
          </p>
        </CardContent>
      </Card>

      {/* Total Return */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Return</CardTitle>
          <TrendIcon className={`h-4 w-4 ${getProfitColor(totalReturnPct)}`} />
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${getProfitColor(totalReturnPct)}`}>
            {formatCurrency(totalReturn)}
          </div>
          <p className={`text-xs ${getProfitColor(totalReturnPct)}`}>
            {formatPercentage(totalReturnPct)}
          </p>
        </CardContent>
      </Card>

      {/* Open Positions */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
          <Target className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{openPositions}</div>
          <p className="text-xs text-muted-foreground">
            Value: {formatCurrency(positionsValue)}
          </p>
        </CardContent>
      </Card>

      {/* Total Trades */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Trades</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{totalTrades}</div>
          <p className="text-xs text-muted-foreground">
            Since start
          </p>
        </CardContent>
      </Card>

      {/* Bot Status */}
      <Card className="md:col-span-2 lg:col-span-4">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Bot Status
          </CardTitle>
          <CardDescription>
            Current trading bot configuration and status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <p className="text-sm font-medium">Trading Mode</p>
              <Badge variant={tradingMode === 'live' ? 'destructive' : 'secondary'}>
                {tradingMode.toUpperCase()}
              </Badge>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">LLM Provider</p>
              <Badge variant="outline">{llmProvider.toUpperCase()}</Badge>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Exchange</p>
              <Badge variant="outline">{exchange.toUpperCase()}</Badge>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Run Interval</p>
              <Badge variant="outline">{runInterval}s</Badge>
            </div>
          </div>
          <div className="mt-4 text-sm text-muted-foreground">
            Last update: {new Date(lastUpdate).toLocaleString('en-US', {
              timeZone: 'America/New_York', // EST/EDT
              month: 'short',
              day: 'numeric',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Memoize with custom comparison to prevent re-renders when unrelated data changes
export const PortfolioOverview = memo(PortfolioOverviewComponent, (prevProps, nextProps) => {
  return prevProps.className === nextProps.className;
});
