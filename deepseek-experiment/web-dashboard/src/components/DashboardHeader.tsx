import { memo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Settings } from 'lucide-react';
import { useConnectionStatus, usePortfolio } from '@/contexts/TradingDataContext';
import { formatCurrency, formatPercentage, getProfitColor } from '@/lib/utils';
import { SettingsDialog } from './SettingsDialog';

export const DashboardHeader = memo(function DashboardHeader() {
  const { isConnected, error } = useConnectionStatus();
  const { portfolio } = usePortfolio();
  const [settingsOpen, setSettingsOpen] = useState(false);
  
  const totalValue = portfolio?.total_value ?? 0;
  const totalReturnPct = portfolio?.total_return_pct ?? 0;

  return (
    <header className="border-b bg-card">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <img 
              src="/logos/DeepSeek_logo.svg" 
              alt="DeepSeek Logo" 
              className="h-8 w-8"
            />
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Trading Bot Dashboard</h1>
              <p className="text-muted-foreground text-sm font-normal">
                {portfolio ? (
                  <>
                    Portfolio: <span className="font-medium">{formatCurrency(totalValue)}</span>
                    {' • '}
                    Return: <span className={`font-medium ${getProfitColor(totalReturnPct)}`}>
                      {formatPercentage(totalReturnPct)}
                    </span>
                  </>
                ) : (
                  'Real-time portfolio monitoring'
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSettingsOpen(true)}
              className="px-4 py-2 text-sm font-medium text-foreground hover:text-primary transition-colors border border-border rounded-md hover:border-primary tracking-normal flex items-center gap-2"
            >
              <Settings className="h-4 w-4" />
              Settings
            </button>
            <Link
              to="/docs"
              className="px-4 py-2 text-sm font-medium text-foreground hover:text-primary transition-colors border border-border rounded-md hover:border-primary tracking-normal"
            >
              What is This?
            </Link>
            <div className="flex items-center gap-2">
              {isConnected ? (
                <>
                  <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-muted-foreground">Connected</span>
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
      </div>
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </header>
  );
});
