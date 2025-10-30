import { PnLChart } from './components/PnLChart';
import { PortfolioOverview } from './components/PortfolioOverview';
import { RecentTrades } from './components/RecentTrades';
import { useTradingData } from './hooks/useTradingData';
import { Separator } from './components/ui/separator';
import { Activity, AlertCircle, Loader2 } from 'lucide-react';

function App() {
  const { trades, portfolio, pnlData, botStatus, isLoading, error, refetch, isConnected, retryCount } = useTradingData();

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
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Activity className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-2xl font-bold">Trading Bot Dashboard</h1>
                <p className="text-muted-foreground">Real-time portfolio monitoring</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isConnected ? (
                <>
                  <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-muted-foreground">Live</span>
                </>
              ) : error ? (
                <>
                  <div className="h-2 w-2 bg-red-500 rounded-full"></div>
                  <span className="text-sm text-destructive">Disconnected</span>
                </>
              ) : (
                <>
                  <div className="h-2 w-2 bg-yellow-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-muted-foreground">Connecting...</span>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Error Banner (if error but we have cached data) */}
      {error && portfolio && (
        <div className="bg-destructive/10 border-l-4 border-destructive p-4 mx-4 mt-4 rounded">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <p className="text-sm text-destructive font-medium">{error}</p>
            </div>
            <button 
              onClick={refetch}
              className="text-sm px-3 py-1 bg-destructive text-destructive-foreground rounded hover:bg-destructive/90"
            >
              Retry
            </button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Showing cached data. Updates paused due to connection issues.
          </p>
        </div>
      )}

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <div className="space-y-6">
          {/* Portfolio Overview */}
          {portfolio && botStatus && (
            <PortfolioOverview portfolio={portfolio} botStatus={botStatus} />
          )}

          <Separator />

          {/* P&L Chart */}
          <PnLChart data={pnlData} />

          <Separator />

          {/* Recent Trades */}
          <RecentTrades trades={trades} />
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

export default App;
