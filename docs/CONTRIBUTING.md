# Contributing to HuskyCat

## Development Setup

```bash
# Clone and setup
git clone https://gitlab.com/tinyland/ai/huskycat.git
cd huskycat
uv sync --dev
npm run hooks:install
```

## Code Standards

- Python: Black formatting, Ruff linting, MyPy type checking
- Commits: Conventional commits format (`feat:`, `fix:`, `docs:`, etc.)
- Tests: pytest with hypothesis for property-based testing

## Development Workflow

1. Create feature branch from `main`
2. Make changes with passing tests
3. Run validation: `npm run validate`
4. Commit with conventional format
5. Push and create merge request

## Testing

```bash
# Run all tests
npm run test:all

# Run specific tests
uv run pytest tests/test_mode_detection.py -v

# With coverage
uv run pytest --cov=src/huskycat --cov-report=html
```

## Pull Request Checklist

- [ ] Tests pass: `npm run test:all`
- [ ] Validation passes: `npm run validate`
- [ ] Conventional commit format used
- [ ] Documentation updated if needed

## Reporting Issues

Use GitLab Issues: https://gitlab.com/tinyland/ai/huskycat/-/issues

Include:
- HuskyCat version (`huskycat --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
