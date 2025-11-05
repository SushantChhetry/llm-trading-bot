# Risk Service Deployment Options

The risk service can be deployed in two ways on Railway, depending on your needs for isolation, cost, and scalability.

## Option A: Separate Service (Recommended)

**Best for:** Production environments where isolation and independent scaling are important.

### Setup
1. Create a new Railway service in your existing project
2. Root Directory: `deepseek-experiment`
3. Railway will auto-detect `services/railway.json`
4. Set environment variable in Trading Bot service:
   ```
   RISK_SERVICE_URL=http://risk-service.railway.internal:8003
   ```

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

### Setup
1. Update Trading Bot service start command to:
   ```
   bash scripts/start_with_risk_service.sh
   ```
2. Or use the provided `railway.json.with-risk-service`:
   ```bash
   cp railway.json.with-risk-service railway.json
   ```
3. Set environment variables:
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

You can start with Option B and migrate to Option A later if needed:

1. Create the new risk service
2. Update `RISK_SERVICE_URL` to point to the new service
3. Remove the startup script from trading bot
4. Revert to original `railway.json`

The risk client is designed to handle both scenarios gracefully.

