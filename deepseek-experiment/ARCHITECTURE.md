# 🏗️ System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ALPHA ARENA TRADING BOT                              │
│                                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   MARKET    │    │  PORTFOLIO  │    │     LLM     │    │  TRADING    │     │
│  │   DATA      │───▶│    STATE    │───▶│   CLIENT    │───▶│  ENGINE     │     │
│  │  FETCHER    │    │ CALCULATOR  │    │             │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                   │                   │         │
│         │                   │                   │                   ▼         │
│         │                   │                   │            ┌─────────────┐   │
│         │                   │                   │            │  POSITION   │   │
│         │                   │                   │            │  MANAGER    │   │
│         │                   │                   │            └─────────────┘   │
│         │                   │                   │                   │         │
│         │                   │                   │                   ▼         │
│         │                   │                   │            ┌─────────────┐   │
│         │                   │                   │            │    RISK     │   │
│         │                   │                   │            │  MANAGER    │   │
│         │                   │                   │            └─────────────┘   │
│         │                   │                   │                   │         │
│         │                   │                   │                   ▼         │
│         │                   │                   │            ┌─────────────┐   │
│         │                   │                   │            │BEHAVIORAL   │   │
│         │                   │                   │            │  TRACKER    │   │
│         │                   │                   │            └─────────────┘   │
│         │                   │                   │                   │         │
│         │                   │                   │                   ▼         │
│         │                   │                   │            ┌─────────────┐   │
│         │                   │                   │            │PERFORMANCE  │   │
│         │                   │                   │            │  MONITOR    │   │
│         │                   │                   │            └─────────────┘   │
│         │                   │                   │                   │         │
│         │                   │                   │                   ▼         │
│         │                   │                   │            ┌─────────────┐   │
│         │                   │                   │            │   WEB       │   │
│         │                   │                   │            │ DASHBOARD   │   │
│         │                   │                   │            └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Trading Loop Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TRADING CYCLE (2.5 min)                          │
│                                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   1. FETCH  │    │   2. CALC   │    │   3. LLM    │    │   4. EXEC   │     │
│  │  MARKET     │───▶│ PORTFOLIO   │───▶│ DECISION    │───▶│   TRADE     │     │
│  │   DATA      │    │   METRICS   │    │ GENERATION  │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                   │                   │         │
│         │                   │                   │                   ▼         │
│         │                   │                   │            ┌─────────────┐   │
│         │                   │                   │            │   5. UPDATE │   │
│         │                   │                   │            │  BEHAVIORAL │   │
│         │                   │                   │            │   METRICS   │   │
│         │                   │                   │            └─────────────┘   │
│         │                   │                   │                   │         │
│         │                   │                   │                   ▼         │
│         │                   │                   │            ┌─────────────┐   │
│         │                   │                   │            │   6. WAIT   │   │
│         │                   │                   │            │  NEXT CYCLE │   │
│         │                   │                   │            └─────────────┘   │
│         │                   │                   │                   │         │
│         │                   │                   │                   ▼         │
│         │                   │                   │            ┌─────────────┐   │
│         │                   │                   │            │   REPEAT    │   │
│         │                   │                   │            │   CYCLE     │   │
│         │                   │                   │            └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Alpha Arena Features

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            ALPHA ARENA FEATURES                               │
│                                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   SHARPE    │    │  LEVERAGE   │    │    SHORT    │    │   EXIT      │     │
│  │   RATIO     │    │   SUPPORT   │    │  SELLING    │    │   PLANS     │     │
│  │ FEEDBACK    │    │             │    │             │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                   │                   │         │
│         │                   │                   │                   │         │
│         ▼                   ▼                   ▼                   ▼         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │    FEE      │    │   RISK      │    │  POSITION   │    │  BEHAVIORAL │     │
│  │ AWARENESS   │    │ MANAGEMENT  │    │   LIMITS    │    │  TRACKING   │     │
│  │             │    │             │    │             │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Behavioral Pattern Tracking

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         BEHAVIORAL PATTERN TRACKING                           │
│                                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   BULLISH   │    │   HOLDING   │    │    TRADE    │    │  POSITION   │     │
│  │    TILT     │    │  PERIODS    │    │ FREQUENCY   │    │   SIZING    │     │
│  │             │    │             │    │             │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                   │                   │         │
│         │                   │                   │                   │         │
│         ▼                   ▼                   ▼                   ▼         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ CONFIDENCE  │    │   EXIT      │    │   ACTIVE    │    │  INVALIDATION│     │
│  │   LEVELS    │    │   PLAN      │    │ POSITIONS   │    │ CONDITIONS  │     │
│  │             │    │ TIGHTNESS   │    │             │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                DATA FLOW                                       │
│                                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   MARKET    │    │  PORTFOLIO  │    │     LLM     │    │  TRADING    │     │
│  │   DATA      │───▶│    STATE    │───▶│   PROMPT    │───▶│ DECISION    │     │
│  │             │    │             │    │             │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                   │                   │         │
│         │                   │                   │                   ▼         │
│         │                   │                   │            ┌─────────────┐   │
│         │                   │                   │            │  VALIDATION │   │
│         │                   │                   │            │   & RISK    │   │
│         │                   │                   │            │  CHECKING   │   │
│         │                   │                   │            └─────────────┘   │
│         │                   │                   │                   │         │
│         │                   │                   │                   ▼         │
│         │                   │                   │            ┌─────────────┐   │
│         │                   │                   │            │  EXECUTION  │   │
│         │                   │                   │            │   & TRADE   │   │
│         │                   │                   │            │  RECORDING  │   │
│         │                   │                   │            └─────────────┘   │
│         │                   │                   │                   │         │
│         │                   │                   │                   ▼         │
│         │                   │                   │            ┌─────────────┐   │
│         │                   │                   │            │  BEHAVIORAL │   │
│         │                   │                   │            │   UPDATE    │   │
│         │                   │                   │            │   & FEEDBACK│   │
│         │                   │                   │            └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Market Data Fetcher
- Fetches real-time cryptocurrency prices
- Retrieves 24h volume and change data
- Provides clean, structured market data

### Portfolio State Calculator
- Calculates current portfolio value
- Tracks open positions and balances
- Computes performance metrics (Sharpe ratio, volatility, etc.)
- Updates behavioral pattern metrics

### LLM Client
- Formats market data and portfolio state into prompts
- Handles multiple LLM providers (DeepSeek, OpenAI, Anthropic)
- Validates and parses LLM responses
- Provides fallback mechanisms for API failures

### Trading Engine
- Executes buy/sell/short orders
- Manages leverage and margin calculations
- Handles position tracking and PnL calculations
- Enforces risk limits and position constraints

### Risk Manager
- Validates trade decisions against risk limits
- Checks position limits and margin requirements
- Monitors fee impact and over-trading
- Enforces stop-loss and take-profit rules

### Behavioral Tracker
- Monitors trading patterns and behaviors
- Tracks bullish/bearish tilt
- Calculates holding periods and trade frequency
- Analyzes confidence levels and position sizing

### Performance Monitor
- Displays real-time trading dashboard
- Generates performance reports
- Tracks key metrics and KPIs
- Provides behavioral pattern insights

## Configuration Management

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CONFIGURATION LAYERS                               │
│                                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ ENVIRONMENT │    │   CONFIG    │    │   RUNTIME   │    │   COMMAND   │     │
│  │ VARIABLES   │───▶│    FILE     │───▶│  DEFAULTS   │───▶│   LINE      │     │
│  │             │    │             │    │             │    │  ARGUMENTS  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                   │                   │         │
│         │                   │                   │                   │         │
│         ▼                   ▼                   ▼                   ▼         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   LLM       │    │   TRADING   │    │  BEHAVIORAL │    │    RISK     │     │
│  │  SETTINGS   │    │  PARAMETERS │    │  SIMULATION │    │ MANAGEMENT  │     │
│  │             │    │             │    │             │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

This architecture provides a robust, scalable foundation for the Alpha Arena trading bot with comprehensive behavioral tracking and risk management capabilities.
