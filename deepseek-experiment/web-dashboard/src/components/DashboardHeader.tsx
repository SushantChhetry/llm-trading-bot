import { memo } from 'react';
import { Activity } from 'lucide-react';
import { useConnectionStatus } from '@/contexts/TradingDataContext';

export const DashboardHeader = memo(function DashboardHeader() {
  const { isConnected, error } = useConnectionStatus();

  return (
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
  );
});
