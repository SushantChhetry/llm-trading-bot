import { memo } from 'react';
import { AlertCircle } from 'lucide-react';
import { useConnectionStatus, usePortfolio } from '@/contexts/TradingDataContext';

export const ErrorBanner = memo(function ErrorBanner() {
  const { error, refetch } = useConnectionStatus();
  const { portfolio } = usePortfolio();

  if (!error || !portfolio) {
    return null;
  }

  return (
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
  );
});
