# Contributing Guide

Thank you for your interest in contributing to the Alpha Arena Trading Bot! This guide will help you get started.

## 🤝 How to Contribute

There are many ways to contribute:

- 🐛 **Report bugs** - Help us improve by reporting issues
- 💡 **Suggest features** - Share your ideas for improvements
- 📝 **Improve documentation** - Help make docs better for everyone
- 🔧 **Submit code** - Fix bugs, add features, improve performance
- ✅ **Write tests** - Help ensure code quality

---

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/your-username/llm-trading-bot.git
cd llm-trading-bot/deepseek-experiment
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black isort mypy
```

### 3. Configure Your Environment

```bash
# Copy environment template
cp env.production.template .env

# Edit .env with your settings (use mock mode for testing)
# LLM_PROVIDER=mock  # No API key needed for development
```

---

## 📝 Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

**Branch naming:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

### 2. Make Your Changes

- Write clean, readable code
- Follow existing code style
- Add comments for complex logic
- Update documentation if needed

### 3. Test Your Changes

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_trading_engine.py

# Run with coverage
pytest --cov=src tests/

# Run linting
black src/ --check
isort src/ --check
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

**Commit message format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding/updating tests
- `chore:` - Maintenance tasks

**Examples:**
```
feat: add support for new exchange
fix: resolve database connection timeout
docs: update installation guide
test: add tests for risk manager
```

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Reference to related issues (if any)
- Screenshots/evidence (if UI changes)

---

## 📋 Code Style Guidelines

### Python Style

We follow PEP 8 with some modifications:

**Formatting:**
- Use `black` for code formatting (line length: 88)
- Use `isort` for import sorting
- Maximum line length: 100 characters

```bash
# Format code
black src/

# Sort imports
isort src/
```

**Type Hints:**
- Use type hints for function parameters and return values
- Use `Optional[T]` for nullable types
- Use `List[T]`, `Dict[K, V]` for collections

**Example:**
```python
from typing import Optional, List, Dict

def process_trades(
    trades: List[Dict[str, float]],
    filter_active: bool = True
) -> Optional[List[Dict[str, float]]]:
    """Process trading data with optional filtering."""
    pass
```

**Documentation:**
- Use docstrings for all public functions/classes
- Follow Google-style docstrings

**Example:**
```python
def calculate_sharpe_ratio(
    returns: List[float],
    risk_free_rate: float = 0.0
) -> float:
    """
    Calculate Sharpe ratio for a series of returns.

    Args:
        returns: List of return percentages
        risk_free_rate: Risk-free rate (default: 0.0)

    Returns:
        Sharpe ratio as float

    Raises:
        ValueError: If returns list is empty
    """
    pass
```

### File Organization

```
src/
├── main.py              # Entry point
├── trading_engine.py    # Core trading logic
├── llm_client.py        # LLM integration
└── ...
```

- Keep files focused on single responsibility
- Group related functionality together
- Use descriptive file names

---

## 🧪 Testing Guidelines

### Writing Tests

- Write tests for new features
- Aim for high code coverage
- Test edge cases and error conditions
- Use descriptive test names

**Test file structure:**
```python
import pytest
from src.trading_engine import TradingEngine

class TestTradingEngine:
    def test_execute_buy_with_valid_input(self):
        """Test buying with valid parameters."""
        engine = TradingEngine()
        result = engine.execute_buy(amount_usdt=100.0, leverage=2.0)
        assert result["success"] is True

    def test_execute_buy_insufficient_balance(self):
        """Test buying with insufficient balance."""
        engine = TradingEngine()
        engine.balance = 50.0
        result = engine.execute_buy(amount_usdt=100.0, leverage=1.0)
        assert result["success"] is False
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_trading_engine.py

# Run specific test
pytest tests/test_trading_engine.py::TestTradingEngine::test_execute_buy

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### Test Coverage

- Aim for >80% code coverage
- Focus on critical paths (trading logic, risk management)
- Don't obsess over 100% coverage

---

## 📚 Documentation Guidelines

### Code Documentation

- Document all public functions/classes
- Include parameter types and return types
- Add examples for complex functions
- Update docstrings when code changes

### User Documentation

When updating documentation:

- Keep it clear and concise
- Use examples where helpful
- Update all related docs when changing features
- Check spelling and grammar

**Documentation locations:**
- User guides: `docs/`
- API docs: `API.md`
- Architecture: `ARCHITECTURE.md`
- README: `README.md`

---

## 🔍 Code Review Process

### Before Submitting PR

- [ ] Code follows style guidelines
- [ ] Tests pass (`pytest`)
- [ ] Code is formatted (`black`, `isort`)
- [ ] Documentation updated
- [ ] No sensitive data in code
- [ ] Commit messages follow format

### PR Review Checklist

Maintainers will check:
- ✅ Code quality and style
- ✅ Test coverage
- ✅ Documentation completeness
- ✅ Security considerations
- ✅ Performance impact
- ✅ Breaking changes

### Addressing Feedback

- Be open to feedback
- Respond to comments promptly
- Make requested changes
- Ask questions if unclear

---

## 🐛 Reporting Bugs

### Before Reporting

1. Check existing issues
2. Verify it's not already fixed
3. Reproduce the issue

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**Steps to Reproduce**
1. Step one
2. Step two
3. ...

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: [e.g., macOS 13.0]
- Python: [e.g., 3.9.0]
- Version: [e.g., commit hash]

**Logs**
Relevant log output (sanitized of secrets)

**Additional Context**
Any other relevant information
```

---

## 💡 Suggesting Features

### Feature Request Template

```markdown
**Feature Description**
Clear description of the feature

**Use Case**
Why is this feature needed?

**Proposed Solution**
How should it work?

**Alternatives Considered**
Other approaches you've thought about

**Additional Context**
Any other relevant information
```

---

## 🔒 Security

### Security Best Practices

- Never commit API keys or secrets
- Use environment variables for sensitive data
- Sanitize logs before sharing
- Follow [Security Guidelines](SECURITY.md)

### Reporting Security Issues

**Do NOT** open public issues for security vulnerabilities.

Instead:
1. Email security concerns privately
2. Or create a draft security advisory on GitHub
3. Wait for response before disclosing

---

## 🎯 Project Priorities

We prioritize:

1. **Stability** - Reliability over features
2. **Security** - Protect user data and keys
3. **Documentation** - Clear, helpful docs
4. **Performance** - Efficient, scalable code
5. **Testing** - Well-tested code

---

## 📞 Getting Help

### Questions?

- Check [Documentation Index](docs/README.md)
- Review [FAQ](docs/troubleshooting/faq.md)
- Search existing issues
- Open a new issue (use "question" label)

### Stuck?

- Review similar code in the codebase
- Check test files for examples
- Ask in PR comments
- Open a discussion on GitHub

---

## 🙏 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md (if we add one)
- Acknowledged in release notes
- Appreciated by the community!

---

## 📋 Checklist for Contributors

Before submitting:

- [ ] Code follows style guidelines
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] No secrets in code
- [ ] Commit messages follow format
- [ ] PR description is clear
- [ ] Related issues referenced

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

**Thank you for contributing!** 🎉
