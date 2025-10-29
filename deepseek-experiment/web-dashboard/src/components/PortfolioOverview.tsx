import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { formatCurrency, formatPercentage, getProfitColor } from '@/lib/utils';
import { Portfolio, BotStatus } from '@/types/trading';
import { TrendingUp, TrendingDown, DollarSign, Activity, Target, Zap } from 'lucide-react';

interface PortfolioOverviewProps {
  portfolio: Portfolio;
  botStatus: BotStatus;
  className?: string;
}

export function PortfolioOverview({ portfolio, botStatus, className }: PortfolioOverviewProps) {
  const isPositive = portfolio.total_return_pct >= 0;
  const TrendIcon = isPositive ? TrendingUp : TrendingDown;

  return (
    <div className={`grid gap-4 md:grid-cols-2 lg:grid-cols-4 ${className}`}>
      {/* Total Portfolio Value */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Value</CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatCurrency(portfolio.total_value)}</div>
          <p className="text-xs text-muted-foreground">
            Balance: {formatCurrency(portfolio.balance)}
          </p>
        </CardContent>
      </Card>

      {/* Total Return */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Return</CardTitle>
          <TrendIcon className={`h-4 w-4 ${getProfitColor(portfolio.total_return_pct)}`} />
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${getProfitColor(portfolio.total_return_pct)}`}>
            {formatCurrency(portfolio.total_return)}
          </div>
          <p className={`text-xs ${getProfitColor(portfolio.total_return_pct)}`}>
            {formatPercentage(portfolio.total_return_pct)}
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
          <div className="text-2xl font-bold">{portfolio.open_positions}</div>
          <p className="text-xs text-muted-foreground">
            Value: {formatCurrency(portfolio.positions_value)}
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
          <div className="text-2xl font-bold">{portfolio.total_trades}</div>
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
              <Badge variant={botStatus.trading_mode === 'live' ? 'destructive' : 'secondary'}>
                {botStatus.trading_mode.toUpperCase()}
              </Badge>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">LLM Provider</p>
              <Badge variant="outline">{botStatus.llm_provider.toUpperCase()}</Badge>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Exchange</p>
              <Badge variant="outline">{botStatus.exchange.toUpperCase()}</Badge>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Run Interval</p>
              <Badge variant="outline">{botStatus.run_interval_seconds}s</Badge>
            </div>
          </div>
          <div className="mt-4 text-sm text-muted-foreground">
            Last update: {new Date(botStatus.last_update).toLocaleString()}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
