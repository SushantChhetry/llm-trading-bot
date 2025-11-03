import { memo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { formatCurrency, formatTimestamp, getProfitColor } from '@/lib/utils';
import { useTrades } from '@/contexts/TradingDataContext';
import { ArrowUp, ArrowDown, Clock, Target, Brain } from 'lucide-react';
import { AIDecisionDetail } from './AIDecisionDetail';

interface RecentTradesProps {
  className?: string;
}

function RecentTradesComponent({ className }: RecentTradesProps) {
  const { trades } = useTrades();
  const recentTrades = trades.slice(-10).reverse(); // Show last 10 trades, most recent first

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Target className="h-5 w-5" />
          Recent Trades
        </CardTitle>
        <CardDescription>
          Latest trading activity and decisions
        </CardDescription>
      </CardHeader>
      <CardContent>
        {recentTrades.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No trades yet
          </div>
        ) : (
          <div className="space-y-4">
            {recentTrades.map((trade) => (
              <div key={trade.id} className="p-4 border rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      {trade.side === 'buy' ? (
                        <ArrowUp className="h-4 w-4 text-green-600" />
                      ) : (
                        <ArrowDown className="h-4 w-4 text-red-600" />
                      )}
                      <Badge variant={trade.side === 'buy' ? 'success' : 'destructive'}>
                        {trade.side.toUpperCase()}
                      </Badge>
                    </div>
                    <div>
                      <p className="font-medium">{trade.symbol}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatCurrency(trade.price)} × {trade.quantity.toFixed(6)}
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="font-medium">{formatCurrency(trade.amount_usdt)}</p>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Brain className="h-3 w-3" />
                      <span>Conf: {(trade.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  {trade.profit !== undefined && (
                    <div className="text-right">
                      <p className={`font-medium ${getProfitColor(trade.profit)}`}>
                        {formatCurrency(trade.profit)}
                      </p>
                      <Badge variant={trade.profit >= 0 ? 'success' : 'destructive'} className="text-xs">
                        {trade.profit >= 0 ? 'Profit' : 'Loss'}
                      </Badge>
                    </div>
                  )}

                  <div className="text-right text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      <span>{formatTimestamp(trade.timestamp)}</span>
                    </div>
                    {trade.llm_risk_assessment && (
                      <Badge variant="outline" className="text-xs mt-1">
                        {trade.llm_risk_assessment}
                      </Badge>
                    )}
                  </div>
                </div>
                <AIDecisionDetail trade={trade} />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Memoize with custom comparison to prevent re-renders when unrelated data changes
export const RecentTrades = memo(RecentTradesComponent, (prevProps, nextProps) => {
  return prevProps.className === nextProps.className;
});
