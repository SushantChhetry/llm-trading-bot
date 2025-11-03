# Common Issues & Troubleshooting

Quick solutions to the most common problems when setting up and running the Alpha Arena Trading Bot.

---

## 🚨 Bot Won't Start

### Issue: Import Errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'xxx'
```

**Solutions:**
1. Ensure virtual environment is activated:
   ```bash
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate    # Windows
   ```

2. Install all dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Verify Python version:
   ```bash
   python --version  # Should be 3.8+
   ```

### Issue: Configuration Errors

**Symptoms:**
```
KeyError: 'LLM_PROVIDER'
ValueError: Invalid configuration
```

**Solutions:**
1. Check `.env` file exists in `deepseek-experiment/` directory
2. Verify environment variables are set correctly:
   ```bash
   # Check if loaded
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('LLM_PROVIDER'))"
   ```

3. Use mock mode for testing:
   ```bash
   LLM_PROVIDER=mock  # No API key needed
   ```

4. Review [Configuration Reference](../reference/configuration.md) for required variables

### Issue: Port Already in Use

**Symptoms:**
```
OSError: [Errno 48] Address already in use
Port 8000 is already in use
```

**Solutions:**
1. Find what's using the port:
   ```bash
   # Linux/Mac
   lsof -i :8000

   # Windows
   netstat -ano | findstr :8000
   ```

2. Kill the process:
   ```bash
   # Linux/Mac
   kill -9 <PID>

   # Windows
   taskkill /PID <PID> /F
   ```

3. Or change the port in your configuration

---

## 🔌 Connection Issues

### Issue: Can't Connect to Database

**Symptoms:**
```
Connection refused
Could not connect to database
DATABASE_URL not found
```

**Solutions:**

1. **Verify DATABASE_URL is set:**
   ```bash
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✅ Set' if os.getenv('DATABASE_URL') else '❌ Not set')"
   ```

2. **Check Supabase connection:**
   - Ensure using "Direct connection" (port 5432, NOT 6543)
   - Verify password is correct (no `[YOUR-PASSWORD]` placeholder)
   - Check Supabase project is active

3. **Test connection:**
   ```bash
   python scripts/test_alembic_connection.py
   ```

4. **Check network restrictions:**
   - Verify IP isn't blocked in Supabase Network Restrictions
   - Try from different network if possible

5. **See [Database Setup Guide](../guides/database/setup.md)** for detailed instructions

### Issue: LLM API Connection Errors

**Symptoms:**
```
APIError: Invalid API key
Connection timeout
Rate limit exceeded
```

**Solutions:**

1. **Verify API key:**
   - Check key is correct (no extra spaces)
   - Ensure key hasn't expired
   - Verify provider matches key type

2. **Check provider:**
   ```bash
   # Test with mock mode first
   LLM_PROVIDER=mock python -m src.main
   ```

3. **Rate limiting:**
   - Wait and retry
   - Check provider's rate limits
   - Consider upgrading plan

4. **Network issues:**
   - Check internet connection
   - Verify firewall/proxy settings
   - Try from different network

---

## 💾 Data Issues

### Issue: No Trades Being Generated

**Symptoms:**
- Bot runs but no trades appear
- `data/trades.json` is empty
- No trading activity

**Solutions:**

1. **Check LLM responses:**
   - Look for "hold" decisions in logs
   - Verify LLM is actually making decisions
   - Check confidence thresholds

2. **Review configuration:**
   ```bash
   # Check min confidence threshold
   MIN_CONFIDENCE_THRESHOLD=0.5  # Try lower value

   # Check position limits
   MAX_ACTIVE_POSITIONS=6  # Ensure not too restrictive
   ```

3. **Verify market data:**
   - Check if market data is being fetched
   - Look for price updates in logs
   - Ensure exchange/symbol is correct

4. **Check logs:**
   ```bash
   tail -f data/logs/bot.log
   ```

### Issue: Data Files Not Created

**Symptoms:**
- `data/trades.json` doesn't exist
- `data/portfolio.json` missing

**Solutions:**

1. **Check directory permissions:**
   ```bash
   ls -la data/
   chmod -R 755 data/
   ```

2. **Create data directory:**
   ```bash
   mkdir -p data/logs
   touch data/trades.json
   touch data/portfolio.json
   ```

3. **Verify write permissions:**
   ```bash
   python -c "import json; json.dump({}, open('data/test.json', 'w'))"
   ```

### Issue: Database Schema Errors

**Symptoms:**
```
Table 'trades' does not exist
Migration errors
Schema mismatch
```

**Solutions:**

1. **Initialize database schema:**
   ```bash
   # Using Supabase SQL
   # Run scripts/supabase_schema.sql in Supabase SQL Editor
   ```

2. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

3. **Verify schema:**
   ```bash
   # Check tables exist
   python -c "from src.supabase_client import get_supabase_service; print(get_supabase_service().table('trades').select('id').limit(1).execute())"
   ```

4. **See [Migration Guide](../guides/database/migrations.md)** for details

---

## 🚀 Deployment Issues

### Issue: Railway Service Won't Start

**Symptoms:**
- Service shows "Failed" status
- Build errors in Railway logs

**Solutions:**

1. **Check environment variables:**
   - Verify all required variables are set
   - Check for typos in variable names
   - Ensure values don't have quotes

2. **Review build logs:**
   ```bash
   railway logs --build
   ```

3. **Check Python version:**
   - Ensure compatible Python version
   - Verify `requirements.txt` is valid

4. **Verify root directory:**
   - Set to `deepseek-experiment` in Railway settings

5. **See [Railway Deployment Guide](../guides/deployment/railway.md)**

### Issue: Docker Container Won't Start

**Symptoms:**
- Container exits immediately
- Error in docker-compose logs

**Solutions:**

1. **Check logs:**
   ```bash
   docker-compose logs
   docker-compose logs <service-name>
   ```

2. **Verify environment variables:**
   ```bash
   docker-compose config
   ```

3. **Rebuild containers:**
   ```bash
   docker-compose build --no-cache
   docker-compose up
   ```

4. **Check volume permissions:**
   ```bash
   sudo chown -R $USER:$USER ./data ./logs
   ```

5. **See [Docker Deployment Guide](../guides/deployment/docker.md)**

### Issue: API Server Not Responding

**Symptoms:**
- API returns 404 or connection refused
- CORS errors in browser

**Solutions:**

1. **Verify API is running:**
   ```bash
   curl http://localhost:8001/api/status
   ```

2. **Check CORS settings:**
   - Verify `CORS_ORIGINS` includes your frontend URL
   - Check `ENVIRONMENT=production` is set correctly
   - Ensure no trailing slashes in URLs

3. **Check port:**
   - Verify API is listening on correct port
   - Check for port conflicts

4. **Review logs:**
   ```bash
   # Railway
   railway logs api

   # Docker
   docker-compose logs api
   ```

---

## ⚙️ Configuration Issues

### Issue: Environment Variables Not Loading

**Symptoms:**
- Variables show as None or empty
- Default values always used

**Solutions:**

1. **Verify .env file location:**
   ```bash
   # Should be in deepseek-experiment/
   ls -la .env
   ```

2. **Check file format:**
   ```bash
   # No spaces around =
   KEY=value  # ✅ Correct
   KEY = value  # ❌ Wrong
   ```

3. **Verify python-dotenv installed:**
   ```bash
   pip install python-dotenv
   ```

4. **Load manually for testing:**
   ```bash
   export $(cat .env | xargs)
   ```

### Issue: Invalid Configuration Values

**Symptoms:**
- Errors about invalid enum values
- Out of range errors

**Solutions:**

1. **Check valid values:**
   - `LLM_PROVIDER`: `deepseek`, `openai`, `anthropic`, `mock`
   - `TRADING_MODE`: `paper`, `live`
   - Leverage: `1.0` to `10.0`

2. **Review [Configuration Reference](../reference/configuration.md)**

3. **Use validation:**
   ```bash
   python -c "from src.startup_validator import validate_startup; validate_startup()"
   ```

---

## 📊 Dashboard Issues

### Issue: Dashboard Shows No Data

**Symptoms:**
- Dashboard loads but shows empty
- "No data available" messages

**Solutions:**

1. **Verify API connection:**
   - Check browser console for errors
   - Verify API URL is correct
   - Test API directly: `curl http://your-api/api/trades`

2. **Check CORS:**
   - Look for CORS errors in console
   - Verify CORS_ORIGINS includes dashboard URL

3. **Verify data exists:**
   - Check if trading bot has created trades
   - Verify database has data
   - Check API returns data

4. **See [Dashboard Debugging Guide](../guides/dashboard/debugging.md)**

### Issue: Dashboard Won't Build

**Symptoms:**
- `npm run build` fails
- TypeScript errors

**Solutions:**

1. **Install dependencies:**
   ```bash
   cd web-dashboard
   npm install
   ```

2. **Clear cache:**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **Check Node version:**
   ```bash
   node --version  # Should be 16+
   ```

---

## 🔍 Getting More Help

### Debug Steps

1. **Enable debug logging:**
   ```bash
   LOG_LEVEL=DEBUG python -m src.main
   ```

2. **Check logs:**
   ```bash
   tail -f data/logs/bot.log
   ```

3. **Test components individually:**
   ```bash
   # Test database
   python scripts/test_alembic_connection.py

   # Test LLM (mock mode)
   LLM_PROVIDER=mock python -c "from src.llm_client import LLMClient; print('OK')"
   ```

### Still Having Issues?

1. **Check [FAQ](faq.md)** for common questions
2. **Review related documentation** for your specific issue
3. **Search existing issues** on GitHub
4. **Create a new issue** with:
   - Error messages
   - Steps to reproduce
   - System information
   - Logs (sanitized of secrets)

---

## 📋 Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Bot won't start | Check dependencies: `pip install -r requirements.txt` |
| No trades | Lower `MIN_CONFIDENCE_THRESHOLD` or check LLM responses |
| Database connection | Verify `DATABASE_URL` and test with script |
| API not responding | Check service is running and CORS settings |
| Config errors | Verify `.env` file format and location |

---

## Related Documentation

- **[Quick Start Guide](../getting-started/quickstart.md)** - Get started quickly
- **[Database Setup](../guides/database/setup.md)** - Database troubleshooting
- **[Deployment Guides](../guides/deployment/overview.md)** - Deployment issues
- **[Configuration Reference](../reference/configuration.md)** - Config help
