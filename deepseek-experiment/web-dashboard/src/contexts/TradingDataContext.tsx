import { createContext, useContext, useMemo, ReactNode } from 'react';
import { Trade, Portfolio, PnLDataPoint, BotStatus } from '@/types/trading';

interface TradingDataState {
  trades: Trade[];
  portfolio: Portfolio | null;
  pnlData: PnLDataPoint[];
  botStatus: BotStatus | null;
  isLoading: boolean;
  error: string | null;
  isConnected: boolean;
  retryCount: number;
  refetch: () => void;
}

interface TradingDataContextValue extends TradingDataState {}

const TradingDataContext = createContext<TradingDataContextValue | undefined>(undefined);

interface TradingDataProviderProps {
  children: ReactNode;
  value: TradingDataState;
}

export function TradingDataProvider({ children, value }: TradingDataProviderProps) {
  // Memoize the context value using JSON.stringify for deep comparison
  // This ensures we only update when actual data changes, not object references
  const contextValue = useMemo(() => value, [
    JSON.stringify(value.trades),
    JSON.stringify(value.portfolio),
    JSON.stringify(value.pnlData),
    JSON.stringify(value.botStatus),
    value.isLoading,
    value.error,
    value.isConnected,
    value.retryCount,
    // refetch is a function, should be stable from useCallback
  ]);

  return (
    <TradingDataContext.Provider value={contextValue}>
      {children}
    </TradingDataContext.Provider>
  );
}

// Custom hooks to access specific parts of the context
// These hooks will only cause re-renders when their specific data changes
export function useTradingDataContext() {
  const context = useContext(TradingDataContext);
  if (context === undefined) {
    throw new Error('useTradingDataContext must be used within a TradingDataProvider');
  }
  return context;
}

// Selector hooks - components using these will only re-render when specific data changes
export function usePortfolio() {
  const { portfolio, isLoading, error } = useTradingDataContext();
  return useMemo(() => ({ portfolio, isLoading, error }), [portfolio, isLoading, error]);
}

export function useBotStatus() {
  const { botStatus, isLoading, error } = useTradingDataContext();
  return useMemo(() => ({ botStatus, isLoading, error }), [botStatus, isLoading, error]);
}

export function useTrades() {
  const { trades, isLoading, error } = useTradingDataContext();
  return useMemo(() => ({ trades, isLoading, error }), [trades, isLoading, error]);
}

export function usePnLData() {
  const { pnlData, isLoading, error } = useTradingDataContext();
  return useMemo(() => ({ pnlData, isLoading, error }), [pnlData, isLoading, error]);
}

export function useConnectionStatus() {
  const { isConnected, error, isLoading, retryCount, refetch } = useTradingDataContext();
  return useMemo(
    () => ({ isConnected, error, isLoading, retryCount, refetch }),
    [isConnected, error, isLoading, retryCount, refetch]
  );
}

// Combined hook for components that need both portfolio and botStatus
export function usePortfolioOverview() {
  const { portfolio, botStatus, isLoading, error } = useTradingDataContext();
  return useMemo(
    () => ({ portfolio, botStatus, isLoading, error }),
    [portfolio, botStatus, isLoading, error]
  );
}
