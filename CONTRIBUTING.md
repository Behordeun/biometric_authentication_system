# Contributing to Hybrid Passwordless Authentication System

Thank you for your interest in contributing! This guide will help you get started.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a welcoming environment

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd authentication_system

# Start services
make docker-up

# Or manually
cd docker && docker-compose up -d
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Changes

- Write clean, readable code
- Follow existing code style
- Add tests for new features
- Update documentation

### 3. Code Quality

```bash
# Format code
cd backend
black app/
isort app/
autoflake --remove-all-unused-imports -i app/

# Run tests
pytest
```

### 4. Commit Changes

```bash
# Stage changes
git add .

# Commit (pre-commit hooks will run automatically)
git commit -m "feat: add new feature"
```

**Commit Message Format:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Project Structure

```
authentication_system/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API routes
│   │   ├── core/     # Core utilities
│   │   ├── db/       # Database models
│   │   └── services/ # Business logic
├── frontend/         # React frontend
├── docker/           # Docker configs
├── docs/             # Documentation
└── tests/            # Test files
```

## Coding Standards

### Python (Backend)

- Follow PEP 8
- Use type hints
- Maximum line length: 88 characters (Black default)
- Use async/await for I/O operations
- Write docstrings for public functions

```python
async def example_function(param: str) -> dict:
    """
    Brief description.

    Args:
        param: Parameter description

    Returns:
        Description of return value
    """
    return {"result": param}
```

### TypeScript (Frontend)

- Use functional components with hooks
- Use TypeScript for type safety
- Follow React best practices
- Use meaningful variable names

```typescript
const ExampleComponent: React.FC = () => {
  const [state, setState] = useState<string>('');

  return <div>{state}</div>;
};
```

## Testing

### Backend Tests

```bash
cd backend
pytest tests/
pytest tests/test_auth.py -v
```

### Frontend Tests

```bash
cd frontend
npm test
```

## Security

- **Never commit secrets** (pre-commit hooks will catch this)
- Use environment variables for configuration
- Follow OWASP security guidelines
- Report security issues privately

## Documentation

- Update README.md for user-facing changes
- Update relevant docs/ files
- Add inline comments for complex logic
- Update API documentation

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows project style
- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Pre-commit hooks pass
- [ ] No merge conflicts

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated
- [ ] Documentation updated
```

## Areas for Contribution

### High Priority

- [ ] Additional authentication methods
- [ ] Enhanced audit logging
- [ ] Performance optimizations
- [ ] Test coverage improvements

### Good First Issues

- [ ] Documentation improvements
- [ ] Code formatting fixes
- [ ] Minor bug fixes
- [ ] UI/UX enhancements

### Advanced Features

- [ ] Multi-tenant support
- [ ] Advanced rate limiting
- [ ] Monitoring dashboards
- [ ] Additional OAuth providers

## Getting Help

- Check [documentation](docs/)
- Review existing issues
- Ask questions in discussions
- Join community chat

## Review Process

1. **Automated Checks**: CI/CD runs tests and linters
2. **Code Review**: Maintainers review code quality
3. **Testing**: Changes tested in staging
4. **Approval**: At least one maintainer approval required
5. **Merge**: Squash and merge to main branch

## Release Process

- Semantic versioning (MAJOR.MINOR.PATCH)
- Changelog updated for each release
- Tagged releases on main branch

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue for questions or clarifications.

---

Thank you for contributing! 🎉
