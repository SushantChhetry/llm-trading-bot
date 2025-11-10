import { useState, useEffect } from 'react';
import { History, RotateCcw, X, Check } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Card, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';

// Get API base URL from environment variable or use relative path
// Vercel rewrites will handle /api/* requests, or use VITE_API_URL if set
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Helper function to build API URL (same as useTradingData)
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

interface ConfigVersion {
  id: number;
  version: number;
  name: string;
  description: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  created_by: string;
}

interface ConfigHistoryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ConfigHistoryDialog({ open, onOpenChange }: ConfigHistoryDialogProps) {
  const [history, setHistory] = useState<ConfigVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activating, setActivating] = useState<number | null>(null);

  useEffect(() => {
    if (open) {
      loadHistory();
    }
  }, [open]);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(getApiUrl('/api/config/history'));
      if (!response.ok) throw new Error('Failed to load configuration history');
      const data = await response.json();
      setHistory(data.configurations || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const activateConfig = async (configId: number) => {
    setActivating(configId);
    setError(null);
    try {
      const response = await fetch(getApiUrl(`/api/config/activate/${configId}`), {
        method: 'POST',
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to activate configuration');
      }
      
      const data = await response.json();
      if (data.success) {
        // Reload history to update active status
        await loadHistory();
        // Optionally reload the page
        window.location.reload();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate configuration');
    } finally {
      setActivating(null);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Configuration History
          </DialogTitle>
          <DialogDescription>
            View and restore previous configuration versions. Active configuration is marked with a badge.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-8 text-center text-muted-foreground">
            Loading configuration history...
          </div>
        ) : history.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground">
            No configuration history found.
          </div>
        ) : (
          <div className="space-y-4">
            {history.map((config) => (
              <Card key={config.id} className={config.is_active ? 'border-primary' : ''}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="flex items-center gap-2">
                        {config.name}
                        {config.is_active && (
                          <Badge variant="default">Active</Badge>
                        )}
                        {config.is_default && (
                          <Badge variant="secondary">Default</Badge>
                        )}
                      </CardTitle>
                      <CardDescription>
                        Version {config.version} • Created {formatDate(config.created_at)}
                        {config.created_by && ` by ${config.created_by}`}
                      </CardDescription>
                      {config.description && (
                        <p className="text-sm text-muted-foreground mt-2">
                          {config.description}
                        </p>
                      )}
                    </div>
                    {!config.is_active && (
                      <Button
                        size="sm"
                        onClick={() => activateConfig(config.id)}
                        disabled={activating === config.id}
                      >
                        {activating === config.id ? (
                          'Activating...'
                        ) : (
                          <>
                            <RotateCcw className="h-4 w-4 mr-2" />
                            Activate
                          </>
                        )}
                      </Button>
                    )}
                    {config.is_active && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Check className="h-4 w-4 text-primary" />
                        <span>Currently Active</span>
                      </div>
                    )}
                  </div>
                </CardHeader>
              </Card>
            ))}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            <X className="h-4 w-4 mr-2" />
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

