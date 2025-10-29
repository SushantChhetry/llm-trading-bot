import { useState, useEffect, useCallback } from 'react';
import { Trade, Portfolio, PnLDataPoint, BotStatus } from '@/types/trading';

interface TradingData {
  trades: Trade[];
  portfolio: Portfolio | null;
  pnlData: PnLDataPoint[];
  botStatus: BotStatus | null;
  isLoading: boolean;
  error: string | null;
}

export function useTradingData() {
  const [data, setData] = useState<TradingData>({
    trades: [],
    portfolio: null,
    pnlData: [],
    botStatus: null,
    isLoading: true,
    error: null,
  });

  const fetchData = useCallback(async () => {
    try {
      const [tradesRes, portfolioRes, statusRes] = await Promise.all([
        fetch('/api/trades'),
        fetch('/api/portfolio'),
        fetch('/api/status'),
      ]);

      if (!tradesRes.ok || !portfolioRes.ok || !statusRes.ok) {
        throw new Error('Failed to fetch data');
      }

      const [trades, portfolio, botStatus] = await Promise.all([
        tradesRes.json(),
        portfolioRes.json(),
        statusRes.json(),
      ]);

      // Generate PnL data points from trades
      const pnlData: PnLDataPoint[] = [];
      let runningValue = portfolio?.initial_balance || 10000;
      let runningReturn = 0;
      let tradeCount = 0;

      // Add initial point
      pnlData.push({
        timestamp: new Date().toISOString(),
        total_value: runningValue,
        total_return: 0,
        total_return_pct: 0,
        trade_count: 0,
      });

      // Process trades chronologically
      const sortedTrades = [...trades].sort((a, b) => 
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      );

      for (const trade of sortedTrades) {
        tradeCount++;
        
        if (trade.side === 'buy') {
          runningValue -= trade.amount_usdt;
        } else if (trade.side === 'sell') {
          const sellValue = trade.quantity * trade.price;
          runningValue += sellValue;
          if (trade.profit !== undefined) {
            runningReturn += trade.profit;
          }
        }

        pnlData.push({
          timestamp: trade.timestamp,
          total_value: runningValue + (portfolio?.positions_value || 0),
          total_return: runningReturn,
          total_return_pct: (runningReturn / (portfolio?.initial_balance || 10000)) * 100,
          trade_count: tradeCount,
        });
      }

      setData({
        trades,
        portfolio,
        pnlData,
        botStatus,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      setData(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }));
    }
  }, []);

  useEffect(() => {
    fetchData();
    
    // Set up polling every 5 seconds
    const interval = setInterval(fetchData, 5000);
    
    return () => clearInterval(interval);
  }, [fetchData]);

  return {
    ...data,
    refetch: fetchData,
  };
}
