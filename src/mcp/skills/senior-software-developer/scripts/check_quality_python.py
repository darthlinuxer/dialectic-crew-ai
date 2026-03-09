#!/usr/bin/env python3
"""
Python code quality checker
Runs black, ruff, mypy, and pytest with coverage
"""

import subprocess
import sys
from pathlib import Path


class Colors:
    """Terminal colors for output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_section(title: str) -> None:
    """Print a section header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{title}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")


def run_command(command: list[str], description: str) -> tuple[bool, str]:
    """
    Run a shell command and return success status and output
    
    Args:
        command: Command to run as list of strings
        description: Human-readable description for logging
        
    Returns:
        Tuple of (success: bool, output: str)
    """
    print(f"{Colors.YELLOW}Running: {description}...{Colors.RESET}")
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, cwd=Path.cwd()
        )

        if result.returncode == 0:
            print(f"{Colors.GREEN}✓ {description} passed{Colors.RESET}")
            return True, result.stdout
        else:
            print(f"{Colors.RED}✗ {description} failed{Colors.RESET}")
            print(result.stdout)
            print(result.stderr)
            return False, result.stderr

    except FileNotFoundError:
        print(
            f"{Colors.RED}✗ {description} - Command not found: {command[0]}{Colors.RESET}"
        )
        print(
            f"  Install with: uv pip install {command[0]} or add to pyproject.toml"
        )
        return False, f"Command not found: {command[0]}"


def check_python_files() -> bool:
    """Check if there are Python files to analyze"""
    python_files = list(Path.cwd().rglob("*.py"))
    if not python_files:
        print(f"{Colors.YELLOW}No Python files found in current directory{Colors.RESET}")
        return False
    return True


def main() -> int:
    """Main entry point"""
    print(f"{Colors.BOLD}Python Code Quality Check{Colors.RESET}")
    print(f"Working directory: {Path.cwd()}")

    if not check_python_files():
        return 1

    all_passed = True
    results = []

    # 1. Black - Code formatting
    print_section("1. Black - Code Formatting")
    passed, output = run_command(
        ["black", "--check", "--diff", "."], "Black formatting check"
    )
    results.append(("Black", passed))
    if not passed:
        all_passed = False
        print(f"\n{Colors.YELLOW}To fix: black .{Colors.RESET}")

    # 2. Ruff - Linting
    print_section("2. Ruff - Linting")
    passed, output = run_command(["ruff", "check", "."], "Ruff linting")
    results.append(("Ruff", passed))
    if not passed:
        all_passed = False
        print(f"\n{Colors.YELLOW}To fix: ruff check --fix .{Colors.RESET}")

    # 3. Mypy - Type checking
    print_section("3. Mypy - Type Checking")
    passed, output = run_command(["mypy", "."], "Mypy type checking")
    results.append(("Mypy", passed))
    if not passed:
        all_passed = False

    # 4. Pytest - Tests with coverage
    print_section("4. Pytest - Tests with Coverage")
    
    # Check if tests directory exists
    tests_exist = (
        Path("tests").exists()
        or Path("test").exists()
        or list(Path.cwd().rglob("test_*.py"))
    )

    if tests_exist:
        passed, output = run_command(
            [
                "pytest",
                "--cov=.",
                "--cov-report=term-missing",
                "--cov-report=html",
                "-v",
            ],
            "Pytest with coverage",
        )
        results.append(("Pytest", passed))
        if not passed:
            all_passed = False
        else:
            print(
                f"\n{Colors.GREEN}Coverage report generated in htmlcov/index.html{Colors.RESET}"
            )
    else:
        print(f"{Colors.YELLOW}No tests found (tests/ dir or test_*.py files){Colors.RESET}")
        results.append(("Pytest", None))

    # Summary
    print_section("Summary")
    for tool, status in results:
        if status is True:
            print(f"  {Colors.GREEN}✓{Colors.RESET} {tool}")
        elif status is False:
            print(f"  {Colors.RED}✗{Colors.RESET} {tool}")
        else:
            print(f"  {Colors.YELLOW}⊘{Colors.RESET} {tool} (skipped)")

    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All checks passed!{Colors.RESET}\n")
        return 0
    else:
        print(
            f"\n{Colors.RED}{Colors.BOLD}Some checks failed. Please fix the issues above.{Colors.RESET}\n"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
