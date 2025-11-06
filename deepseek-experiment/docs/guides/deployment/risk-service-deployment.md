# Risk Service Deployment Options

The risk service can be deployed in two ways on Railway, depending on your needs for isolation, cost, and scalability.

## Option A: Separate Service (Recommended)

**Best for:** Production environments where isolation and independent scaling are important.

### Setup
1. Create a new Railway service in your existing project
2. **Service Name**: `risk-service` (important - this becomes the hostname for private networking)
3. **Root Directory**: `deepseek-experiment`
4. **Builder**: Set to **Railpack** (or leave as default) - remove any Dockerfile configuration
5. Railway will auto-detect `services/railway.json` in the subdirectory
6. Set environment variable in Trading Bot service:
   ```
   RISK_SERVICE_URL=http://risk-service.railway.internal:8003
   ```
   **Important**: The service name (`risk-service`) must match the hostname in the URL.

### Pros
- ✅ **Complete isolation** - Risk service failures don't affect trading bot
- ✅ **Independent scaling** - Scale each service separately
- ✅ **Better resource allocation** - Each service gets dedicated resources
- ✅ **Clear separation** - Matches microservices architecture
- ✅ **Easier debugging** - Separate logs and metrics

### Cons
- ❌ **Additional cost** - One more Railway service
- ❌ **More complex** - Need to manage service discovery

## Option B: Combined with Trading Bot (Cost-Effective)

**Best for:** Cost-conscious deployments where you're okay with shared resources.

**Note**: This option is not recommended with Railpack. If you need combined deployment, you would need to use a custom startup script, but separate services are strongly recommended for reliability.

### Setup (Not Recommended with Railpack)
1. Update Trading Bot service start command to:
   ```
   bash scripts/start_with_risk_service.sh
   ```
2. Set environment variables:
   ```
   RISK_SERVICE_URL=http://localhost:8003
   RISK_SERVICE_PORT=8003
   ```

### Pros
- ✅ **Cost-effective** - Only 2 services instead of 3
- ✅ **Process separation** - Still runs as separate processes
- ✅ **Shared resources** - Efficient resource usage
- ✅ **Simple networking** - Uses localhost (no network latency)

### Cons
- ❌ **Tied scaling** - Can't scale independently
- ❌ **Shared failure** - If container crashes, both services restart
- ❌ **Resource contention** - Both compete for same resources

## Recommendation

**For Production:** Use **Option A** (separate service) for maximum reliability and isolation.

**For Development/Staging:** Use **Option B** (combined) to save costs while maintaining functionality.

## Migration Path

If you're currently using Option B (combined) and want to migrate to Option A (separate service):

1. Create the new risk service with **Railpack** builder
2. Service Name: `risk-service`
3. Root Directory: `deepseek-experiment`
4. Railway auto-detects `services/railway.json`
5. Update `RISK_SERVICE_URL` in Trading Bot service to: `http://risk-service.railway.internal:8003`
6. Remove the startup script from trading bot (if using combined approach)
7. Update trading bot `railway.json` to use standalone start command: `python -m src.main`

The risk client is designed to handle both scenarios gracefully.

## Builder Configuration

Both services use **Railpack** (Railway's default builder) which:
- ✅ Auto-detects Python projects
- ✅ Uses `requirements.txt` automatically
- ✅ No Dockerfile needed
- ✅ Eliminates Dockerfile path configuration issues

