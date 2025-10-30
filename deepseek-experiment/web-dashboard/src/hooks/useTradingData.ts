import { useState, useEffect, useCallback, useRef } from 'react';
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
const INITIAL_POLL_INTERVAL = 5000; // 5 seconds
const ERROR_RETRY_INTERVAL = 30000; // 30 seconds when error
const MAX_ERROR_RETRY_INTERVAL = 300000; // 5 minutes max delay

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
        fetch('/api/trades').catch(err => {
          throw new Error(`Failed to fetch trades: ${err.message}`);
        }),
        fetch('/api/portfolio').catch(err => {
          throw new Error(`Failed to fetch portfolio: ${err.message}`);
        }),
        fetch('/api/status').catch(err => {
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

      // Success - reset error state
      setData({
        trades,
        portfolio,
        pnlData,
        botStatus,
        isLoading: false,
        error: null,
        isConnected: true,
        retryCount: 0,
      });

      // Restart polling on success
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      intervalRef.current = setInterval(() => fetchData(false), INITIAL_POLL_INTERVAL);
      
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      
      setData(prev => {
        const newRetryCount = isManualRetry ? 0 : prev.retryCount + 1;
        
        // Stop polling if we've exceeded retry limit
        if (newRetryCount >= MAX_RETRY_COUNT && !isManualRetry) {
          // Clear existing intervals
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          
          // Set up longer retry interval for error recovery
          const retryDelay = Math.min(
            ERROR_RETRY_INTERVAL * Math.pow(2, newRetryCount - MAX_RETRY_COUNT), 
            MAX_ERROR_RETRY_INTERVAL
          );
          
          if (retryTimeoutRef.current) {
            clearTimeout(retryTimeoutRef.current);
          }
          
          retryTimeoutRef.current = setTimeout(() => {
            setData(current => ({ ...current, retryCount: 0 }));
            fetchData(false);
          }, retryDelay);
        }
        
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

    // Set up initial polling interval (will be managed by fetchData)
    intervalRef.current = setInterval(() => {
      fetchData(false);
    }, INITIAL_POLL_INTERVAL);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, [fetchData]);

  return {
    ...data,
    refetch: manualRefetch,
  };
}
