#!/bin/bash
# check_quality_nodejs.sh
# Node.js code quality checker
# Runs eslint, prettier, and jest/vitest with coverage

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_section() {
    echo -e "\n${BLUE}${BOLD}============================================================${NC}"
    echo -e "${BLUE}${BOLD}$1${NC}"
    echo -e "${BLUE}${BOLD}============================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⊘ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}$1${NC}"
}

# Check for JavaScript files (excluding TypeScript)
JS_FILES=$(find . -name "*.js" -o -name "*.mjs" -o -name "*.cjs" ! -path "*/node_modules/*" | head -n 1)

if [ -z "$JS_FILES" ]; then
    print_error "No JavaScript files found in current directory"
    exit 1
fi

# Check if this is actually a TypeScript project
if [ -f "tsconfig.json" ]; then
    print_warning "This appears to be a TypeScript project (tsconfig.json found)"
    print_info "Use check_quality_typescript.sh instead"
    exit 1
fi

echo -e "${BOLD}Node.js Code Quality Check${NC}"
echo "Working directory: $(pwd)"
echo ""

# Check for node_modules
if [ ! -d "node_modules" ]; then
    print_warning "node_modules not found. Run 'npm install' first."
    exit 1
fi

ALL_PASSED=true

# 1. ESLint - Linting
print_section "1. ESLint - Linting"

if [ -f ".eslintrc.js" ] || [ -f ".eslintrc.json" ] || [ -f ".eslintrc.yml" ] || [ -f "eslint.config.js" ] || grep -q '"eslintConfig"' package.json 2>/dev/null; then
    print_info "Running: eslint..."
    
    # Try with npm script first, fallback to npx
    if grep -q '"lint"' package.json 2>/dev/null; then
        if npm run lint; then
            print_success "ESLint passed"
        else
            print_error "ESLint failed"
            print_info "To fix: npm run lint -- --fix"
            ALL_PASSED=false
        fi
    else
        if npx eslint . --ext .js,.mjs,.cjs; then
            print_success "ESLint passed"
        else
            print_error "ESLint failed"
            print_info "To fix: npx eslint . --ext .js,.mjs,.cjs --fix"
            ALL_PASSED=false
        fi
    fi
else
    print_warning "ESLint config not found"
    print_info "Initialize with: npm init @eslint/config"
fi

# 2. Prettier - Code formatting
print_section "2. Prettier - Code Formatting"

if [ -f ".prettierrc" ] || [ -f ".prettierrc.json" ] || [ -f ".prettierrc.yml" ] || [ -f "prettier.config.js" ] || grep -q '"prettier"' package.json 2>/dev/null; then
    print_info "Running: prettier --check..."
    
    if npx prettier --check "**/*.{js,mjs,cjs,json}"; then
        print_success "Prettier check passed"
    else
        print_error "Prettier check failed"
        print_info "To fix: npx prettier --write \"**/*.{js,mjs,cjs,json}\""
        ALL_PASSED=false
    fi
else
    print_warning "Prettier config not found"
    print_info "Create .prettierrc with your formatting preferences"
fi

# 3. Tests with coverage (Jest or Vitest)
print_section "3. Tests with Coverage"

# Detect test framework
if grep -q '"vitest"' package.json 2>/dev/null; then
    TEST_FRAMEWORK="vitest"
    print_info "Detected: Vitest"
    print_info "Running: vitest run --coverage..."
    
    if npx vitest run --coverage; then
        print_success "Vitest tests passed"
        
        if [ -d "coverage" ]; then
            print_success "Coverage report generated in coverage/index.html"
        fi
    else
        print_error "Vitest tests failed"
        ALL_PASSED=false
    fi
    
elif grep -q '"jest"' package.json 2>/dev/null || [ -f "jest.config.js" ] || [ -f "jest.config.mjs" ]; then
    TEST_FRAMEWORK="jest"
    print_info "Detected: Jest"
    print_info "Running: jest --coverage..."
    
    if grep -q '"test"' package.json 2>/dev/null; then
        if npm test -- --coverage --passWithNoTests; then
            print_success "Jest tests passed"
            
            if [ -d "coverage" ]; then
                print_success "Coverage report generated in coverage/lcov-report/index.html"
            fi
        else
            print_error "Jest tests failed"
            ALL_PASSED=false
        fi
    else
        if npx jest --coverage --passWithNoTests; then
            print_success "Jest tests passed"
            
            if [ -d "coverage" ]; then
                print_success "Coverage report generated in coverage/lcov-report/index.html"
            fi
        else
            print_error "Jest tests failed"
            ALL_PASSED=false
        fi
    fi
else
    print_warning "No test framework detected (jest or vitest)"
    print_info "Install Jest: npm install --save-dev jest"
    print_info "Install Vitest: npm install --save-dev vitest @vitest/coverage-v8"
fi

# 4. Node.js security check (optional but recommended)
print_section "4. Security Audit"

print_info "Running: npm audit..."

if npm audit --audit-level=moderate; then
    print_success "No security vulnerabilities found"
else
    print_warning "Security vulnerabilities detected"
    print_info "Review vulnerabilities above. Fix with: npm audit fix"
    # Don't fail overall check for security issues (they might be in devDependencies)
fi

# Summary
print_section "Summary"

if [ "$ALL_PASSED" = true ]; then
    echo -e "  ${GREEN}✓${NC} ESLint"
    echo -e "  ${GREEN}✓${NC} Prettier"
    echo -e "  ${GREEN}✓${NC} Tests"
    echo ""
    echo -e "${GREEN}${BOLD}All checks passed!${NC}\n"
    exit 0
else
    echo -e "  ${RED}✗${NC} Some checks failed"
    echo ""
    echo -e "${RED}${BOLD}Some checks failed. Please fix the issues above.${NC}\n"
    exit 1
fi
