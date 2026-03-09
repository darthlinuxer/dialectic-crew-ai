#!/bin/bash
# setup_dev_environment.sh
# Sets up development environment with linters, formatters, and tools

set -e

echo "==================================="
echo "Development Environment Setup"
echo "==================================="

# Detect project types
HAS_PYTHON=false
HAS_CSHARP=false
HAS_NODE=false

if [ -f "setup.py" ] || [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
    HAS_PYTHON=true
fi

if [ -n "$(find . -maxdepth 2 -name '*.sln' -o -name '*.csproj' 2>/dev/null)" ]; then
    HAS_CSHARP=true
fi

if [ -f "package.json" ]; then
    HAS_NODE=true
fi

echo ""
echo "Detected project types:"
[ "$HAS_PYTHON" = true ] && echo "  ✓ Python"
[ "$HAS_CSHARP" = true ] && echo "  ✓ C#"
[ "$HAS_NODE" = true ] && echo "  ✓ Node.js/TypeScript"

# Python setup
if [ "$HAS_PYTHON" = true ]; then
    echo ""
    echo "=== Setting up Python environment ==="
    
    # Check for uv (modern Python package manager)
    if ! command -v uv &> /dev/null; then
        echo "❌ uv not found. Installing uv..."
        echo "   Visit https://github.com/astral-sh/uv for manual installation or:"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    echo "uv version: $(uv --version)"
    
    # Modern workflow with pyproject.toml
    if [ -f "pyproject.toml" ]; then
        echo "Found pyproject.toml - using modern uv workflow"
        
        # Check for .venv, create if it doesn't exist
        if [ ! -d ".venv" ]; then
            echo "Creating virtual environment with uv..."
            uv venv
        else
            echo "Found existing .venv"
        fi
        
        # Sync dependencies from pyproject.toml
        echo "Syncing dependencies with uv sync..."
        uv sync
        
        echo "✓ Python environment ready with uv sync"
        echo "  To activate: source .venv/bin/activate"
        
    # Legacy workflow with requirements.txt
    elif [ -f "requirements.txt" ]; then
        echo "Found requirements.txt - using legacy workflow"
        
        # Check for .venv, create if it doesn't exist
        if [ ! -d ".venv" ]; then
            echo "Creating virtual environment with uv..."
            uv venv
        else
            echo "Found existing .venv"
        fi
        
        # Install from requirements.txt
        echo "Installing dependencies with uv pip..."
        uv pip install -r requirements.txt
        
        # Install dev dependencies if available
        if [ -f "requirements-dev.txt" ]; then
            echo "Installing dev requirements..."
            uv pip install -r requirements-dev.txt
        fi
        
        echo "✓ Python environment ready with requirements.txt"
        echo "  To activate: source .venv/bin/activate"
        echo "  Consider migrating to pyproject.toml for modern workflow"
        
    # No dependency files found
    else
        echo "No pyproject.toml or requirements.txt found"
        
        # Create .venv anyway for development
        if [ ! -d ".venv" ]; then
            echo "Creating virtual environment with uv..."
            uv venv
        else
            echo "Found existing .venv"
        fi
        
        # Install standard dev tools
        echo "Installing standard dev tools..."
        uv pip install pytest pytest-cov black ruff mypy
        
        echo "✓ Python environment ready with dev tools"
        echo "  To activate: source .venv/bin/activate"
        echo "  Consider creating a pyproject.toml for dependency management"
    fi
    
    # Setup pre-commit hooks if config exists
    if [ -f ".pre-commit-config.yaml" ]; then
        echo "Setting up pre-commit hooks..."
        # Activate venv to access pre-commit
        source .venv/bin/activate
        
        # Install pre-commit if not present
        if ! command -v pre-commit &> /dev/null; then
            uv pip install pre-commit
        fi
        
        pre-commit install
        deactivate
    fi
fi

# C# setup
if [ "$HAS_CSHARP" = true ]; then
    echo ""
    echo "=== Setting up C# environment ==="
    
    # Check for .NET
    if ! command -v dotnet &> /dev/null; then
        echo "❌ .NET SDK not found. Please install .NET SDK"
        exit 1
    fi
    
    echo ".NET version: $(dotnet --version)"
    
    # Restore packages
    echo "Restoring NuGet packages..."
    dotnet restore
    
    # Install tools
    echo "Installing .NET tools..."
    dotnet tool restore 2>/dev/null || true
    
    # Install/update format tool
    if ! dotnet tool list -g | grep -q "dotnet-format"; then
        echo "Installing dotnet-format..."
        dotnet tool install -g dotnet-format
    fi
    
    echo "✓ C# environment ready"
fi

# Node.js/TypeScript setup
if [ "$HAS_NODE" = true ]; then
    echo ""
    echo "=== Setting up Node.js environment ==="
    
    # Check for Node.js
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js not found. Please install Node.js 18+"
        exit 1
    fi
    
    echo "Node.js version: $(node --version)"
    echo "npm version: $(npm --version)"
    
    # Install dependencies
    echo "Installing npm packages..."
    npm install
    
    # Install dev dependencies if they're not in package.json
    echo "Ensuring dev tools are installed..."
    npm install --save-dev \
        typescript \
        @typescript-eslint/eslint-plugin \
        @typescript-eslint/parser \
        eslint \
        prettier \
        jest \
        @types/jest \
        @types/node 2>/dev/null || true
    
    # Setup husky for git hooks if available
    if [ -d ".husky" ] || grep -q "husky" package.json 2>/dev/null; then
        echo "Setting up husky git hooks..."
        npm run prepare 2>/dev/null || npx husky install
    fi
    
    echo "✓ Node.js environment ready"
fi

# Git setup
echo ""
echo "=== Setting up Git configuration ==="

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
.venv/
venv/
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# C#
bin/
obj/
*.user
*.suo
.vs/
TestResults/
coverage/

# Node.js
node_modules/
dist/
build/
*.log
.env
coverage/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
EOF
    echo "✓ Created .gitignore"
fi

# EditorConfig
if [ ! -f ".editorconfig" ]; then
    echo "Creating .editorconfig..."
    cat > .editorconfig << 'EOF'
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.{py,pyi}]
indent_style = space
indent_size = 4

[*.{cs,csx}]
indent_style = space
indent_size = 4

[*.{js,ts,jsx,tsx,json}]
indent_style = space
indent_size = 2

[*.{yml,yaml}]
indent_style = space
indent_size = 2

[Makefile]
indent_style = tab
EOF
    echo "✓ Created .editorconfig"
fi

echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Quick reference commands:"

if [ "$HAS_PYTHON" = true ]; then
    echo ""
    echo "Python:"
    echo "  source .venv/bin/activate # Activate virtual environment"
    echo "  uv sync                   # Sync dependencies (pyproject.toml)"
    echo "  uv add <package>          # Add new dependency"
    echo "  uv pip install <package>  # Install package (legacy)"
    echo "  pytest                    # Run tests"
    echo "  black .                   # Format code"
    echo "  ruff check .              # Lint code"
    echo "  mypy .                    # Type check"
fi

if [ "$HAS_CSHARP" = true ]; then
    echo ""
    echo "C#:"
    echo "  dotnet build              # Build solution"
    echo "  dotnet test               # Run tests"
    echo "  dotnet format             # Format code"
fi

if [ "$HAS_NODE" = true ]; then
    echo ""
    echo "Node.js/TypeScript:"
    echo "  npm test                  # Run tests"
    echo "  npm run build             # Build project"
    echo "  npm run lint              # Lint code"
    echo "  npm run format            # Format code"
fi

echo ""
echo "To check overall code quality, run:"
echo "  python3 scripts/check_quality.py"
echo ""
