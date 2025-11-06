import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Separator } from './ui/separator';
import mermaid from 'mermaid';

export function DocumentationPage() {
  const mermaidRef1 = useRef<HTMLDivElement>(null);
  const mermaidRef2 = useRef<HTMLDivElement>(null);
  const mermaidRef3 = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mermaid.initialize({ 
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
    });

    const renderDiagrams = async () => {
      if (mermaidRef1.current) {
        const diagram1 = `graph TB
    A[Market Data Fetcher] --> B[Portfolio State Calculator]
    B --> C[LLM Client]
    C --> D[Decision Validator]
    D --> E[Trading Engine]
    E --> F[Position Manager]
    F --> G[Risk Manager]
    G --> H[Behavioral Tracker]
    H --> I[Performance Monitor]

    subgraph "Alpha Arena Features"
        J[Sharpe Ratio Feedback]
        K[Leverage Support]
        L[Short Selling]
        M[Exit Plans]
        N[Fee Awareness]
    end

    subgraph "Behavioral Patterns"
        O[Bullish Tilt Tracking]
        P[Holding Period Analysis]
        Q[Trade Frequency Monitoring]
        R[Position Sizing Patterns]
        S[Confidence Analysis]
    end

    C --> J
    E --> K
    E --> L
    D --> M
    E --> N

    H --> O
    H --> P
    H --> Q
    H --> R
    H --> S`;
        
        try {
          const { svg } = await mermaid.render('diagram1', diagram1);
          mermaidRef1.current.innerHTML = svg;
        } catch (e) {
          console.error('Error rendering diagram 1:', e);
        }
      }

      if (mermaidRef2.current) {
        const diagram2 = `sequenceDiagram
    participant M as Market Data
    participant P as Portfolio State
    participant L as LLM Client
    participant T as Trading Engine
    participant R as Risk Manager
    participant B as Behavioral Tracker

    M->>P: Fetch current price & volume
    P->>L: Calculate portfolio metrics
    L->>L: Generate trading decision
    L->>T: Validate decision format
    T->>R: Check risk limits
    R->>T: Approve/reject trade
    T->>B: Execute trade & update metrics
    B->>P: Update behavioral patterns
    P->>L: Provide feedback for next cycle`;
        
        try {
          const { svg } = await mermaid.render('diagram2', diagram2);
          mermaidRef2.current.innerHTML = svg;
        } catch (e) {
          console.error('Error rendering diagram 2:', e);
        }
      }

      if (mermaidRef3.current) {
        const diagram3 = `flowchart LR
    A[Market Data] --> B[Technical Indicators]
    B --> C[Portfolio State]
    C --> D[LLM Analysis]
    D --> E{Decision}
    E -->|Buy| F[Risk Check]
    E -->|Sell| F
    E -->|Hold| G[Wait Next Cycle]
    F --> H{Approved?}
    H -->|Yes| I[Execute Trade]
    H -->|No| G
    I --> J[Update Positions]
    J --> K[Track Behavior]
    K --> G`;
        
        try {
          const { svg } = await mermaid.render('diagram3', diagram3);
          mermaidRef3.current.innerHTML = svg;
        } catch (e) {
          console.error('Error rendering diagram 3:', e);
        }
      }
    };

    renderDiagrams();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img 
                src="/logos/DeepSeek_logo.svg" 
                alt="DeepSeek Logo" 
                className="h-8 w-8"
              />
              <h1 className="text-2xl font-semibold tracking-tight">Project Documentation</h1>
            </div>
            <Link
              to="/"
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-foreground hover:text-primary transition-colors border border-border rounded-md hover:border-primary"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-5xl">
        <div className="space-y-6">
          {/* Section 1: Overview */}
          <Card>
            <CardHeader>
              <CardTitle>1. Overview</CardTitle>
              <CardDescription>High-level project description and capabilities</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm leading-7">
                This is an <strong>Alpha Arena Trading Bot</strong> - a sophisticated cryptocurrency trading system 
                that uses Large Language Models (LLMs) to make autonomous trading decisions. The bot simulates 
                the <a href="https://nof1.ai/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-medium">Alpha Arena</a> competition methodology where AI agents are given $10,000 to trade perpetual 
                futures with zero human intervention.
              </p>
              
              <div>
                <h3 className="text-base font-semibold mb-2">Key Features</h3>
                <ul className="list-disc list-inside space-y-2 text-muted-foreground">
                  <li><strong>Autonomous Trading:</strong> Fully automated decision-making using LLMs</li>
                  <li><strong>Leverage Support:</strong> Up to 10x leverage on perpetual futures</li>
                  <li><strong>Risk Management:</strong> Built-in position limits, stop losses, and margin requirements</li>
                  <li><strong>Behavioral Tracking:</strong> Comprehensive pattern analysis (bullish tilt, holding periods, confidence levels)</li>
                  <li><strong>Real-time Monitoring:</strong> Live dashboard with portfolio tracking and trade history</li>
                  <li><strong>Regime Detection:</strong> Adaptive strategy selection based on market conditions</li>
                  <li><strong>Fee Awareness:</strong> Intelligent fee management to prevent over-trading</li>
                </ul>
              </div>

              <div>
                <h3 className="text-base font-semibold mb-2">Technology Stack</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
                  <div className="p-2 bg-muted rounded">
                    <strong>Backend:</strong> Python, FastAPI
                  </div>
                  <div className="p-2 bg-muted rounded">
                    <strong>Frontend:</strong> React, TypeScript, Vite
                  </div>
                  <div className="p-2 bg-muted rounded">
                    <strong>LLM:</strong> DeepSeek, OpenAI, Anthropic
                  </div>
                  <div className="p-2 bg-muted rounded">
                    <strong>Database:</strong> Supabase (PostgreSQL)
                  </div>
                  <div className="p-2 bg-muted rounded">
                    <strong>Exchange:</strong> Kraken API
                  </div>
                  <div className="p-2 bg-muted rounded">
                    <strong>UI:</strong> Radix UI, Tailwind CSS
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 2: Who am I */}
          <Card>
            <CardHeader>
              <CardTitle>2. Who am I</CardTitle>
              <CardDescription>About the creator</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="text-base font-semibold mb-3 text-foreground">
                  AI-First Product Manager | 0→1 → Scale | Unlocking User & Business Value with Modern Product and GenAI Methods
                </h3>
                <p className="text-sm leading-7 text-muted-foreground">
                  Hi! I'm <strong className="text-foreground">Sushant Chhetry</strong>, the creator of this LLM-powered trading bot project. 
                  I specialize in building and scaling products at the intersection of AI and real-world user problems.
                </p>
              </div>

              <div>
                <h4 className="text-sm font-semibold mb-2 text-foreground">What makes me different</h4>
                <p className="text-sm leading-7 text-muted-foreground">
                  I blend classical product rigor (discovery, prioritization, clear roadmaps) with hands-on AI prototyping and rapid experimentation. 
                  At SmartWiz, I architected modular GenAI solutions that empowered teams to ship faster and validate features with real users—cutting 
                  prototyping time by <strong className="text-foreground">3x</strong> and reducing onboarding friction by <strong className="text-foreground">40%</strong>.
                </p>
                <p className="text-sm leading-7 text-muted-foreground mt-3">
                  I've led <strong className="text-foreground">50+ user interviews</strong>, run iterative design partner programs, and orchestrated beta launches 
                  that moved metrics (activation, retention, TTFT). My superpower? Translating messy feedback and ambiguous "AI opportunity" into clear 
                  product wins—always putting user value first but leveraging the best of what GenAI brings.
                </p>
                <p className="text-sm leading-7 text-muted-foreground mt-3">
                  I work best in teams obsessed with impact, data, and velocity, where AI is not just a badge but a business driver.
                </p>
              </div>

              <div>
                <h4 className="text-sm font-semibold mb-3 text-foreground">Core strengths</h4>
                <ul className="list-disc list-inside space-y-2 text-sm text-muted-foreground">
                  <li>Zero-to-one product launches in AI/B2B SaaS</li>
                  <li>User research and signal-to-bets prioritization</li>
                  <li>Modular GenAI integration (prompting, RAG, LLM evals)</li>
                  <li>Metrics-driven iteration and GTM collaboration</li>
                </ul>
              </div>

              <div className="p-4 bg-muted rounded-lg border border-border">
                <p className="text-sm leading-7 text-muted-foreground">
                  <strong className="text-foreground">Actively open to:</strong> Senior PM/Product Lead roles in high-growth SaaS, AI/ML, or B2B startups.
                </p>
                <p className="text-sm leading-7 text-muted-foreground mt-2 italic">
                  Let's accelerate product impact in the AI era. DM or connect if you're building!
                </p>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <a
                  href="https://www.linkedin.com/in/sushantchhetry/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors font-medium text-sm"
                >
                  Connect on LinkedIn
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>
            </CardContent>
          </Card>

          {/* Section 3: What are we trying to achieve */}
          <Card>
            <CardHeader>
              <CardTitle>3. What are we trying to achieve</CardTitle>
              <CardDescription>Project goals and objectives</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="text-base font-semibold mb-2">Primary Objectives</h3>
                <ul className="list-disc list-inside space-y-2 text-muted-foreground">
                  <li><strong>Maximize PnL:</strong> The bot's primary goal is to generate consistent profits through systematic trading</li>
                  <li><strong>Zero Human Intervention:</strong> Fully autonomous operation following <a href="https://nof1.ai/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">Alpha Arena</a> methodology</li>
                  <li><strong>Quantitative Analysis Only:</strong> Decisions based purely on numerical data - no news or narratives</li>
                  <li><strong>Risk-Adjusted Returns:</strong> Optimize for Sharpe ratio, not just raw profits</li>
                  <li><strong>Behavioral Pattern Learning:</strong> Track and adapt trading style based on performance</li>
                </ul>
              </div>

              <div>
                <h3 className="text-base font-semibold mb-2">
                  <a href="https://nof1.ai/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">Alpha Arena</a> Methodology
                </h3>
                <p className="text-sm leading-7 text-muted-foreground mb-2">
                  The bot implements the <a href="https://nof1.ai/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-medium">Alpha Arena</a> competition framework:
                </p>
                <ul className="list-disc list-inside space-y-2 text-muted-foreground">
                  <li><strong>$10,000 Starting Capital:</strong> Simulated trading account</li>
                  <li><strong>2.5-minute Trading Cycles:</strong> Regular decision-making intervals</li>
                  <li><strong>Perpetual Futures:</strong> Trade with leverage on crypto perpetuals</li>
                  <li><strong>Structured Decision Format:</strong> LLM outputs JSON with action, confidence, reasoning, and exit plans</li>
                  <li><strong>Comprehensive Feedback:</strong> Sharpe ratio, behavioral metrics, and performance tracking</li>
                </ul>
              </div>

              <div>
                <h3 className="text-base font-semibold mb-2">Research Goals</h3>
                <p className="text-sm leading-7 text-muted-foreground">
                  This project serves as a research platform to understand:
                </p>
                <ul className="list-disc list-inside space-y-2 text-muted-foreground mt-2">
                  <li>How LLMs perform in quantitative trading scenarios</li>
                  <li>Behavioral patterns in AI-driven trading systems</li>
                  <li>Cost-effectiveness of different LLM providers for trading</li>
                  <li>Adaptive strategy selection based on market regimes</li>
                  <li>Risk management effectiveness in autonomous systems</li>
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Section 4: Under the hood */}
          <Card>
            <CardHeader>
              <CardTitle>4. Under the hood</CardTitle>
              <CardDescription>System architecture and data flow</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="text-base font-semibold mb-4">System Architecture</h3>
                <div ref={mermaidRef1} className="flex justify-center bg-muted/50 p-4 rounded-lg overflow-x-auto"></div>
              </div>

              <Separator />

              <div>
                <h3 className="text-base font-semibold mb-4">Trading Loop Sequence</h3>
                <div ref={mermaidRef2} className="flex justify-center bg-muted/50 p-4 rounded-lg overflow-x-auto"></div>
              </div>

              <Separator />

              <div>
                <h3 className="text-base font-semibold mb-4">Decision Flow</h3>
                <div ref={mermaidRef3} className="flex justify-center bg-muted/50 p-4 rounded-lg overflow-x-auto"></div>
              </div>

              <div>
                <h3 className="text-base font-semibold mb-2">Key Components</h3>
                <div className="space-y-3 text-sm">
                  <div className="p-3 bg-muted rounded">
                    <strong>Market Data Fetcher:</strong> Retrieves real-time prices, volume, and technical indicators from exchange APIs
                  </div>
                  <div className="p-3 bg-muted rounded">
                    <strong>Portfolio State Calculator:</strong> Tracks balance, positions, PnL, Sharpe ratio, and behavioral metrics
                  </div>
                  <div className="p-3 bg-muted rounded">
                    <strong>LLM Client:</strong> Formats prompts and processes trading decisions from language models
                  </div>
                  <div className="p-3 bg-muted rounded">
                    <strong>Trading Engine:</strong> Executes trades, manages positions, calculates margins and leverage
                  </div>
                  <div className="p-3 bg-muted rounded">
                    <strong>Risk Manager:</strong> Validates trades against risk limits, position constraints, and margin requirements
                  </div>
                  <div className="p-3 bg-muted rounded">
                    <strong>Behavioral Tracker:</strong> Monitors trading patterns, confidence levels, and style metrics
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 5: How does the bot make the trade */}
          <Card>
            <CardHeader>
              <CardTitle>5. How does the bot make the trade</CardTitle>
              <CardDescription>Step-by-step trading cycle explanation</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="text-base font-semibold mb-3">Trading Cycle (Every 2.5 minutes)</h3>
                <ol className="list-decimal list-inside space-y-3 text-muted-foreground">
                  <li>
                    <strong>Fetch Market Data:</strong> The bot retrieves current price, 24h volume, and change percentage 
                    from the exchange. It also fetches technical indicators including EMA (20, 50), MACD, RSI (7, 14), 
                    ATR, and market regime information.
                  </li>
                  <li>
                    <strong>Calculate Portfolio State:</strong> The system computes current portfolio value, total return, 
                    Sharpe ratio, volatility, drawdown, and all behavioral metrics (bullish tilt, holding periods, etc.).
                  </li>
                  <li>
                    <strong>Format LLM Prompt:</strong> Market data, portfolio state, technical indicators, and trading 
                    parameters are formatted into a structured prompt. The prompt includes risk management guidelines, 
                    fee awareness, and <a href="https://nof1.ai/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">Alpha Arena</a> objectives.
                  </li>
                  <li>
                    <strong>LLM Decision Generation:</strong> The language model analyzes all the data and generates a 
                    JSON response with:
                    <ul className="list-disc list-inside ml-6 mt-2 space-y-1">
                      <li>Action (buy/sell/hold)</li>
                      <li>Direction (long/short/none)</li>
                      <li>Confidence (0.0-1.0)</li>
                      <li>Position size in USDT</li>
                      <li>Leverage (1x-10x)</li>
                      <li>Exit plan (profit target and stop loss)</li>
                      <li>Justification (reasoning)</li>
                    </ul>
                  </li>
                  <li>
                    <strong>Decision Validation:</strong> The bot validates the JSON format, checks that confidence 
                    meets minimum threshold (0.6), and ensures the decision structure is correct.
                  </li>
                  <li>
                    <strong>Risk Management Check:</strong> Before execution, the system verifies:
                    <ul className="list-disc list-inside ml-6 mt-2 space-y-1">
                      <li>Position limits (max 6 active positions)</li>
                      <li>Margin requirements (sufficient balance)</li>
                      <li>Leverage limits (1x-10x)</li>
                      <li>Position size limits (max 10% of balance per trade)</li>
                      <li>Funding/carry costs (avoid trades when costs exceed expected edge)</li>
                    </ul>
                  </li>
                  <li>
                    <strong>Trade Execution:</strong> If approved, the bot executes the trade:
                    <ul className="list-disc list-inside ml-6 mt-2 space-y-1">
                      <li>Calculates required margin (position_size / leverage)</li>
                      <li>Updates balance (deducts margin, not full notional)</li>
                      <li>Creates or updates position entry</li>
                      <li>Records trade with timestamp, price, size, leverage</li>
                      <li>Applies trading fees (0.05% taker fee)</li>
                    </ul>
                  </li>
                  <li>
                    <strong>Position Management:</strong> The system monitors open positions:
                    <ul className="list-disc list-inside ml-6 mt-2 space-y-1">
                      <li>Checks exit conditions (profit targets, stop losses)</li>
                      <li>Calculates unrealized PnL</li>
                      <li>Monitors liquidation risk</li>
                      <li>Updates position values in real-time</li>
                    </ul>
                  </li>
                  <li>
                    <strong>Behavioral Tracking Update:</strong> After each cycle, the bot updates:
                    <ul className="list-disc list-inside ml-6 mt-2 space-y-1">
                      <li>Bullish/bearish tilt ratio</li>
                      <li>Average holding periods</li>
                      <li>Trade frequency</li>
                      <li>Confidence distribution</li>
                      <li>Position sizing patterns</li>
                      <li>Fee impact on PnL</li>
                    </ul>
                  </li>
                  <li>
                    <strong>Feedback Loop:</strong> All metrics are fed back into the next cycle's prompt, 
                    allowing the LLM to learn from past performance and adapt its strategy.
                  </li>
                </ol>
              </div>

              <Separator />

              <div>
                <h3 className="text-base font-semibold mb-2">Risk Management Integration</h3>
                <p className="text-sm leading-7 text-muted-foreground">
                  Risk management is integrated at multiple levels:
                </p>
                <ul className="list-disc list-inside space-y-2 text-muted-foreground mt-2">
                  <li><strong>Pre-trade:</strong> Position limits, margin checks, leverage validation</li>
                  <li><strong>During trade:</strong> Stop losses, profit targets, position monitoring</li>
                  <li><strong>Post-trade:</strong> Fee impact analysis, behavioral pattern tracking, Sharpe ratio feedback</li>
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Section 6: Why use LLM */}
          <Card>
            <CardHeader>
              <CardTitle>6. Why use LLM</CardTitle>
              <CardDescription>Advantages of LLM-based trading decisions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="text-base font-semibold mb-2">Key Advantages</h3>
                <ul className="list-disc list-inside space-y-2 text-muted-foreground">
                  <li>
                    <strong>Flexibility:</strong> LLMs can adapt to different market regimes (trending, mean-reverting, choppy) 
                    without hardcoded rules. They can reason about complex relationships between indicators.
                  </li>
                  <li>
                    <strong>Contextual Understanding:</strong> Language models can process and reason about multiple data 
                    points simultaneously - price, volume, technical indicators, portfolio state, and behavioral patterns.
                  </li>
                  <li>
                    <strong>Natural Language Reasoning:</strong> LLMs can explain their decisions, making it easier to 
                    understand and debug trading behavior. The justification field provides transparency.
                  </li>
                  <li>
                    <strong>Adaptive Learning:</strong> Through feedback loops (Sharpe ratio, behavioral metrics), LLMs 
                    can adjust their strategy over time without explicit reprogramming.
                  </li>
                  <li>
                    <strong>Complex Pattern Recognition:</strong> LLMs excel at identifying non-linear patterns and 
                    relationships that might be difficult to encode in traditional algorithms.
                  </li>
                  <li>
                    <strong>Multi-factor Analysis:</strong> Can simultaneously consider dozens of factors (indicators, 
                    metrics, patterns) and weigh their importance contextually.
                  </li>
                </ul>
              </div>

              <Separator />

              <div>
                <h3 className="text-base font-semibold mb-2">Comparison with Traditional Algorithms</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border-collapse">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left p-2 font-medium">Aspect</th>
                        <th className="text-left p-2 font-medium">Traditional Algorithms</th>
                        <th className="text-left p-2 font-medium">LLM-Based</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-border">
                        <td className="p-2">Rule Definition</td>
                        <td className="p-2 text-muted-foreground">Hardcoded, explicit rules</td>
                        <td className="p-2 text-muted-foreground">Natural language instructions, flexible</td>
                      </tr>
                      <tr className="border-b border-border">
                        <td className="p-2">Adaptability</td>
                        <td className="p-2 text-muted-foreground">Requires reprogramming for changes</td>
                        <td className="p-2 text-muted-foreground">Adapts through prompt engineering</td>
                      </tr>
                      <tr className="border-b border-border">
                        <td className="p-2">Complex Patterns</td>
                        <td className="p-2 text-muted-foreground">Limited to predefined patterns</td>
                        <td className="p-2 text-muted-foreground">Can identify novel patterns</td>
                      </tr>
                      <tr className="border-b border-border">
                        <td className="p-2">Explainability</td>
                        <td className="p-2 text-muted-foreground">Black box or complex logic</td>
                        <td className="p-2 text-muted-foreground">Natural language justifications</td>
                      </tr>
                      <tr>
                        <td className="p-2">Cost</td>
                        <td className="p-2 text-muted-foreground">Low (compute only)</td>
                        <td className="p-2 text-muted-foreground">Low-Medium (~$0.03/day with DeepSeek)</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="text-base font-semibold mb-2">Cost Analysis</h3>
                <p className="text-sm leading-7 text-muted-foreground mb-3">
                  Running the bot with different LLM providers (based on 288 cycles/day):
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="p-3 bg-muted rounded">
                    <strong>DeepSeek</strong>
                    <div className="text-sm mt-1">~$0.03/day</div>
                    <div className="text-xs text-muted-foreground">Recommended</div>
                  </div>
                  <div className="p-3 bg-muted rounded">
                    <strong>GPT-3.5</strong>
                    <div className="text-sm mt-1">~$0.13/day</div>
                    <div className="text-xs text-muted-foreground">Good balance</div>
                  </div>
                  <div className="p-3 bg-muted rounded">
                    <strong>GPT-4</strong>
                    <div className="text-sm mt-1">~$0.80/day</div>
                    <div className="text-xs text-muted-foreground">Best reasoning</div>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground mt-3">
                  DeepSeek offers 27x cost savings compared to GPT-4 while providing comparable performance 
                  for structured trading decisions.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Section 7: Limitations and Considerations */}
          <Card>
            <CardHeader>
              <CardTitle>7. Limitations and Considerations</CardTitle>
              <CardDescription>Understanding the trade-offs and challenges of LLM-based trading</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm leading-7 text-muted-foreground">
                While LLMs offer significant advantages for trading, it's important to understand their limitations 
                and the considerations that come with using them in a financial context.
              </p>

              <div>
                <h3 className="text-base font-semibold mb-3">Key Limitations</h3>
                <div className="space-y-4">
                  <div className="p-4 bg-muted rounded-lg border border-border">
                    <h4 className="font-semibold mb-2 text-foreground">Non-Deterministic Behavior</h4>
                    <p className="text-sm text-muted-foreground">
                      LLMs can produce different outputs for the same input, making it challenging to achieve 
                      perfectly reproducible results. This variability requires robust validation and fallback 
                      mechanisms to ensure consistent trading behavior.
                    </p>
                  </div>

                  <div className="p-4 bg-muted rounded-lg border border-border">
                    <h4 className="font-semibold mb-2 text-foreground">Latency and Response Time</h4>
                    <p className="text-sm text-muted-foreground">
                      API calls to LLM providers introduce latency (typically 1-5 seconds), which can be 
                      problematic in fast-moving markets. While acceptable for the 2.5-minute trading cycles 
                      used here, this may limit applicability to high-frequency trading strategies.
                    </p>
                  </div>

                  <div className="p-4 bg-muted rounded-lg border border-border">
                    <h4 className="font-semibold mb-2 text-foreground">API Dependency and Reliability</h4>
                    <p className="text-sm text-muted-foreground">
                      Trading decisions depend on external LLM API availability. Network issues, rate limits, 
                      or service outages could interrupt trading. This project includes fallback mechanisms, 
                      but complete independence from external services isn't possible.
                    </p>
                  </div>

                  <div className="p-4 bg-muted rounded-lg border border-border">
                    <h4 className="font-semibold mb-2 text-foreground">Hallucination and Incorrect Decisions</h4>
                    <p className="text-sm text-muted-foreground">
                      LLMs can "hallucinate" or generate plausible-sounding but incorrect reasoning. While 
                      structured JSON outputs and validation help mitigate this, there's always a risk of 
                      the model making a decision based on flawed logic that appears valid.
                    </p>
                  </div>

                  <div className="p-4 bg-muted rounded-lg border border-border">
                    <h4 className="font-semibold mb-2 text-foreground">Limited Backtesting Capabilities</h4>
                    <p className="text-sm text-muted-foreground">
                      Traditional algorithmic strategies can be backtested deterministically. LLM-based strategies 
                      are harder to backtest accurately because the model's responses may vary between runs, 
                      making it difficult to validate historical performance with certainty.
                    </p>
                  </div>

                  <div className="p-4 bg-muted rounded-lg border border-border">
                    <h4 className="font-semibold mb-2 text-foreground">Token Limits and Context Constraints</h4>
                    <p className="text-sm text-muted-foreground">
                      LLMs have context window limitations. While sufficient for current use cases, incorporating 
                      extensive historical data or complex multi-asset analysis may require careful prompt 
                      engineering or model selection to fit within token limits.
                    </p>
                  </div>

                  <div className="p-4 bg-muted rounded-lg border border-border">
                    <h4 className="font-semibold mb-2 text-foreground">Cost Scaling</h4>
                    <p className="text-sm text-muted-foreground">
                      While costs are reasonable at current usage levels (~$0.03/day with DeepSeek), scaling 
                      to higher-frequency trading or multiple concurrent strategies could significantly increase 
                      expenses. Traditional algorithms have minimal marginal costs once developed.
                    </p>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="text-base font-semibold mb-3">Risk Mitigation Strategies</h3>
                <p className="text-sm leading-7 text-muted-foreground mb-3">
                  This project implements several strategies to address these limitations:
                </p>
                <ul className="list-disc list-inside space-y-2 text-sm text-muted-foreground">
                  <li><strong className="text-foreground">Structured Output Validation:</strong> JSON schema validation ensures responses meet required format and constraints</li>
                  <li><strong className="text-foreground">Confidence Thresholds:</strong> Only executing trades above minimum confidence levels (0.6) filters out uncertain decisions</li>
                  <li><strong className="text-foreground">Risk Management Layer:</strong> Independent risk checks validate all trades before execution, regardless of LLM decision</li>
                  <li><strong className="text-foreground">Fallback Mechanisms:</strong> Graceful degradation when API calls fail, with hold decisions as default</li>
                  <li><strong className="text-foreground">Position Limits:</strong> Maximum position constraints prevent over-leveraging from any single decision</li>
                  <li><strong className="text-foreground">Behavioral Monitoring:</strong> Continuous tracking of trading patterns helps identify and correct problematic behaviors</li>
                  <li><strong className="text-foreground">Paper Trading First:</strong> Extensive testing in simulated environments before considering live trading</li>
                </ul>
              </div>

              <div className="p-4 bg-muted/50 rounded-lg border border-border">
                <p className="text-sm leading-7 text-muted-foreground">
                  <strong className="text-foreground">Important Note:</strong> This project is designed for research 
                  and educational purposes. LLM-based trading systems should be thoroughly tested and validated 
                  before any real capital deployment. Always start with paper trading and understand the risks 
                  involved in algorithmic trading.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Section 8: Nice to know terms */}
          <Card>
            <CardHeader>
              <CardTitle>8. Nice to know terms</CardTitle>
              <CardDescription>Glossary of trading and technical terminology</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">Leverage</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    The ability to control a larger position with a smaller amount of capital. 
                    10x leverage means controlling $10,000 with $1,000 margin.
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/l/leverage.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">Perpetual Futures</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    Derivatives contracts without an expiration date. Traders can hold positions 
                    indefinitely and trade both long (betting price goes up) and short (betting price goes down).
                  </p>
                  <a 
                    href="https://www.binance.com/en/support/faq/perpetual-futures" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">Sharpe Ratio</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    A measure of risk-adjusted return. Higher Sharpe ratio indicates better returns 
                    relative to the risk taken. Formula: (Return - Risk-free rate) / Volatility.
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/s/sharperatio.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">RSI (Relative Strength Index)</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    A momentum oscillator that measures the speed and magnitude of price changes. 
                    Values above 70 indicate overbought conditions, below 30 indicate oversold.
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/r/rsi.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">MACD (Moving Average Convergence Divergence)</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    A trend-following momentum indicator that shows the relationship between two 
                    moving averages. Positive histogram indicates bullish momentum.
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/m/macd.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">EMA (Exponential Moving Average)</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    A type of moving average that gives more weight to recent prices. EMA 20 and 
                    EMA 50 are commonly used to identify trends.
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/e/ema.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">ATR (Average True Range)</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    A volatility indicator that measures market volatility by calculating the average 
                    range of price movements over a period.
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/a/atr.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">Funding Rate</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    A periodic payment between long and short traders in perpetual futures markets. 
                    Positive rates mean longs pay shorts (bearish sentiment).
                  </p>
                  <a 
                    href="https://www.binance.com/en/support/faq/funding-rates" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">Margin</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    The collateral required to open and maintain a leveraged position. With 10x leverage, 
                    you need 10% margin (e.g., $1,000 margin for $10,000 position).
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/m/margin.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">Liquidation</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    When a leveraged position is forcibly closed because losses exceed available margin. 
                    The bot monitors liquidation risk to prevent total loss.
                  </p>
                  <a 
                    href="https://www.binance.com/en/support/faq/liquidation" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">PnL (Profit and Loss)</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    The total profit or loss from trading activities. Can be realized (closed positions) 
                    or unrealized (open positions).
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/p/plstatement.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">Drawdown</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    The peak-to-trough decline during a specific period. Maximum drawdown measures the 
                    largest loss from a peak value.
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/d/drawdown.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">Stop Loss</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    A predetermined price level at which a position is automatically closed to limit losses. 
                    The bot uses stop losses as part of its exit plans.
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/s/stop-lossorder.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">Take Profit / Profit Target</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    A predetermined price level at which a position is automatically closed to secure profits. 
                    The bot sets profit targets as part of its exit strategy.
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/t/take-profitorder.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">Volatility</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    A measure of price variability over time. Higher volatility means larger price swings. 
                    The bot tracks volatility to assess risk.
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/v/volatility.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-semibold mb-2">Market Regime</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    The current market condition (trending bullish, trending bearish, mean-reverting, or choppy). 
                    The bot adapts its strategy based on detected regime.
                  </p>
                  <a 
                    href="https://www.investopedia.com/terms/m/marketregime.asp" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t bg-card mt-12">
        <div className="container mx-auto px-4 py-6">
          <div className="text-center text-sm text-muted-foreground">
            <p>LLM Trading Bot Documentation</p>
            <p className="mt-1">Built with React, TypeScript, and Mermaid</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

