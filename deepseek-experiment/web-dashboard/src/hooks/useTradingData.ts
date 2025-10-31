import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Trade, Portfolio, PnLDataPoint, BotStatus } from '@/types/trading';

interface TradingData {
  trades: Trade[];
  portfolio: Portfolio | null;
  pnlData: PnLDataPoint[];
  botStatus: BotStatus | null;
  isLoading: boolean;
  error: string | null;
  isConnected: boolean;
  retryCount: number;
}

const MAX_RETRY_COUNT = 3;
const INITIAL_POLL_INTERVAL = 30000; // 30 seconds (optimized for Alpha Arena - bot updates every 2.5 min)
const ERROR_RETRY_INTERVAL = 30000; // 30 seconds when error
const MAX_ERROR_RETRY_INTERVAL = 300000; // 5 minutes max delay

// Get API base URL from environment variable or use relative path
// Vercel rewrites will handle /api/* requests, or use VITE_API_URL if set
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Helper function to build API URL
const getApiUrl = (endpoint: string): string => {
  if (API_BASE_URL) {
    // If VITE_API_URL is set, use it (with or without trailing slash)
    const base = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${base}${path}`;
  }
  // Otherwise use relative path (works with Vercel rewrites and local dev proxy)
  return endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
};

export function useTradingData() {
  const [data, setData] = useState<TradingData>({
    trades: [],
    portfolio: null,
    pnlData: [],
    botStatus: null,
    isLoading: true,
    error: null,
    isConnected: false,
    retryCount: 0,
  });

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const getErrorMessage = (error: unknown, status?: number): string => {
    if (status === 502) {
      return 'Backend service is unavailable (502). The API server may be starting up or experiencing issues.';
    }
    if (status === 503) {
      return 'Service temporarily unavailable (503). Please try again in a moment.';
    }
    if (status === 404) {
      return 'API endpoint not found (404). The service may be misconfigured.';
    }
    if (status === 403) {
      return 'Access forbidden (403). CORS or authentication issue.';
    }
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return 'Network error: Unable to connect to the API server. Check your connection.';
    }
    if (error instanceof Error) {
      return error.message;
    }
    return 'Unknown error occurred while fetching data.';
  };

  const fetchData = useCallback(async (isManualRetry = false) => {
    try {
      setData(prev => {
        // Don't fetch if we've exceeded retry limit and it's not a manual retry
        if (!isManualRetry && prev.retryCount >= MAX_RETRY_COUNT && prev.error) {
          return prev;
        }
        return { ...prev, isLoading: prev.error === null };
      });

      const [tradesRes, portfolioRes, statusRes] = await Promise.all([
        fetch(getApiUrl('/api/trades')).catch(err => {
          throw new Error(`Failed to fetch trades: ${err.message}`);
        }),
        fetch(getApiUrl('/api/portfolio')).catch(err => {
          throw new Error(`Failed to fetch portfolio: ${err.message}`);
        }),
        fetch(getApiUrl('/api/status')).catch(err => {
          throw new Error(`Failed to fetch status: ${err.message}`);
        }),
      ]);

      // Check for HTTP errors
      const errors: string[] = [];
      if (!tradesRes.ok) {
        errors.push(`Trades: ${tradesRes.status} ${tradesRes.statusText}`);
      }
      if (!portfolioRes.ok) {
        errors.push(`Portfolio: ${portfolioRes.status} ${portfolioRes.statusText}`);
      }
      if (!statusRes.ok) {
        errors.push(`Status: ${statusRes.status} ${statusRes.statusText}`);
      }

      if (errors.length > 0) {
        const statusCode = !tradesRes.ok ? tradesRes.status : !portfolioRes.ok ? portfolioRes.status : statusRes.status;
        throw new Error(getErrorMessage(null, statusCode));
      }

      const [trades, portfolio, botStatus] = await Promise.all([
        tradesRes.json(),
        portfolioRes.json(),
        statusRes.json(),
      ]);

      // Check if data has actually changed before updating state (prevents unnecessary re-renders)
      setData(prev => {
        const hasChanges = (
          JSON.stringify(prev.trades) !== JSON.stringify(trades) ||
          JSON.stringify(prev.portfolio) !== JSON.stringify(portfolio) ||
          JSON.stringify(prev.botStatus) !== JSON.stringify(botStatus)
        );

        // If no changes and already connected, skip the expensive update
        if (!hasChanges && prev.isConnected && !prev.error) {
          return prev;
        }

        // Generate PnL data points from trades (only if data changed)
        const pnlData: PnLDataPoint[] = [];
        const initialBalance = portfolio?.initial_balance && !isNaN(portfolio.initial_balance) ? portfolio.initial_balance : 10000;
        const positionsValue = portfolio?.positions_value && !isNaN(portfolio.positions_value) ? portfolio.positions_value : 0;
        let runningValue = initialBalance;
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
            const amount = trade.amount_usdt && !isNaN(trade.amount_usdt) ? trade.amount_usdt : 0;
            runningValue -= amount;
          } else if (trade.side === 'sell') {
            const quantity = trade.quantity && !isNaN(trade.quantity) ? trade.quantity : 0;
            const price = trade.price && !isNaN(trade.price) ? trade.price : 0;
            const sellValue = quantity * price;
            runningValue += sellValue;
            if (trade.profit !== undefined && !isNaN(trade.profit)) {
              runningReturn += trade.profit;
            }
          }

          // Ensure all values are valid numbers
          const totalValue = (runningValue + positionsValue) || 0;
          const totalReturn = runningReturn || 0;
          const totalReturnPct = initialBalance > 0 ? (totalReturn / initialBalance) * 100 : 0;

          pnlData.push({
            timestamp: trade.timestamp,
            total_value: totalValue,
            total_return: totalReturn,
            total_return_pct: totalReturnPct,
            trade_count: tradeCount,
          });
        }

        // Success - reset error state
        return {
          trades,
          portfolio,
          pnlData,
          botStatus,
          isLoading: false,
          error: null,
          isConnected: true,
          retryCount: 0,
        };
      });
      
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      
      setData(prev => {
        const newRetryCount = isManualRetry ? 0 : prev.retryCount + 1;
        
        return {
          ...prev,
          isLoading: false,
          error: errorMessage,
          isConnected: false,
          retryCount: newRetryCount,
        };
      });
    }
  }, []);

  const manualRefetch = useCallback(() => {
    // Reset retry count on manual retry
    setData(prev => ({ ...prev, retryCount: 0, error: null }));
    fetchData(true);
  }, [fetchData]);

  useEffect(() => {
    // Initial fetch
    fetchData(false);

    // Set up polling interval - fetchData will handle skipping if retry limit exceeded
    const pollInterval = setInterval(() => {
      fetchData(false);
    }, INITIAL_POLL_INTERVAL);
    
    intervalRef.current = pollInterval;
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
    };
  }, [fetchData]);

  return {
    ...data,
    refetch: manualRefetch,
  };
}
