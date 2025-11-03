# Frequently Asked Questions (FAQ)

Common questions and answers about the Alpha Arena Trading Bot.

---

## 🚀 Getting Started

### Q: Which LLM provider should I use?

**A**: DeepSeek is recommended for most users:
- **Cost-effective**: ~$0.03/day vs $0.80/day for GPT-4
- **Good performance**: Comparable results for trading decisions
- **Reliable**: Stable API and good documentation

**Use GPT-4** if you need the absolute best reasoning, but expect 27x higher costs.

**See**: [LLM Cost Analysis](../reference/LLM_COST_ANALYSIS.md) for detailed comparison.

### Q: Do I need an API key to get started?

**A**: No! Start with mock mode:
```bash
LLM_PROVIDER=mock python -m src.main
```

This lets you test everything without API keys. When ready for real trading, switch to a real provider.

### Q: How long does setup take?

**A**:
- **Quick start**: ~5 minutes (mock mode)
- **Full setup**: ~15 minutes (with database, API keys)
- **Production deployment**: ~30-60 minutes (Railway/Docker)

**See**: [Quick Start Guide](../getting-started/quickstart.md)

---

## 💰 Costs

### Q: How much does it cost to run the bot?

**A**: Costs vary by LLM provider and usage:

| Provider | Daily Cost | Monthly Cost |
|----------|------------|--------------|
| DeepSeek | ~$0.03 | ~$0.87 |
| GPT-3.5 | ~$0.13 | ~$3.81 |
| GPT-4 | ~$0.80 | ~$24.00 |

**Plus hosting costs**:
- Railway: $5-15/month (free tier includes $5 credit)
- Supabase: Free tier available
- Vercel (frontend): Free tier

**See**: [LLM Cost Analysis](../reference/LLM_COST_ANALYSIS.md)

### Q: Can I reduce costs?

**A**: Yes, several ways:
1. **Use DeepSeek** instead of GPT-4 (27x cheaper)
2. **Increase interval**: `RUN_INTERVAL_SECONDS=300` (5 min) reduces API calls by 50%
3. **Use mock mode** for testing/development
4. **Monitor usage**: Check logs for excessive API calls

---

## 🔒 Safety & Security

### Q: Is it safe for live trading?

**A**: **Start with paper trading!**

The bot is designed for Alpha Arena simulation (paper trading). Before live trading:
1. Test extensively in paper mode
2. Understand the risks
3. Start with minimal amounts
4. Never trade more than you can afford to lose

**Always use testnet first** even for live trading setup.

### Q: Are my API keys secure?

**A**: Yes, if you follow best practices:
- ✅ Use `.env` file (git-ignored)
- ✅ Never commit keys to git
- ✅ Use environment variables in production
- ✅ Rotate keys regularly
- ✅ Use Railway's encrypted variables

**See**: [Security Guidelines](../../SECURITY.md)

---

## 📊 Trading

### Q: What is Alpha Arena?

**A**: Alpha Arena is a competition methodology where LLMs are given $10,000 to trade perpetual futures with:
- Zero human intervention
- Quantitative data only (no news)
- 2.5-minute trading cycles
- PnL maximization goal

The bot implements this methodology.

**See**: [Alpha Arena Enhancements](../advanced/ALPHA_ARENA_ENHANCEMENTS.md)

### Q: What trading pairs are supported?

**A**: Any pair supported by your exchange. Common ones:
- `BTC/USDT`
- `ETH/USDT`
- `SOL/USDT`

Set via `SYMBOL` environment variable.

### Q: How does leverage work?

**A**: Leverage allows larger positions with less capital:
- **1x leverage**: $100 buys $100 worth
- **3x leverage**: $100 buys $300 worth
- **10x leverage**: $100 buys $1,000 worth (max)

Risks and rewards increase with leverage. Default is 1x, max is 10x.

---

## 🗄️ Database

### Q: Do I need a database?

**A**: For basic paper trading: **No**
- Data stored in JSON files (`data/trades.json`, `data/portfolio.json`)

For production/API: **Yes**
- Use Supabase (free tier available)
- Enables web dashboard
- Persistent storage
- Better for production

**See**: [Database Setup Guide](../guides/database/setup.md)

### Q: What's the difference between SUPABASE_URL and DATABASE_URL?

**A**:
- **SUPABASE_URL**: REST API endpoint (`https://xxx.supabase.co`) - used by application code
- **DATABASE_URL**: Direct PostgreSQL connection (`postgresql://...`) - used by Alembic migrations

Both point to the same database, just different access methods.

**See**: [Database Setup Guide](../guides/database/setup.md) for details.

---

## 🚀 Deployment

### Q: Which deployment method should I use?

**A**:
- **Railway**: Easiest, recommended for most users
- **Docker**: Good for developers, consistent environments
- **Manual**: Full control, advanced users

**See**: [Deployment Overview](../guides/deployment/overview.md)

### Q: Can I run this locally?

**A**: Yes! That's the recommended way to start:
```bash
python -m src.main
```

Run in paper trading mode locally before deploying.

### Q: Do I need to make my repository public?

**A**: **No!** Both Railway and Vercel support private repositories. Keep it private for better security.

---

## 🐛 Troubleshooting

### Q: Bot won't start - what do I check?

**A**: Common issues:
1. **Dependencies**: `pip install -r requirements.txt`
2. **Python version**: Need 3.8+
3. **Environment variables**: Check `.env` file
4. **Logs**: Check `data/logs/bot.log`

**See**: [Troubleshooting Guide](common-issues.md)

### Q: No trades are being generated

**A**: Check:
1. **LLM responses**: Look for "hold" decisions in logs
2. **Confidence threshold**: Lower `MIN_CONFIDENCE_THRESHOLD`
3. **Market data**: Verify data is being fetched
4. **Position limits**: Check `MAX_ACTIVE_POSITIONS`

### Q: API connection errors

**A**:
1. **Verify API key**: Check key is correct
2. **Check provider**: Ensure provider matches key type
3. **Rate limits**: Wait and retry
4. **Network**: Check internet connection

**See**: [Troubleshooting Guide](common-issues.md)

---

## 📈 Performance

### Q: How often does the bot trade?

**A**: Default is every 2.5 minutes (150 seconds), matching Alpha Arena style.

You can change via `RUN_INTERVAL_SECONDS`:
- `150` = 2.5 minutes (default)
- `300` = 5 minutes
- `600` = 10 minutes

### Q: Can I backtest strategies?

**A**: The bot focuses on live/paper trading. For backtesting:
- Use paper trading mode
- Analyze historical trades in `data/trades.json`
- Use visualization scripts: `python scripts/visualize_pnl.py`

### Q: How do I monitor performance?

**A**:
- **Console output**: Real-time trading decisions
- **Data files**: `data/trades.json`, `data/portfolio.json`
- **Web dashboard**: Real-time monitoring (if deployed)
- **Logs**: `data/logs/bot.log`

---

## 🤝 Contributing

### Q: How can I contribute?

**A**:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

**See**: [Contributing Guide](../../CONTRIBUTING.md) (coming soon)

### Q: Where should I report bugs?

**A**:
1. Search existing issues on GitHub
2. Create a new issue with:
   - Error messages
   - Steps to reproduce
   - System information
   - Logs (sanitized)

---

## 🎓 Learning

### Q: How does the bot make trading decisions?

**A**:
1. Fetches market data (price, volume)
2. Calculates portfolio state (balance, positions, PnL)
3. Sends data to LLM with trading instructions
4. LLM generates trading decision (buy/sell/hold)
5. Validates and executes decision

**See**: [Architecture Overview](../../ARCHITECTURE.md)

### Q: What behavioral patterns are tracked?

**A**:
- Bullish tilt (long vs short ratio)
- Holding periods
- Trade frequency
- Position sizing
- Confidence levels
- Exit plan tightness

**See**: [Behavioral Analysis](../advanced/ALPHA_ARENA_BEHAVIORAL_ANALYSIS.md)

---

## 🔧 Technical

### Q: What Python version do I need?

**A**: Python 3.8 or higher. Recommended: 3.9+

### Q: Can I use SQLite instead of PostgreSQL?

**A**: For development/testing: Yes (with modifications).
For production: Use PostgreSQL/Supabase.

### Q: Does it work on Windows/Mac/Linux?

**A**: Yes! Works on all platforms. Setup may vary slightly (paths, commands).

---

## 📚 Documentation

### Q: Where do I find documentation?

**A**:
- **Main docs**: [Documentation Index](../README.md)
- **Quick start**: [Quick Start Guide](../getting-started/quickstart.md)
- **API docs**: [API Documentation](../../API.md)
- **Troubleshooting**: [Troubleshooting Guide](common-issues.md)

### Q: Documentation is outdated

**A**:
- Check git history for recent changes
- Open an issue if you find outdated info
- Submit a PR with updates

---

## ⚠️ Important Notes

### Q: Is this financial advice?

**A**: **No!** This is for educational and research purposes only. Trading cryptocurrencies involves substantial risk. Never trade with money you cannot afford to lose.

### Q: Can I use this commercially?

**A**: Check the [LICENSE](../../LICENSE) file. MIT License generally allows commercial use, but verify for your use case.

---

## 🆘 Still Have Questions?

1. Check [Troubleshooting Guide](common-issues.md)
2. Search [existing GitHub issues](https://github.com/yourusername/llm-trading-bot/issues)
3. Review [Documentation Index](../README.md)
4. Open a new issue on GitHub

---

**Last Updated**: See git history for FAQ updates.
