# 🔒 Security Guidelines

This document outlines security best practices and guidelines for the LLM Trading Bot system.

## 🚨 Critical Security Rules

### 1. API Key Management
- **NEVER** commit API keys to version control
- **NEVER** hardcode API keys in source code
- **ALWAYS** use environment variables for sensitive data
- **ALWAYS** validate API key formats before use
- **ALWAYS** rotate API keys regularly

### 2. Test Data Security
- **NEVER** use real API keys in tests
- **ALWAYS** use mock data generators for testing
- **ALWAYS** use placeholder values in test files
- **ALWAYS** ensure test data doesn't contain sensitive information

### 3. Configuration Security
- **NEVER** store sensitive data in configuration files
- **ALWAYS** use environment variable substitution
- **ALWAYS** validate configuration before deployment
- **ALWAYS** use different configurations for different environments

## 🛡️ Security Implementation

### API Key Validation
```python
# ✅ CORRECT - Using mock data in tests
valid_key = MockDataGenerator.generate_mock_api_key("deepseek")
self.assertTrue(security_manager.validate_api_key(valid_key, "deepseek"))

# ❌ WRONG - Hardcoded API key
valid_key = "sk-1234567890abcdef1234567890abcdef"  # NEVER DO THIS
```

### Environment Variables
```bash
# ✅ CORRECT - Using environment variables
export LLM_API_KEY="sk-your-actual-key-here"
export EXCHANGE_API_KEY="your-exchange-key"

# ❌ WRONG - Hardcoded in code
LLM_API_KEY = "sk-1234567890abcdef"  # NEVER DO THIS
```

### Configuration Files
```yaml
# ✅ CORRECT - Using environment variable substitution
llm:
  api_key: "${LLM_API_KEY}"  # Will be replaced at runtime

# ❌ WRONG - Hardcoded values
llm:
  api_key: "sk-1234567890abcdef"  # NEVER DO THIS
```

## 🔍 Security Checklist

### Before Committing Code
- [ ] No API keys or secrets in source code
- [ ] No hardcoded credentials
- [ ] All sensitive data uses environment variables
- [ ] Test files use mock data only
- [ ] Configuration files use variable substitution
- [ ] No sensitive data in comments or documentation

### Before Deployment
- [ ] Environment variables properly set
- [ ] API keys validated and rotated
- [ ] Database credentials secured
- [ ] SSL/TLS certificates valid
- [ ] Firewall rules configured
- [ ] Access controls implemented

### Regular Security Tasks
- [ ] Rotate API keys monthly
- [ ] Review access logs weekly
- [ ] Update dependencies monthly
- [ ] Security audit quarterly
- [ ] Backup verification weekly

## 🚫 What NOT to Do

### ❌ Never Commit These
```bash
# API Keys
sk-1234567890abcdef1234567890abcdef
sk-ant-1234567890abcdef1234567890abcdef1234567890abcdef1234567890

# Database Credentials
postgresql://user:password@localhost:5432/db
mongodb://user:password@localhost:27017/db

# Exchange Credentials
api_key: "your-exchange-api-key"
api_secret: "your-exchange-secret"

# JWT Secrets
JWT_SECRET: "your-jwt-secret-key"

# Encryption Keys
ENCRYPTION_KEY: "your-encryption-key"
```

### ❌ Never Hardcode in Tests
```python
# ❌ WRONG - Real-looking API key
test_key = "sk-1234567890abcdef1234567890abcdef"

# ❌ WRONG - Real-looking database URL
test_db_url = "postgresql://user:password@localhost:5432/test"

# ❌ WRONG - Real-looking credentials
test_credentials = {
    "api_key": "your-api-key",
    "secret": "your-secret"
}
```

## ✅ What TO Do

### ✅ Use Mock Data Generators
```python
# ✅ CORRECT - Using mock generators
from tests.test_utils import MockDataGenerator

# Generate mock API key
mock_key = MockDataGenerator.generate_mock_api_key("deepseek")

# Generate mock trading data
mock_trade = MockDataGenerator.generate_mock_trade_data()

# Generate mock portfolio data
mock_portfolio = MockDataGenerator.generate_mock_portfolio_data()
```

### ✅ Use Environment Variables
```python
# ✅ CORRECT - Reading from environment
import os
api_key = os.getenv("LLM_API_KEY")
if not api_key:
    raise ValueError("LLM_API_KEY environment variable not set")
```

### ✅ Use Configuration Management
```python
# ✅ CORRECT - Using config manager
from src.config_manager import config_manager

api_key = config_manager.llm.api_key
if not config_manager.security_manager.validate_api_key(api_key, "deepseek"):
    raise ValueError("Invalid API key format")
```

## 🔐 Secure Development Practices

### 1. Input Validation
- Always validate and sanitize user inputs
- Use type hints for better code safety
- Implement proper error handling
- Never trust external data

### 2. Error Handling
- Never expose sensitive information in error messages
- Log errors securely without sensitive data
- Use generic error messages for users
- Implement proper exception handling

### 3. Logging Security
- Never log API keys or passwords
- Use structured logging with sensitive data filtering
- Implement log rotation and retention policies
- Monitor logs for security events

### 4. Data Protection
- Encrypt sensitive data at rest
- Use secure communication protocols (HTTPS/TLS)
- Implement proper access controls
- Regular security audits

## 🚨 Incident Response

### If API Keys Are Exposed
1. **Immediately** rotate the exposed keys
2. **Revoke** access for compromised keys
3. **Audit** logs for unauthorized access
4. **Update** all systems with new keys
5. **Review** code for other potential exposures

### If Sensitive Data Is Committed
1. **Immediately** remove from version control
2. **Purge** from git history if necessary
3. **Rotate** all affected credentials
4. **Audit** access to the repository
5. **Implement** additional security measures

## 📚 Security Resources

### Tools
- `git-secrets` - Prevents committing secrets
- `truffleHog` - Finds secrets in git repos
- `bandit` - Python security linter
- `safety` - Checks for known security vulnerabilities

### Commands
```bash
# Check for secrets in git history
git log --all --full-history -- . | grep -i "api_key\|password\|secret"

# Scan for secrets in current code
truffleHog --regex --entropy=False .

# Check Python security issues
bandit -r src/

# Check for vulnerable dependencies
safety check
```

## 🔄 Regular Security Tasks

### Daily
- Monitor access logs
- Check for failed authentication attempts
- Review error logs for security issues

### Weekly
- Rotate test API keys
- Review user access permissions
- Check for dependency updates

### Monthly
- Rotate production API keys
- Security dependency updates
- Access log analysis
- Backup verification

### Quarterly
- Full security audit
- Penetration testing
- Security training review
- Incident response drill

## 📞 Security Contacts

- **Security Team**: security@yourcompany.com
- **Incident Response**: incident@yourcompany.com
- **Emergency**: +1-XXX-XXX-XXXX

## 📋 Security Checklist Template

```markdown
## Security Review Checklist

### Code Review
- [ ] No hardcoded secrets
- [ ] Proper input validation
- [ ] Secure error handling
- [ ] No sensitive data in logs

### Configuration
- [ ] Environment variables used
- [ ] No secrets in config files
- [ ] Proper access controls
- [ ] Secure defaults

### Testing
- [ ] Mock data used in tests
- [ ] No real credentials in tests
- [ ] Security tests included
- [ ] Edge cases covered

### Deployment
- [ ] Secrets properly configured
- [ ] SSL/TLS enabled
- [ ] Firewall rules set
- [ ] Monitoring enabled
```

Remember: **Security is everyone's responsibility!** 🛡️
