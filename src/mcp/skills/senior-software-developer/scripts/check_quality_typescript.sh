#!/bin/bash
# check_quality_typescript.sh
# TypeScript code quality checker
# Runs tsc, eslint, prettier, and jest with coverage

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

# Check for TypeScript files
TS_FILES=$(find . -name "*.ts" ! -name "*.d.ts" ! -path "*/node_modules/*" | head -n 1)

if [ -z "$TS_FILES" ]; then
    print_error "No TypeScript files found in current directory"
    exit 1
fi

echo -e "${BOLD}TypeScript Code Quality Check${NC}"
echo "Working directory: $(pwd)"
echo ""

# Check for node_modules
if [ ! -d "node_modules" ]; then
    print_warning "node_modules not found. Run 'npm install' first."
    exit 1
fi

ALL_PASSED=true

# 1. TypeScript compiler - Type checking
print_section "1. tsc - TypeScript Compiler"

if [ -f "tsconfig.json" ]; then
    print_info "Running: tsc --noEmit..."
    
    if npx tsc --noEmit; then
        print_success "TypeScript compilation passed"
    else
        print_error "TypeScript compilation failed"
        ALL_PASSED=false
    fi
else
    print_warning "tsconfig.json not found - skipping tsc"
    print_info "Create tsconfig.json with: npx tsc --init"
fi

# 2. ESLint - Linting
print_section "2. ESLint - Linting"

if [ -f ".eslintrc.js" ] || [ -f ".eslintrc.json" ] || [ -f ".eslintrc.yml" ] || grep -q '"eslintConfig"' package.json 2>/dev/null; then
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
        if npx eslint . --ext .ts,.tsx; then
            print_success "ESLint passed"
        else
            print_error "ESLint failed"
            print_info "To fix: npx eslint . --ext .ts,.tsx --fix"
            ALL_PASSED=false
        fi
    fi
else
    print_warning "ESLint config not found"
    print_info "Initialize with: npm init @eslint/config"
fi

# 3. Prettier - Code formatting
print_section "3. Prettier - Code Formatting"

if [ -f ".prettierrc" ] || [ -f ".prettierrc.json" ] || [ -f ".prettierrc.yml" ] || [ -f "prettier.config.js" ] || grep -q '"prettier"' package.json 2>/dev/null; then
    print_info "Running: prettier --check..."
    
    if npx prettier --check "**/*.{ts,tsx,js,jsx,json}"; then
        print_success "Prettier check passed"
    else
        print_error "Prettier check failed"
        print_info "To fix: npx prettier --write \"**/*.{ts,tsx,js,jsx,json}\""
        ALL_PASSED=false
    fi
else
    print_warning "Prettier config not found"
    print_info "Create .prettierrc with your formatting preferences"
fi

# 4. Jest - Tests with coverage
print_section "4. Jest - Tests with Coverage"

if [ -f "jest.config.js" ] || [ -f "jest.config.ts" ] || grep -q '"jest"' package.json 2>/dev/null; then
    print_info "Running: jest --coverage..."
    
    # Check if test script exists
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
    print_warning "Jest config not found (jest.config.js or jest config in package.json)"
    print_info "Install with: npm install --save-dev jest @types/jest ts-jest"
fi

# Summary
print_section "Summary"

if [ "$ALL_PASSED" = true ]; then
    echo -e "  ${GREEN}✓${NC} TypeScript compilation"
    echo -e "  ${GREEN}✓${NC} ESLint"
    echo -e "  ${GREEN}✓${NC} Prettier"
    echo -e "  ${GREEN}✓${NC} Jest tests"
    echo ""
    echo -e "${GREEN}${BOLD}All checks passed!${NC}\n"
    exit 0
else
    echo -e "  ${RED}✗${NC} Some checks failed"
    echo ""
    echo -e "${RED}${BOLD}Some checks failed. Please fix the issues above.${NC}\n"
    exit 1
fi
