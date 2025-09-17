# Contributing to alix-cli

## PR Guidelines

### Size Limits
- Maximum 80 lines of code per PR
- One feature/fix per PR
- Reference an issue in your PR

### Branch Naming
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `setup/` - Infrastructure
- `refactor/` - Code improvements

### Commit Messages
Use conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `style:` formatting
- `refactor:` code restructuring
- `test:` adding tests
- `chore:` maintenance

## Development Setup

### Option 1: Using Make (Recommended)
```bash
git clone git@github.com:TheDevOpsBlueprint/alix-cli.git
cd alix-cli
make dev-install  # Creates venv and installs everything
make test        # Run tests
make run         # Run alix