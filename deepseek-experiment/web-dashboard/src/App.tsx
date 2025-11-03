import { PnLChart } from './components/PnLChart';
import { PortfolioOverview } from './components/PortfolioOverview';
import { RecentTrades } from './components/RecentTrades';
import { DashboardHeader } from './components/DashboardHeader';
import { ErrorBanner } from './components/ErrorBanner';
import { useTradingData } from './hooks/useTradingData';
import { TradingDataProvider } from './contexts/TradingDataContext';
import { Separator } from './components/ui/separator';
import { AlertCircle, Loader2 } from 'lucide-react';
import { useConnectionStatus, usePortfolio } from './contexts/TradingDataContext';

function DashboardContent() {
  const { isLoading, error, retryCount, refetch } = useConnectionStatus();
  const { portfolio } = usePortfolio();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading trading data...</p>
        </div>
      </div>
    );
  }

  if (error && !portfolio) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Connection Error</h2>
          <p className="text-destructive mb-6">{error}</p>

          {retryCount >= 3 && (
            <div className="bg-muted p-4 rounded-lg mb-4 text-left">
              <p className="text-sm font-medium mb-2">Troubleshooting Tips:</p>
              <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                <li>Check if the Railway API service is running</li>
                <li>Verify the API server is accessible</li>
                <li>Check browser console for more details</li>
                <li>Wait a moment and try again</li>
              </ul>
            </div>
          )}

          <button
            onClick={refetch}
            className="px-6 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 font-medium transition-colors"
          >
            {isLoading ? 'Retrying...' : 'Retry Connection'}
          </button>

          <p className="text-xs text-muted-foreground mt-4">
            Auto-retry paused after {retryCount} failed attempts
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <DashboardHeader />

      {/* Error Banner (if error but we have cached data) */}
      <ErrorBanner />

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <div className="space-y-6">
          {/* Portfolio Overview */}
          <PortfolioOverview />

          <Separator />

          {/* P&L Chart */}
          <PnLChart />

          <Separator />

          {/* Recent Trades */}
          <RecentTrades />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t bg-card mt-12">
        <div className="container mx-auto px-4 py-6">
          <div className="text-center text-sm text-muted-foreground">
            <p>Trading Bot Dashboard - Real-time monitoring and analytics</p>
            <p className="mt-1">Data updates every 5 seconds</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function App() {
  const tradingData = useTradingData();

  return (
    <TradingDataProvider value={tradingData}>
      <DashboardContent />
    </TradingDataProvider>
  );
}

export default App;
