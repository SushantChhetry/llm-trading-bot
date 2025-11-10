# Pre-Live Trading Checklist

This checklist must be completed before enabling live trading mode with real money. Follow each step carefully and verify all items are checked before proceeding.

## Critical Safety Checks

### 1. Risk Service Verification

- [ ] Risk service is running and accessible
  ```bash
  curl http://localhost:8003/health
  ```
  Expected: `{"status": "healthy", "service": "risk_service"}`

- [ ] Risk service fail-closed behavior is enabled for live trading
  - Verify `RISK_SERVICE_FAIL_CLOSED=true` in environment variables
  - Verify `RISK_SERVICE_REQUIRED=true` for live trading

- [ ] Kill switch functionality tested
  ```bash
  python scripts/test_kill_switch_manual.py
  ```
  Expected: All tests pass

- [ ] Kill switch can be manually activated/deactivated
  ```bash
  # Activate
  curl -X POST http://localhost:8003/risk/kill_switch \
    -H "Content-Type: application/json" \
    -d '{"action": "activate", "reason": "Manual test"}'
  
  # Deactivate
  curl -X POST http://localhost:8003/risk/kill_switch \
    -H "Content-Type: application/json" \
    -d '{"action": "deactivate"}'
  ```

### 2. Risk Validation Integration

- [ ] Risk validation is called BEFORE trade execution
  - Verify in logs: `RISK_VALIDATION_PASSED` appears before `TRADE_EXECUTION_COMPLETE`
  - Verify trades are rejected when risk validation fails

- [ ] Risk limits are appropriate for your risk tolerance
  - Check `services/risk_service.py` for default limits:
    - `max_position_value_pct`: 10% of NAV (default)
    - `max_leverage`: 3x (default)
    - `per_trade_var_pct`: 0.35% of NAV (default)
    - `max_daily_loss_pct`: 2% of NAV (default)
    - `max_drawdown_pct`: 10% drawdown (default)

- [ ] Daily loss tracking is working
  - Verify daily loss percentage is calculated and passed to risk service
  - Check logs for: `Daily loss tracking: start_nav=... current_nav=... daily_loss_pct=...`

### 3. Position Reconciliation

- [ ] Position reconciliation is enabled
  - Verify `POSITION_RECONCILIATION_INTERVAL` is set (default: 5 cycles)
  - Verify position reconciler is initialized in logs

- [ ] Position reconciliation runs periodically
  - Check logs for reconciliation messages every N cycles
  - Verify discrepancies are detected and logged

### 4. Configuration Verification

- [ ] All required environment variables are set
  ```bash
  # Required for live trading:
  TRADING_MODE=live
  TRADING_MODE_LIVE_CONFIRMED=yes
  EXCHANGE_API_KEY=...
  EXCHANGE_API_SECRET=...
  LLM_API_KEY=...
  RISK_SERVICE_URL=http://localhost:8003
  RISK_SERVICE_FAIL_CLOSED=true
  RISK_SERVICE_REQUIRED=true
  ```

- [ ] Trading limits are appropriate
  - `MAX_POSITION_SIZE`: Max % of balance per trade
  - `MAX_LEVERAGE`: Maximum leverage allowed
  - `STOP_LOSS_PERCENT`: Stop loss percentage
  - `TAKE_PROFIT_PERCENT`: Take profit percentage

- [ ] Risk service configuration is correct
  - `RISK_SERVICE_FAIL_CLOSED=true` for live trading (rejects trades when service is down)
  - `RISK_SERVICE_REQUIRED=true` for live trading (fails startup if service unavailable)

### 5. Paper Trading Validation

- [ ] Extensive paper trading completed
  - Minimum 1-2 weeks of paper trading
  - Tested across different market conditions
  - Verified strategy performance is consistent

- [ ] Paper trading results are realistic
  - Check for overfitting (unrealistic Sharpe ratios >3.0)
  - Verify win rate is reasonable (not >80%)
  - Check for proper drawdowns (not zero or very small)

- [ ] Paper trading matches expected behavior
  - Trades execute as expected
  - Risk limits are enforced
  - Position monitoring works correctly

### 6. Exchange API Integration

- [ ] Exchange API keys are valid and have correct permissions
  - Test API connectivity
  - Verify API keys have trading permissions (not just read-only)
  - Check API rate limits are understood

- [ ] Exchange testnet tested (if available)
  - Test order placement on testnet
  - Test order cancellation
  - Test position fetching
  - Note: Kraken does not have testnet

- [ ] Exchange-specific requirements understood
  - Minimum order sizes
  - Price precision requirements
  - Quantity precision requirements
  - Trading fees (maker vs taker)

### 7. Monitoring and Alerts

- [ ] Monitoring is set up and working
  - Dashboard is accessible
  - Logs are being written
  - Metrics are being collected

- [ ] Alerts are configured (if applicable)
  - Risk service alerts
  - Exchange API alerts
  - System health alerts

### 8. Error Handling

- [ ] Error handling is robust
  - API failures are handled gracefully
  - Network errors are retried appropriately
  - Invalid responses are logged and handled

- [ ] Circuit breakers are configured
  - Verify circuit breaker thresholds are appropriate
  - Test circuit breaker activation

### 9. Backup and Recovery

- [ ] Backup procedures are in place
  - Trade history is backed up
  - Portfolio state is backed up
  - Configuration is backed up

- [ ] Recovery procedures are tested
  - Can restore from backup
  - Can resume trading after restart
  - Position state is preserved

### 10. Documentation Review

- [ ] All documentation is reviewed
  - Architecture documentation
  - Risk management documentation
  - Deployment documentation

- [ ] Team members understand the system
  - Risk management limits
  - Kill switch procedures
  - Emergency shutdown procedures

## Final Verification Steps

1. **Start with minimal capital**
   - Use 1-5% of intended capital for first live trades
   - Monitor closely for first 24-48 hours
   - Gradually increase if performance is consistent

2. **Monitor first trades closely**
   - Watch logs in real-time
   - Verify trades execute as expected
   - Check risk validation is working
   - Verify position reconciliation

3. **Verify kill switch works**
   - Test kill switch activation
   - Verify trades are blocked
   - Test kill switch deactivation
   - Verify trades resume

4. **Check risk service health**
   - Verify health checks pass
   - Monitor for any errors
   - Check kill switch status

## Emergency Procedures

### If Something Goes Wrong

1. **Immediately activate kill switch**
   ```bash
   curl -X POST http://localhost:8003/risk/kill_switch \
     -H "Content-Type: application/json" \
     -d '{"action": "activate", "reason": "Emergency"}'
   ```

2. **Stop the trading bot**
   - Use Ctrl+C or stop the service
   - Verify bot stops cleanly

3. **Review logs**
   - Check for errors
   - Identify root cause
   - Document issues

4. **Manual position management**
   - Check exchange for actual positions
   - Manually close positions if needed
   - Verify all positions are closed

## Post-Go-Live Monitoring

After going live, monitor these metrics closely:

- [ ] Risk service health (every cycle)
- [ ] Daily loss tracking (should reset at midnight UTC)
- [ ] Position reconciliation (every N cycles)
- [ ] Trade execution success rate
- [ ] API error rate
- [ ] Kill switch status

## Sign-Off

Before enabling live trading, ensure:

- [ ] All critical checks above are completed
- [ ] At least one other person has reviewed this checklist
- [ ] You understand all risks involved
- [ ] You have tested extensively in paper mode
- [ ] You are prepared to monitor the system closely

**Date:** _______________

**Reviewed by:** _______________

**Approved by:** _______________

---

**Remember:** Trading with real money involves significant risk. Only proceed when you are confident in the system and have tested thoroughly.

