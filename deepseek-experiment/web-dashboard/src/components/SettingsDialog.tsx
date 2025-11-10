import { useState, useEffect } from 'react';
import { Settings, Save, X, RotateCcw, History } from 'lucide-react';
import { ConfigHistoryDialog } from './ConfigHistoryDialog';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Switch } from './ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';

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

interface ConfigData {
  llm: {
    provider: string;
    api_key: string;
    api_url: string;
    model: string;
    temperature: number;
    max_tokens: number;
    timeout: number;
  };
  exchange: {
    name: string;
    symbol: string;
    use_testnet: boolean;
  };
  trading: {
    mode: string;
    initial_balance: number;
    max_position_size: number;
    max_leverage: number;
    default_leverage: number;
    trading_fee_percent: number;
    max_risk_per_trade: number;
    stop_loss_percent: number;
    take_profit_percent: number;
    max_active_positions: number;
    min_confidence_threshold: number;
    fee_impact_warning_threshold: number;
    run_interval_seconds: number;
  };
  position_management: {
    enable_position_monitoring: boolean;
    portfolio_profit_target_pct: number;
    enable_trailing_stop_loss: boolean;
    trailing_stop_distance_pct: number;
    trailing_stop_activation_pct: number;
    enable_partial_profit_taking: boolean;
    partial_profit_percent: number;
    partial_profit_target_pct: number;
  };
  logging: {
    level: string;
  };
}

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [configName, setConfigName] = useState('');
  const [configDescription, setConfigDescription] = useState('');
  const [historyOpen, setHistoryOpen] = useState(false);

  useEffect(() => {
    if (open) {
      loadCurrentConfig();
    }
  }, [open]);

  const loadCurrentConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(getApiUrl('/api/config/current'));
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = 'Failed to load configuration';
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          errorMessage = errorText || `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }
      const data = await response.json();
      setConfig(data.config);
      setConfigName(data.name || '');
      setConfigDescription(data.description || '');
    } catch (err) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        setError(`Cannot connect to API server. Please check if the server is running.`);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load configuration');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadDefaultConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(getApiUrl('/api/config/default'));
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = 'Failed to load default configuration';
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          errorMessage = errorText || `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }
      const data = await response.json();
      setConfig(data.config);
      setConfigName('Default Configuration');
      setConfigDescription('Reset to system defaults');
    } catch (err) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        setError(`Cannot connect to API server. Please check if the server is running.`);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load default configuration');
      }
    } finally {
      setLoading(false);
    }
  };

  const validateConfig = (): string | null => {
    if (!config) return 'Configuration is missing';
    if (!config.llm) return 'LLM configuration is missing';
    if (!config.trading) return 'Trading configuration is missing';
    if (!config.exchange) return 'Exchange configuration is missing';
    
    // Validate LLM
    if (!config.llm.provider) return 'LLM provider is required';
    if (config.llm.temperature < 0 || config.llm.temperature > 2) {
      return 'Temperature must be between 0 and 2';
    }
    if (config.llm.max_tokens < 1 || config.llm.max_tokens > 100000) {
      return 'Max tokens must be between 1 and 100,000';
    }
    if (config.llm.timeout < 1 || config.llm.timeout > 300) {
      return 'Timeout must be between 1 and 300 seconds';
    }
    
    // Validate Trading
    if (!['paper', 'live'].includes(config.trading.mode)) {
      return 'Trading mode must be "paper" or "live"';
    }
    if (config.trading.initial_balance <= 0) {
      return 'Initial balance must be greater than 0';
    }
    if (config.trading.max_position_size <= 0 || config.trading.max_position_size > 1) {
      return 'Max position size must be between 0 and 1 (0-100%)';
    }
    if (config.trading.max_leverage < 1 || config.trading.max_leverage > 100) {
      return 'Max leverage must be between 1 and 100';
    }
    if (config.trading.stop_loss_percent <= 0 || config.trading.stop_loss_percent > 50) {
      return 'Stop loss must be between 0 and 50%';
    }
    if (config.trading.take_profit_percent <= 0 || config.trading.take_profit_percent > 100) {
      return 'Take profit must be between 0 and 100%';
    }
    if (config.trading.max_active_positions < 1 || config.trading.max_active_positions > 50) {
      return 'Max active positions must be between 1 and 50';
    }
    if (config.trading.min_confidence_threshold < 0 || config.trading.min_confidence_threshold > 1) {
      return 'Min confidence threshold must be between 0 and 1';
    }
    if (config.trading.run_interval_seconds < 10 || config.trading.run_interval_seconds > 3600) {
      return 'Run interval must be between 10 and 3600 seconds';
    }
    
    // Validate Exchange
    if (!['kraken', 'bybit', 'binance', 'coinbase'].includes(config.exchange.name)) {
      return 'Invalid exchange name';
    }
    if (!config.exchange.symbol || config.exchange.symbol.trim() === '') {
      return 'Trading symbol is required';
    }
    
    // Validate Position Management
    if (config.position_management.portfolio_profit_target_pct < 0 || config.position_management.portfolio_profit_target_pct > 100) {
      return 'Portfolio profit target must be between 0 and 100%';
    }
    if (config.position_management.trailing_stop_distance_pct < 0 || config.position_management.trailing_stop_distance_pct > 10) {
      return 'Trailing stop distance must be between 0 and 10%';
    }
    if (config.position_management.partial_profit_percent < 0 || config.position_management.partial_profit_percent > 100) {
      return 'Partial profit percent must be between 0 and 100%';
    }
    
    return null;
  };

  const handleSave = async (activate: boolean = true) => {
    if (!config) return;
    
    // Validate configuration
    const validationError = validateConfig();
    if (validationError) {
      setError(validationError);
      return;
    }
    
    setSaving(true);
    setError(null);
    try {
      const response = await fetch(getApiUrl('/api/config/save'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config,
          name: configName || 'Custom Configuration',
          description: configDescription,
          activate,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save configuration');
      }
      
      const data = await response.json();
      if (data.success) {
        onOpenChange(false);
        // Optionally reload the page or show a success message
        window.location.reload();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const updateConfig = (path: string[], value: string | number | boolean) => {
    if (!config) return;
    const newConfig = { ...config };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let current: any = newConfig;
    for (let i = 0; i < path.length - 1; i++) {
      current = current[path[i]] = { ...current[path[i]] };
    }
    current[path[path.length - 1]] = value;
    setConfig(newConfig);
  };

  if (loading && !config) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Loading Configuration...</DialogTitle>
            <DialogDescription>Please wait while we load your configuration...</DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    );
  }

  if (!config || !config.llm || !config.trading || !config.exchange) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Error</DialogTitle>
            <DialogDescription>{error || 'Failed to load configuration. The configuration structure is invalid.'}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={() => onOpenChange(false)}>Close</Button>
            <Button onClick={loadDefaultConfig} variant="outline">
              <RotateCcw className="h-4 w-4 mr-2" />
              Load Default Config
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Trading Bot Configuration
          </DialogTitle>
          <DialogDescription>
            Configure your trading bot settings. Changes are saved as versioned configurations that can be reverted.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="config-name">Configuration Name</Label>
            <Input
              id="config-name"
              value={configName}
              onChange={(e) => setConfigName(e.target.value)}
              placeholder="e.g., Aggressive Strategy v1"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="config-description">Description (Optional)</Label>
            <Input
              id="config-description"
              value={configDescription}
              onChange={(e) => setConfigDescription(e.target.value)}
              placeholder="Describe what this configuration does..."
            />
          </div>

          <Tabs defaultValue="llm" className="w-full">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="llm">LLM</TabsTrigger>
              <TabsTrigger value="trading">Trading</TabsTrigger>
              <TabsTrigger value="risk">Risk</TabsTrigger>
              <TabsTrigger value="positions">Positions</TabsTrigger>
              <TabsTrigger value="exchange">Exchange</TabsTrigger>
            </TabsList>

            <TabsContent value="llm" className="space-y-4 mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>LLM Configuration</CardTitle>
                  <CardDescription>Configure the AI model that makes trading decisions</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="llm-provider">Provider</Label>
                    <Select
                      value={config.llm.provider}
                      onValueChange={(value) => updateConfig(['llm', 'provider'], value)}
                    >
                      <SelectTrigger id="llm-provider">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="mock">Mock (Testing)</SelectItem>
                        <SelectItem value="deepseek">DeepSeek</SelectItem>
                        <SelectItem value="openai">OpenAI</SelectItem>
                        <SelectItem value="anthropic">Anthropic</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      The AI provider that will analyze market data and make trading decisions. Mock mode is for testing without API costs.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="llm-model">Model Name</Label>
                    <Input
                      id="llm-model"
                      value={config.llm.model}
                      onChange={(e) => updateConfig(['llm', 'model'], e.target.value)}
                      placeholder="e.g., deepseek-chat"
                    />
                    <p className="text-xs text-muted-foreground">
                      Specific model to use. Leave empty for provider defaults.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="llm-temperature">Temperature: {config.llm.temperature}</Label>
                    <Input
                      id="llm-temperature"
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={config.llm.temperature}
                      onChange={(e) => updateConfig(['llm', 'temperature'], parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Controls randomness (0 = deterministic, 2 = very creative). Lower values = more consistent decisions. Recommended: 0.7
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="llm-max-tokens">Max Tokens</Label>
                    <Input
                      id="llm-max-tokens"
                      type="number"
                      value={config.llm.max_tokens}
                      onChange={(e) => updateConfig(['llm', 'max_tokens'], parseInt(e.target.value))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Maximum length of AI responses. Higher = more detailed analysis but higher costs. Recommended: 500-2000
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="llm-timeout">Timeout (seconds)</Label>
                    <Input
                      id="llm-timeout"
                      type="number"
                      value={config.llm.timeout}
                      onChange={(e) => updateConfig(['llm', 'timeout'], parseInt(e.target.value))}
                    />
                    <p className="text-xs text-muted-foreground">
                      How long to wait for AI response before timing out. Recommended: 30 seconds
                    </p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="trading" className="space-y-4 mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Trading Parameters</CardTitle>
                  <CardDescription>Core trading behavior and limits</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="trading-mode">Trading Mode</Label>
                    <Select
                      value={config.trading.mode}
                      onValueChange={(value) => updateConfig(['trading', 'mode'], value)}
                    >
                      <SelectTrigger id="trading-mode">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="paper">Paper Trading (Simulated)</SelectItem>
                        <SelectItem value="live">Live Trading (Real Money) ⚠️</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      ⚠️ Live mode uses real money. Paper mode is safe for testing.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="initial-balance">Initial Balance (USDT)</Label>
                    <Input
                      id="initial-balance"
                      type="number"
                      step="0.01"
                      value={config.trading.initial_balance}
                      onChange={(e) => updateConfig(['trading', 'initial_balance'], parseFloat(e.target.value))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Starting capital for paper trading. This is your virtual starting amount.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="max-position-size">Max Position Size: {(config.trading.max_position_size * 100).toFixed(1)}%</Label>
                    <Input
                      id="max-position-size"
                      type="range"
                      min="0.01"
                      max="1"
                      step="0.01"
                      value={config.trading.max_position_size}
                      onChange={(e) => updateConfig(['trading', 'max_position_size'], parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Maximum % of balance to use per trade. 10% = can use up to 10% of balance per trade. Lower = more conservative.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="run-interval">Run Interval (seconds)</Label>
                    <Input
                      id="run-interval"
                      type="number"
                      value={config.trading.run_interval_seconds}
                      onChange={(e) => updateConfig(['trading', 'run_interval_seconds'], parseInt(e.target.value))}
                    />
                    <p className="text-xs text-muted-foreground">
                      How often the bot checks the market and makes decisions. 150 seconds = 2.5 minutes (Alpha Arena style).
                    </p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="risk" className="space-y-4 mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Risk Management</CardTitle>
                  <CardDescription>Protect your capital with risk controls</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="stop-loss">Stop Loss: {config.trading.stop_loss_percent}%</Label>
                    <Input
                      id="stop-loss"
                      type="range"
                      min="0.5"
                      max="10"
                      step="0.1"
                      value={config.trading.stop_loss_percent}
                      onChange={(e) => updateConfig(['trading', 'stop_loss_percent'], parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Automatically sell if price drops by this %. 2% = sell if down 2%. Protects against big losses.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="take-profit">Take Profit: {config.trading.take_profit_percent}%</Label>
                    <Input
                      id="take-profit"
                      type="range"
                      min="0.5"
                      max="20"
                      step="0.1"
                      value={config.trading.take_profit_percent}
                      onChange={(e) => updateConfig(['trading', 'take_profit_percent'], parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Automatically sell if price rises by this %. 3% = sell if up 3%. Locks in profits.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="max-risk">Max Risk Per Trade: {config.trading.max_risk_per_trade}%</Label>
                    <Input
                      id="max-risk"
                      type="range"
                      min="0.5"
                      max="10"
                      step="0.1"
                      value={config.trading.max_risk_per_trade}
                      onChange={(e) => updateConfig(['trading', 'max_risk_per_trade'], parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Maximum % of portfolio to risk on a single trade. 2% = never risk more than 2% per trade.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="max-leverage">Max Leverage: {config.trading.max_leverage}x</Label>
                    <Input
                      id="max-leverage"
                      type="number"
                      min="1"
                      max="100"
                      step="1"
                      value={config.trading.max_leverage}
                      onChange={(e) => updateConfig(['trading', 'max_leverage'], parseFloat(e.target.value))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Maximum leverage allowed. 10x = can trade 10x your balance. Higher = more risk and reward.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="min-confidence">Min Confidence: {config.trading.min_confidence_threshold}</Label>
                    <Input
                      id="min-confidence"
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={config.trading.min_confidence_threshold}
                      onChange={(e) => updateConfig(['trading', 'min_confidence_threshold'], parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      AI must be this confident (0-1) to make a trade. 0.6 = 60% confidence required. Higher = fewer but more certain trades.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="positions" className="space-y-4 mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Position Management</CardTitle>
                  <CardDescription>How the bot manages open positions</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="max-positions">Max Active Positions</Label>
                    <Input
                      id="max-positions"
                      type="number"
                      min="1"
                      max="20"
                      value={config.trading.max_active_positions}
                      onChange={(e) => updateConfig(['trading', 'max_active_positions'], parseInt(e.target.value))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Maximum number of simultaneous trades. 6 = can hold up to 6 positions at once. More = more diversified but more complex.
                    </p>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="enable-monitoring">Enable Position Monitoring</Label>
                      <p className="text-xs text-muted-foreground">
                        Automatically check and manage open positions
                      </p>
                    </div>
                    <Switch
                      id="enable-monitoring"
                      checked={config.position_management.enable_position_monitoring}
                      onCheckedChange={(checked) => updateConfig(['position_management', 'enable_position_monitoring'], checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="enable-trailing">Enable Trailing Stop Loss</Label>
                      <p className="text-xs text-muted-foreground">
                        Stop loss moves up as price rises (locks in profits)
                      </p>
                    </div>
                    <Switch
                      id="enable-trailing"
                      checked={config.position_management.enable_trailing_stop_loss}
                      onCheckedChange={(checked) => updateConfig(['position_management', 'enable_trailing_stop_loss'], checked)}
                    />
                  </div>

                  {config.position_management.enable_trailing_stop_loss && (
                    <div className="space-y-2">
                      <Label htmlFor="trailing-distance">Trailing Stop Distance: {config.position_management.trailing_stop_distance_pct}%</Label>
                      <Input
                        id="trailing-distance"
                        type="range"
                        min="0.1"
                        max="5"
                        step="0.1"
                        value={config.position_management.trailing_stop_distance_pct}
                        onChange={(e) => updateConfig(['position_management', 'trailing_stop_distance_pct'], parseFloat(e.target.value))}
                        className="w-full"
                      />
                      <p className="text-xs text-muted-foreground">
                        How far below peak price to set stop loss. 1% = stop loss stays 1% below highest price reached.
                      </p>
                    </div>
                  )}

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="enable-partial">Enable Partial Profit Taking</Label>
                      <p className="text-xs text-muted-foreground">
                        Sell part of position at first profit target, keep rest for more gains
                      </p>
                    </div>
                    <Switch
                      id="enable-partial"
                      checked={config.position_management.enable_partial_profit_taking}
                      onCheckedChange={(checked) => updateConfig(['position_management', 'enable_partial_profit_taking'], checked)}
                    />
                  </div>

                  {config.position_management.enable_partial_profit_taking && (
                    <>
                      <div className="space-y-2">
                        <Label htmlFor="partial-target">Partial Profit Target: {config.position_management.partial_profit_target_pct}%</Label>
                        <Input
                          id="partial-target"
                          type="range"
                          min="0.5"
                          max="10"
                          step="0.1"
                          value={config.position_management.partial_profit_target_pct}
                          onChange={(e) => updateConfig(['position_management', 'partial_profit_target_pct'], parseFloat(e.target.value))}
                          className="w-full"
                        />
                        <p className="text-xs text-muted-foreground">
                          When to take partial profits. 1.5% = sell part when up 1.5%.
                        </p>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="partial-percent">Sell % at Target: {config.position_management.partial_profit_percent}%</Label>
                        <Input
                          id="partial-percent"
                          type="range"
                          min="10"
                          max="90"
                          step="5"
                          value={config.position_management.partial_profit_percent}
                          onChange={(e) => updateConfig(['position_management', 'partial_profit_percent'], parseFloat(e.target.value))}
                          className="w-full"
                        />
                        <p className="text-xs text-muted-foreground">
                          How much of position to sell at target. 50% = sell half, keep half for more gains.
                        </p>
                      </div>
                    </>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="portfolio-target">Portfolio Profit Target: {config.position_management.portfolio_profit_target_pct}%</Label>
                    <Input
                      id="portfolio-target"
                      type="range"
                      min="5"
                      max="50"
                      step="1"
                      value={config.position_management.portfolio_profit_target_pct}
                      onChange={(e) => updateConfig(['position_management', 'portfolio_profit_target_pct'], parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Close all positions when total portfolio profit reaches this %. 10% = cash out everything when up 10%.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="exchange" className="space-y-4 mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Exchange Configuration</CardTitle>
                  <CardDescription>Which exchange and trading pair to use</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="exchange-name">Exchange</Label>
                    <Select
                      value={config.exchange.name}
                      onValueChange={(value) => updateConfig(['exchange', 'name'], value)}
                    >
                      <SelectTrigger id="exchange-name">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="kraken">Kraken</SelectItem>
                        <SelectItem value="bybit">Bybit</SelectItem>
                        <SelectItem value="binance">Binance</SelectItem>
                        <SelectItem value="coinbase">Coinbase</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Which cryptocurrency exchange to trade on. Kraken is US-friendly.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="symbol">Trading Pair</Label>
                    <Input
                      id="symbol"
                      value={config.exchange.symbol}
                      onChange={(e) => updateConfig(['exchange', 'symbol'], e.target.value)}
                      placeholder="BTC/USDT"
                    />
                    <p className="text-xs text-muted-foreground">
                      Which cryptocurrency pair to trade. BTC/USDT = Bitcoin vs US Dollar Tether.
                    </p>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="use-testnet">Use Testnet</Label>
                      <p className="text-xs text-muted-foreground">
                        Use testnet environment (if available) for safer testing
                      </p>
                    </div>
                    <Switch
                      id="use-testnet"
                      checked={config.exchange.use_testnet}
                      onCheckedChange={(checked) => updateConfig(['exchange', 'use_testnet'], checked)}
                    />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <DialogFooter className="flex items-center justify-between sm:justify-between">
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={loadDefaultConfig}
              disabled={saving}
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Reset to Default
            </Button>
            <Button
              variant="outline"
              onClick={() => setHistoryOpen(true)}
              disabled={saving}
            >
              <History className="h-4 w-4 mr-2" />
              View History
            </Button>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={saving}
            >
              <X className="h-4 w-4 mr-2" />
              Cancel
            </Button>
            <Button
              onClick={() => handleSave(true)}
              disabled={saving}
            >
              <Save className="h-4 w-4 mr-2" />
              {saving ? 'Saving...' : 'Save & Activate'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
      <ConfigHistoryDialog open={historyOpen} onOpenChange={setHistoryOpen} />
    </Dialog>
  );
}

