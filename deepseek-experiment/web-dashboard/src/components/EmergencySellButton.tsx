import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { usePortfolioOverview } from '@/contexts/TradingDataContext';

// Get API base URL from environment variable or use relative path
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Helper function to build API URL (same as useTradingData)
const getApiUrl = (endpoint: string): string => {
  if (API_BASE_URL) {
    const base = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${base}${path}`;
  }
  return endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
};

interface EmergencySellResult {
  success: boolean;
  message: string;
  positions_sold?: number;
  trades?: Array<{
    symbol: string;
    trade_id: string;
    quantity: number;
    price: number;
    profit: number;
    profit_pct: number;
  }>;
  errors?: string[];
}

export function EmergencySellButton() {
  const { botStatus, portfolio, refetch } = usePortfolioOverview();
  const [isOpen, setIsOpen] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<EmergencySellResult | null>(null);

  const tradingMode = botStatus?.trading_mode ?? 'paper';
  const isLiveMode = tradingMode === 'live';
  const hasPositions = (portfolio?.open_positions ?? 0) > 0;

  const handleEmergencySell = async () => {
    setIsExecuting(true);
    setResult(null);

    try {
      const response = await fetch(getApiUrl('/api/emergency-sell'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Failed to execute emergency sell');
      }

      setResult({
        success: data.success,
        message: data.message,
        positions_sold: data.positions_sold,
        trades: data.trades,
        errors: data.errors,
      });

      // Refresh portfolio data after sell
      if (data.success && data.positions_sold > 0) {
        setTimeout(() => {
          refetch();
        }, 1000);
      }
    } catch (error) {
      setResult({
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    // Reset result after a delay to allow user to see it
    setTimeout(() => setResult(null), 100);
  };

  return (
    <>
      <Button
        variant="destructive"
        size="sm"
        disabled={!isLiveMode || !hasPositions}
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2"
        title={
          !isLiveMode
            ? 'Emergency sell is only available in live trading mode'
            : !hasPositions
            ? 'No open positions to sell'
            : 'Emergency sell all positions'
        }
      >
        <AlertTriangle className="h-4 w-4" />
        Emergency Sell All
      </Button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              Emergency Sell All Positions
            </DialogTitle>
            <DialogDescription>
              This will immediately sell all open positions using market orders.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>

          {!result ? (
            <>
              <div className="py-4">
                <p className="text-sm text-muted-foreground mb-4">
                  Are you sure you want to sell all positions? This is a fail-safe mechanism
                  to close all positions if the bot becomes unresponsive.
                </p>
                {portfolio && portfolio.open_positions > 0 && (
                  <div className="bg-muted p-3 rounded-md">
                    <p className="text-sm font-medium">
                      Open Positions: {portfolio.open_positions}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Positions Value: ${(portfolio.positions_value || 0).toFixed(2)}
                    </p>
                  </div>
                )}
              </div>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={handleClose}
                  disabled={isExecuting}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleEmergencySell}
                  disabled={isExecuting}
                >
                  {isExecuting ? 'Executing...' : 'Confirm Sell All'}
                </Button>
              </DialogFooter>
            </>
          ) : (
            <>
              <div className="py-4">
                <div
                  className={`p-4 rounded-md ${
                    result.success
                      ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                      : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
                  }`}
                >
                  <p
                    className={`text-sm font-medium ${
                      result.success
                        ? 'text-green-800 dark:text-green-200'
                        : 'text-red-800 dark:text-red-200'
                    }`}
                  >
                    {result.message}
                  </p>
                  {result.positions_sold !== undefined && (
                    <p className="text-sm text-muted-foreground mt-2">
                      Positions sold: {result.positions_sold}
                    </p>
                  )}
                  {result.trades && result.trades.length > 0 && (
                    <div className="mt-3 space-y-1">
                      <p className="text-sm font-medium text-muted-foreground">Trade Details:</p>
                      {result.trades.map((trade, idx) => (
                        <div key={idx} className="text-xs text-muted-foreground pl-2">
                          {trade.symbol}: {trade.quantity.toFixed(6)} @ ${trade.price.toFixed(2)} 
                          {' '}({trade.profit >= 0 ? '+' : ''}{trade.profit.toFixed(2)} / {trade.profit_pct >= 0 ? '+' : ''}{trade.profit_pct.toFixed(2)}%)
                        </div>
                      ))}
                    </div>
                  )}
                  {result.errors && result.errors.length > 0 && (
                    <div className="mt-3">
                      <p className="text-sm font-medium text-red-800 dark:text-red-200">Errors:</p>
                      <ul className="list-disc list-inside text-sm text-red-700 dark:text-red-300 mt-1 space-y-1">
                        {result.errors.map((error, idx) => (
                          <li key={idx}>{error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              <DialogFooter>
                <Button onClick={handleClose}>Close</Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

