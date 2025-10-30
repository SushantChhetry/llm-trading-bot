import { PnLChart } from './components/PnLChart';
import { PortfolioOverview } from './components/PortfolioOverview';
import { RecentTrades } from './components/RecentTrades';
import { useTradingData } from './hooks/useTradingData';
import { Separator } from './components/ui/separator';
import { Activity, AlertCircle, Loader2 } from 'lucide-react';

function App() {
  const { trades, portfolio, pnlData, botStatus, isLoading, error, refetch } = useTradingData();

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

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-4" />
          <p className="text-destructive mb-4">Error loading data: {error}</p>
          <button 
            onClick={refetch}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Retry
          </button>
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
              <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-muted-foreground">Live</span>
            </div>
          </div>
        </div>
      </header>

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
