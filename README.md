# alix - Interactive Alias Manager for Your Shell 🚀

A powerful, htop-style terminal UI for managing shell aliases. Never forget a command again!

![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Shell](https://img.shields.io/badge/shell-bash%20|%20zsh%20|%20fish-lightgrey.svg)
![CI](https://github.com/YOUR_FORK_USERNAME/alix-cli/workflows/CI/badge.svg)


## ✨ Features

- **Interactive TUI**: Beautiful terminal interface inspired by htop
- **Multi-Shell Support**: Works with bash, zsh, and fish
- **Smart Search**: Real-time filtering and searching
- **Auto-Backup**: Automatic backups before every change
- **Import/Export**: Share alias collections with your team
- **Shell Integration**: Apply aliases directly to your shell config
- **Usage Tracking & Analytics**: Track alias usage with detailed statistics
- **Automatic Tracking**: Set up automatic usage tracking for all aliases
- **Productivity Metrics**: See which aliases save you the most time
- **Usage History**: View detailed usage patterns and trends
- **Alias Templates**: Pre-built alias collections for common tools (git, docker, k8s)
- **Template Marketplace**: Extensible template system for custom alias collections
- **Themes**: Multiple color themes (ocean, forest, monochrome)
- **Safe Operations**: Confirmation prompts for destructive actions

## 🚀 Quick Start

### Installation

#### macOS

```bash
# Using Homebrew to install Python (if needed)
brew install python@3.11

# Clone the repository
git clone https://github.com/TheDevOpsBlueprint/alix-cli.git
cd alix-cli

# Create virtual environment
python3 -m venv alix-venv
source alix-venv/bin/activate

# Install alix
pip install -e .

# Run alix
alix
```

#### Linux (Ubuntu/Debian)

```bash
# Install Python and dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Clone the repository
git clone https://github.com/TheDevOpsBlueprint/alix-cli.git
cd alix-cli

# Create virtual environment
python3 -m venv alix-venv
source alix-venv/bin/activate

# Install alix
pip install -e .

# Run alix
alix
```

#### Linux (Fedora/RHEL/CentOS)

```bash
# Install Python and dependencies
sudo dnf install python3 python3-pip

# Clone the repository
git clone https://github.com/TheDevOpsBlueprint/alix-cli.git
cd alix-cli

# Create virtual environment
python3 -m venv alix-venv
source alix-venv/bin/activate

# Install alix
pip install -e .

# Run alix
alix
```

#### Arch Linux

```bash
# Install Python and dependencies
sudo pacman -S python python-pip

# Clone and install (same as above)
git clone https://github.com/TheDevOpsBlueprint/alix-cli.git
cd alix-cli
python3 -m venv alix-venv
source alix-venv/bin/activate
pip install -e .
alix
```

#### Using Make (Easiest)

```bash
# Clone the repository
git clone https://github.com/TheDevOpsBlueprint/alix-cli.git
cd alix-cli

# Install with make
make dev-install  # Creates venv and installs everything
make run          # Run alix
```

## 📖 Usage Guide

### Interactive Mode (Recommended)

Launch the interactive TUI by simply running:

```bash
alix
```

#### TUI Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `a` | Add | Add a new alias |
| `e` | Edit | Edit selected alias |
| `d` | Delete | Delete selected alias |
| `/` | Search | Focus search box |
| `ESC` | Clear | Clear search |
| `j`/`↓` | Down | Navigate down |
| `k`/`↑` | Up | Navigate up |
| `r` | Refresh | Reload from disk |
| `q` | Quit | Exit application |

### CLI Commands

#### Adding Aliases

```bash
# Interactive add
alix add

# Quick add with flags
alix add -n "gs" -c "git status" -d "Git status shortcut"

# Add complex commands
alix add -n "gpl" -c "git pull origin $(git branch --show-current)" -d "Pull current branch"

# Docker shortcuts
alix add -n "dps" -c "docker ps -a" -d "List all containers"
alix add -n "dex" -c "docker exec -it" -d "Docker exec interactive"
```

#### Listing Aliases

```bash
# List all aliases
alix list

# Beautiful table view
alix ls
```

#### Remove Aliases

```bash
# Remove an alias
alix remove <name>

# Example
alix remove gs
```

#### Usage Tracking Commands

```bash
# Track usage of an alias manually
alix track my-alias --context "working on project"

# View usage history and trends
alix history

# View history for specific alias
alix history --alias my-alias --days 30

# Set up automatic usage tracking
alix setup-tracking

# Create standalone tracking script
alix setup-tracking --standalone --output ~/.alix_tracking.sh

# Set up tracking for specific shell
alix setup-tracking --shell zsh --file ~/.zshrc
```

#### Apply to Shell

Apply your aliases to your shell configuration:

```bash
# Detect and apply to current shell
alix apply

# Apply to specific config file
alix apply --target ~/.zshrc

# Apply with preview what can be changed
alix apply --target ~/.zshrc --dry-run

# The command will:
# 1. Backup your current config
# 2. Add managed aliases section
# 3. Make them available after restart
```

Then reload your shell:
```bash
# For bash
source ~/.bashrc

# For zsh
source ~/.zshrc

# For fish
source ~/.config/fish/config.fish
```

#### Shell Tab Completion

Enable command completions for `alix` (bash, zsh, fish):

```bash
# Preview / generate the script
alix completion bash > ~/.config/alix/completions/alix.bash
alix completion zsh  > ~/.config/alix/completions/alix.zsh
alix completion fish > ~/.config/fish/completions/alix.fish

# One-shot install for your current shell (auto-detects)
alix completion --install

# Or during apply
alix apply --install-completions

# Manual sourcing (bash/zsh) if needed
echo 'source ~/.config/alix/completions/alix.bash' >> ~/.bashrc   # bash
echo 'source ~/.config/alix/completions/alix.zsh'  >> ~/.zshrc    # zsh

# Fish autoloads from ~/.config/fish/completions/
```

After installation, restart your terminal or source your shell config to enable completions.

#### Import/Export

Share your alias collections:

```bash
# Export to JSON
alix export --output my-aliases.json

# Export to YAML
alix export --output my-aliases.yaml --format yaml

# Import aliases (merge with existing)
alix import my-aliases.json --merge

# Import without merging (skip duplicates)
alix import team-aliases.json
```

#### Alias Templates

Quickly import pre-built alias collections for common development tools:

```bash
# List available templates
alix templates list

# Import git aliases
alix templates add git

# Preview docker aliases before importing
alix templates add docker --dry-run

# Import specific aliases from kubernetes template
alix templates add k8s --aliases kgp,kgs,klog

# Import entire category (all templates in a category)
alix templates add-category docker

# Apply imported aliases to your shell
alix apply
```

**Available Templates:**
- **Git**: Version control shortcuts (gs, ga, gc, gp, gl, gb, gco, gd)
- **Docker**: Container management (di, dc, dca, dr, db, de, dl, drm)
- **Kubernetes**: Cluster management (k, kgp, kgs, kgd, kgn, kl, kd, kctx)

**Custom Templates:**
Users can add their own templates by creating YAML files in `alix/templates/`:

```yaml
version: "1.0"
category: "python"
description: "Python development aliases"
aliases:
  - name: "py"
    command: "python"
    description: "Run Python interpreter"
    tags: ["python", "dev"]
  - name: "pipi"
    command: "pip install"
    description: "Install Python packages"
    tags: ["python", "pip"]
```

#### Usage Tracking & Analytics

Track your alias usage and productivity gains with comprehensive analytics:

```bash
# View comprehensive statistics
alix stats

# View detailed analytics with usage patterns
alix stats --detailed

# Export analytics data for analysis
alix stats --export analytics.json

# Manually track usage of an alias
alix track my-alias --context "working on project"

# View usage history and trends
alix history

# View history for specific alias
alix history --alias my-alias

# Set up automatic usage tracking
alix setup-tracking

# Create standalone tracking script
alix setup-tracking --standalone --output ~/.alix_tracking.sh
```

**Analytics Features:**
- **Usage Frequency**: Track how often each alias is used
- **Productivity Metrics**: See which aliases save the most keystrokes
- **Usage Patterns**: View daily, weekly, and monthly usage trends
- **Unused Aliases**: Identify aliases that are never used
- **Recently Used**: See which aliases you've used recently
- **Context Tracking**: Track usage context (working directory, etc.)
- **Export/Import**: Share analytics data across systems

**Example Output:**
```
📊 Alias Statistics & Analytics

Total Aliases: 15
Total Uses: 1,247
Characters Saved: ~3,450 keystrokes
Average Usage per Alias: 83.1
Most Used: ll (156 times)
Unused Aliases: 2
Recently Used (7 days): 8

📈 Detailed Usage Analytics

⚠️  Unused Aliases (2):
  • old-alias
  • unused-command

🔥 Recently Used (7 days):
  • ll - 23 uses
  • gst - 15 uses

💪 Most Productive Aliases:
  Rank  Alias  Chars Saved  Usage Count
  1.     gst    saves 7     156
  2.     ll     saves 4     89
```

#### Configuration

Manage alix settings:

```bash
# Show current config
alix config

# Change theme
alix config --theme ocean

# Available themes:
# - default (cyan/blue)
# - ocean (blue tones)
# - forest (green tones)
# - monochrome (black & white)

# Toggle settings
alix config --auto-backup true
alix config --confirm-delete false
```

## 🎨 Real-World Examples

### DevOps Aliases

```bash
# Kubernetes shortcuts
alix add -n "k" -c "kubectl" -d "Kubectl shortcut"
alix add -n "kgp" -c "kubectl get pods" -d "Get pods"
alix add -n "kgs" -c "kubectl get services" -d "Get services"
alix add -n "kaf" -c "kubectl apply -f" -d "Apply file"
alix add -n "kdel" -c "kubectl delete" -d "Delete resource"
alix add -n "klog" -c "kubectl logs -f" -d "Follow logs"

# Docker shortcuts
alix add -n "dcu" -c "docker-compose up -d" -d "Compose up detached"
alix add -n "dcd" -c "docker-compose down" -d "Compose down"
alix add -n "dcl" -c "docker-compose logs -f" -d "Compose logs"
alix add -n "dprune" -c "docker system prune -af" -d "Clean docker system"

# Terraform shortcuts
alix add -n "tf" -c "terraform" -d "Terraform shortcut"
alix add -n "tfi" -c "terraform init" -d "Terraform init"
alix add -n "tfp" -c "terraform plan" -d "Terraform plan"
alix add -n "tfa" -c "terraform apply -auto-approve" -d "Terraform apply"
```

### Git Workflow

```bash
# Git shortcuts
alix add -n "gs" -c "git status" -d "Git status"
alix add -n "ga" -c "git add ." -d "Stage all changes"
alix add -n "gc" -c "git commit -m" -d "Git commit"
alix add -n "gp" -c "git push" -d "Git push"
alix add -n "gpl" -c "git pull" -d "Git pull"
alix add -n "gco" -c "git checkout" -d "Git checkout"
alix add -n "gcb" -c "git checkout -b" -d "Create new branch"
alix add -n "glog" -c "git log --oneline --graph --decorate" -d "Pretty git log"
alix add -n "gdiff" -c "git diff --staged" -d "Show staged changes"
```

### System Administration

```bash
# System monitoring
alix add -n "ports" -c "sudo lsof -i -P -n | grep LISTEN" -d "List listening ports"
alix add -n "myip" -c "curl -s ifconfig.me" -d "Get public IP"
alix add -n "diskspace" -c "df -h | grep -E '^/dev/'" -d "Check disk space"
alix add -n "meminfo" -c "free -h" -d "Memory information"
alix add -n "cpuinfo" -c "lscpu | grep -E 'Model name|Socket|Core'" -d "CPU information"

# Network utilities
alix add -n "flushdns" -c "sudo systemd-resolve --flush-caches" -d "Flush DNS cache"
alix add -n "listening" -c "netstat -tuln" -d "Show listening ports"
alix add -n "connections" -c "ss -tunap" -d "Show network connections"
```

## 📁 Data Storage

Alix stores data in your home directory:

```
~/.alix/
├── aliases.json       # Main alias storage
├── config.json        # Configuration settings
└── backups/          # Automatic backups
    ├── aliases_20250117_103000.json
    └── aliases_20250117_143000.json
```

### Alias Structure

```json
{
  "gs": {
    "name": "gs",
    "command": "git status",
    "description": "Git status shortcut",
    "tags": ["git", "vcs"],
    "created_at": "2025-01-17T10:30:00",
    "used_count": 42,
    "shell": "zsh"
  }
}
```

## 🔧 Advanced Configuration

### Shell Integration

Alix automatically detects your shell and modifies the appropriate config file:

| Shell | Config Files (in priority order) |
|-------|----------------------------------|
| Bash | `.bash_aliases`, `.bashrc`, `.bash_profile` |
| Zsh | `.zsh_aliases`, `.zshrc` |
| Fish | `.config/fish/config.fish` |

### Environment Variables

```bash
# Custom storage location (optional)
export ALIX_HOME=/custom/path

# Disable colored output
export NO_COLOR=1
```

### Shell Aliases for Alix

Add to your shell config for quick access:

```bash
# Quick shortcuts
alias a='alix'
alias aa='alix add'
alias al='alix list'
alias as='alix stats'
```

## 🧪 Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/TheDevOpsBlueprint/alix-cli.git
cd alix-cli

# Using make (recommended)
make dev-install
make test

# Or manually
python3 -m venv alix-venv
source alix-venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

### Project Structure

```
alix-cli/
├── alix/
│   ├── __init__.py
│   ├── cli.py              # CLI commands
│   ├── tui.py              # Terminal UI
│   ├── models.py           # Data models
│   ├── storage.py          # Storage backend
│   ├── config.py           # Configuration
│   ├── shell_integrator.py # Shell integration
│   ├── shell_detector.py   # Shell detection
│   └── porter.py           # Import/export
│   └── render.py           # CLI UI templates
├── tests/
│   ├── test_cli.py
│   ├── test_models.py
│   └── test_storage.py
├── Makefile
├── pyproject.toml
├── CONTRIBUTING.md
└── README.md
```

## 🤝 Contributing

We follow strict PR guidelines for quality:

1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. **Keep PRs small** - Maximum 80 lines per PR
4. **Test** your changes
5. **Submit** Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 🐛 Troubleshooting

### Common Issues

**Issue: `alix: command not found`**
```bash
# Ensure virtual environment is activated
source alix-venv/bin/activate

# Or add to PATH
export PATH="$HOME/alix-cli/alix-venv/bin:$PATH"
```

**Issue: Aliases not appearing in shell**
```bash
# After running 'alix apply', reload your shell
source ~/.bashrc  # or ~/.zshrc

# Check if aliases section exists
grep "ALIX MANAGED" ~/.bashrc
```

**Issue: TUI colors not displaying correctly**
```bash
# Set proper terminal encoding
export TERM=xterm-256color
export LC_ALL=en_US.UTF-8
```

**Issue: Permission denied errors**
```bash
# Fix permissions
chmod 755 ~/.alix
chmod 644 ~/.alix/aliases.json
```

## 📊 Performance

- **Instant startup**: < 50ms to launch TUI
- **Efficient storage**: JSON format for fast read/write
- **Smart backups**: Only keeps last 10 backups
- **Lightweight**: ~200KB total footprint

## 🛡️ Security

- **No cloud sync**: All data stored locally
- **Safe operations**: Automatic backups before changes
- **Shell injection protection**: Commands are properly escaped
- **Confirmation prompts**: For destructive operations

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal formatting
- [Textual](https://textual.textualize.io/) - Terminal UI framework
- [Python](https://python.org/) - Programming language

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/TheDevOpsBlueprint/alix-cli/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TheDevOpsBlueprint/alix-cli/discussions)
- **Email**: valentin.v.todorov@gmail.com

---

**Made with ❤️ by TheDevOpsBlueprint** | [⭐ Star us on GitHub](https://github.com/TheDevOpsBlueprint/alix-cli)
