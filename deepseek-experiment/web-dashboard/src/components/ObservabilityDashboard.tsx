import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Activity, Server, AlertTriangle, CheckCircle, XCircle, Clock } from 'lucide-react';

interface HealthCheck {
  id?: number;
  timestamp: string;
  service_name: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  details?: Record<string, unknown>;
}

interface ObservabilityData {
  timestamp: string;
  services: {
    'trading-bot': {
      health: HealthCheck | null;
      metrics: {
        counters: Record<string, number>;
        gauges: Record<string, number>;
        histograms: Record<string, { count: number; min: number; max: number; avg: number }>;
      };
    };
    'trading-bot-api': {
      health: HealthCheck | null;
      metrics: Record<string, unknown>;
    };
  };
  metrics_summary: Record<string, unknown>;
}

interface ObservabilityDashboardProps {
  className?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export function ObservabilityDashboard({ className }: ObservabilityDashboardProps) {
  const [data, setData] = useState<ObservabilityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchObservabilityData = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/observability`);
      if (!response.ok) {
        throw new Error(`Failed to fetch observability data: ${response.statusText}`);
      }
      const observabilityData = await response.json();
      setData(observabilityData);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching observability data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchObservabilityData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchObservabilityData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'unhealthy':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'degraded':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'unhealthy':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Observability
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Loading observability data...</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Observability
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-500">Error: {error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Observability
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No observability data available</p>
        </CardContent>
      </Card>
    );
  }

  const botHealth = data.services['trading-bot']?.health;
  const apiHealth = data.services['trading-bot-api']?.health;
  const botMetrics = data.services['trading-bot']?.metrics || { counters: {}, gauges: {}, histograms: {} };

  return (
    <div className={className}>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            System Observability
          </CardTitle>
          <CardDescription>
            Real-time monitoring of bot and API services
            {lastUpdate && (
              <span className="ml-2 text-xs">
                Last updated: {lastUpdate.toLocaleTimeString()}
              </span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Service Health Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  Trading Bot Service
                </CardTitle>
              </CardHeader>
              <CardContent>
                {botHealth ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(botHealth.status)}
                      <Badge
                        variant="outline"
                        className={`${getStatusColor(botHealth.status)} text-white border-0`}
                      >
                        {botHealth.status.toUpperCase()}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Last check: {new Date(botHealth.timestamp).toLocaleString()}
                    </p>
                    {botHealth.details && Object.keys(botHealth.details).length > 0 && (
                      <div className="mt-2 text-xs">
                        <p className="font-medium mb-1">Details:</p>
                        <pre className="bg-muted p-2 rounded text-xs overflow-auto">
                          {JSON.stringify(botHealth.details, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No health data available</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  API Service
                </CardTitle>
              </CardHeader>
              <CardContent>
                {apiHealth ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(apiHealth.status)}
                      <Badge
                        variant="outline"
                        className={`${getStatusColor(apiHealth.status)} text-white border-0`}
                      >
                        {apiHealth.status.toUpperCase()}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Last check: {new Date(apiHealth.timestamp).toLocaleString()}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No health data available</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Metrics Summary */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Bot Metrics Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* Counters */}
                {Object.keys(botMetrics.counters || {}).length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">Counters</p>
                    <div className="space-y-1">
                      {Object.entries(botMetrics.counters).slice(0, 5).map(([name, value]) => (
                        <div key={name} className="flex justify-between text-xs">
                          <span className="truncate">{name}</span>
                          <span className="font-mono">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Gauges */}
                {Object.keys(botMetrics.gauges || {}).length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">Gauges</p>
                    <div className="space-y-1">
                      {Object.entries(botMetrics.gauges).slice(0, 5).map(([name, value]) => (
                        <div key={name} className="flex justify-between text-xs">
                          <span className="truncate">{name}</span>
                          <span className="font-mono">{typeof value === 'number' ? value.toFixed(2) : String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Histograms */}
                {Object.keys(botMetrics.histograms || {}).length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">Histograms</p>
                    <div className="space-y-1">
                      {Object.entries(botMetrics.histograms).slice(0, 5).map(([name, stats]) => (
                        <div key={name} className="text-xs">
                          <div className="font-medium truncate">{name}</div>
                          <div className="text-muted-foreground ml-2">
                            avg: {typeof stats === 'object' && stats?.avg ? stats.avg.toFixed(2) : 'N/A'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* System Info */}
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-2">System Info</p>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span>Total Metrics</span>
                      <span className="font-mono">
                        {(Object.keys(botMetrics.counters || {}).length +
                          Object.keys(botMetrics.gauges || {}).length +
                          Object.keys(botMetrics.histograms || {}).length)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Last Update</span>
                      <span className="font-mono text-xs">
                        {lastUpdate ? lastUpdate.toLocaleTimeString() : 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Refresh Button */}
          <div className="flex justify-end">
            <button
              onClick={fetchObservabilityData}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Refresh
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

