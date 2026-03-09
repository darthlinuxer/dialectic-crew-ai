#!/bin/bash
# check_quality_csharp.sh
# C# code quality checker
# Runs dotnet format, dotnet build, and dotnet test with coverage

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

# Find solution or project files
SOLUTION_FILE=$(find . -maxdepth 2 -name "*.sln" | head -n 1)
PROJECT_FILES=$(find . -maxdepth 3 -name "*.csproj")

if [ -z "$SOLUTION_FILE" ] && [ -z "$PROJECT_FILES" ]; then
    print_error "No .sln or .csproj files found in current directory"
    exit 1
fi

if [ -n "$SOLUTION_FILE" ]; then
    TARGET="$SOLUTION_FILE"
    echo -e "${BOLD}C# Code Quality Check${NC}"
    echo "Target: Solution file - $SOLUTION_FILE"
else
    TARGET="."
    echo -e "${BOLD}C# Code Quality Check${NC}"
    echo "Target: Project files in current directory"
fi

echo ""

ALL_PASSED=true

# 1. dotnet format - Code formatting
print_section "1. dotnet format - Code Formatting"

if command -v dotnet-format &> /dev/null || dotnet format --version &> /dev/null 2>&1; then
    print_info "Running: dotnet format --verify-no-changes..."
    
    if dotnet format "$TARGET" --verify-no-changes --verbosity quiet; then
        print_success "Code formatting check passed"
    else
        print_error "Code formatting check failed"
        print_info "To fix: dotnet format"
        ALL_PASSED=false
    fi
else
    print_warning "dotnet-format not installed"
    print_info "Install with: dotnet tool install -g dotnet-format"
fi

# 2. dotnet build - Compilation
print_section "2. dotnet build - Compilation"

print_info "Running: dotnet build..."

if dotnet build "$TARGET" --configuration Release --verbosity quiet; then
    print_success "Build passed"
else
    print_error "Build failed"
    ALL_PASSED=false
fi

# 3. Analyzers (built into build, but let's be explicit)
print_section "3. Code Analyzers"

print_info "Running: dotnet build with warnings as errors..."

if dotnet build "$TARGET" --configuration Release --verbosity quiet /p:TreatWarningsAsErrors=true; then
    print_success "No analyzer warnings"
else
    print_warning "Analyzer warnings found (not failing overall check)"
    print_info "Review warnings above and fix as appropriate"
fi

# 4. dotnet test - Tests with coverage
print_section "4. dotnet test - Tests with Coverage"

TEST_PROJECTS=$(find . -name "*Tests.csproj" -o -name "*Test.csproj" -o -name "*.Tests.csproj")

if [ -n "$TEST_PROJECTS" ]; then
    print_info "Running: dotnet test with coverage..."
    
    if dotnet test "$TARGET" \
        --configuration Release \
        --verbosity quiet \
        --collect:"XPlat Code Coverage" \
        --results-directory ./TestResults \
        -- DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=opencover; then
        
        print_success "Tests passed"
        
        # Try to generate coverage report if reportgenerator is installed
        if command -v reportgenerator &> /dev/null; then
            print_info "Generating coverage report..."
            
            reportgenerator \
                "-reports:./TestResults/**/coverage.opencover.xml" \
                "-targetdir:./TestResults/CoverageReport" \
                "-reporttypes:Html;TextSummary" \
                > /dev/null 2>&1
            
            if [ -f "./TestResults/CoverageReport/Summary.txt" ]; then
                echo ""
                cat ./TestResults/CoverageReport/Summary.txt
                echo ""
            fi
            
            print_success "Coverage report generated in ./TestResults/CoverageReport/index.html"
        else
            print_info "Install reportgenerator for HTML coverage reports:"
            print_info "  dotnet tool install -g dotnet-reportgenerator-globaltool"
        fi
    else
        print_error "Tests failed"
        ALL_PASSED=false
    fi
else
    print_warning "No test projects found (*Tests.csproj, *Test.csproj)"
fi

# Summary
print_section "Summary"

if [ "$ALL_PASSED" = true ]; then
    echo -e "  ${GREEN}✓${NC} dotnet format"
    echo -e "  ${GREEN}✓${NC} dotnet build"
    echo -e "  ${GREEN}✓${NC} dotnet test"
    echo ""
    echo -e "${GREEN}${BOLD}All checks passed!${NC}\n"
    exit 0
else
    echo -e "  ${RED}✗${NC} Some checks failed"
    echo ""
    echo -e "${RED}${BOLD}Some checks failed. Please fix the issues above.${NC}\n"
    exit 1
fi
