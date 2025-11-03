# ⚡ Quick Start Guide

Get your Alpha Arena Trading Bot running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

**Optional but recommended:**
- Virtual environment (venv)
- Supabase account (for database)
- DeepSeek API key (for LLM)

---

## Step 1: Clone and Install (2 minutes)

```bash
# Clone the repository
git clone https://github.com/yourusername/llm-trading-bot.git
cd llm-trading-bot/deepseek-experiment

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Basic Configuration (1 minute)

Create a `.env` file in the `deepseek-experiment` directory:

```bash
# Copy template (if available)
cp .env.template .env

# Or create manually
nano .env  # or use any text editor
```

Add minimum configuration:

```bash
# LLM Configuration (required for real trading)
LLM_PROVIDER=mock  # Start with 'mock' for testing (no API key needed)
# LLM_PROVIDER=deepseek  # Use when ready for real trading
# LLM_API_KEY=your_key_here

# Trading Configuration
TRADING_MODE=paper  # Always start with paper trading!
SYMBOL=BTC/USDT
INITIAL_BALANCE=10000.0

# Optional: Supabase (for persistent data)
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=your_key_here
```

**💡 Tip**: Start with `LLM_PROVIDER=mock` to test without API keys!

---

## Step 3: Run Your First Test (1 minute)

```bash
# Run the bot (will use mock mode)
python -m src.main
```

You should see:
```
🤖 Starting trading bot in development mode
💰 Portfolio initialized with $10,000.00
🔄 Starting trading cycle...
```

**✅ Success!** The bot is running in mock mode.

---

## Step 4: Verify It's Working (1 minute)

Check that data files were created:

```bash
ls -la data/
```

You should see:
- `trades.json` - Trade history
- `portfolio.json` - Portfolio state
- `logs/bot.log` - Application logs

---

## ✅ You're Done!

Your bot is now running in **mock mode** (simulated trading).

### What's Next?

1. **See it in action**: Let it run for a few cycles and watch the console output
2. **Check the data**: Look at `data/trades.json` to see simulated trades
3. **Configure for real trading**:
   - Get a DeepSeek API key
   - Set `LLM_PROVIDER=deepseek` and add your API key
   - See [Configuration Reference](../reference/configuration.md)

### Next Steps

- 📖 **Read the [Installation Guide](installation.md)** for detailed setup
- 🎮 **Try [Making Your First Trade](first-trade.md)** (coming soon)
- ⚙️ **Review [Configuration Reference](../reference/configuration.md)** for all options
- 🚀 **Learn about [Deployment Options](../guides/deployment/overview.md)** when ready to deploy

---

## 🆘 Having Issues?

- **Bot won't start?** → Check [Troubleshooting Guide](../troubleshooting/common-issues.md)
- **Can't install dependencies?** → See [Installation Guide](installation.md)
- **Configuration errors?** → Review [Configuration Reference](../reference/configuration.md)

---

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Start bot | `python -m src.main` |
| Check logs | `tail -f data/logs/bot.log` |
| View trades | `cat data/trades.json` |
| View portfolio | `cat data/portfolio.json` |

---

**Ready for more?** → [Installation Guide](installation.md) → [Configuration Reference](../reference/configuration.md)
