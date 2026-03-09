#!/usr/bin/env python3
"""
Code Quality Checker
Runs various code quality tools and reports results.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple
import json


class QualityChecker:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = []
        
    def run_command(self, command: List[str], tool_name: str) -> Tuple[bool, str]:
        """Run a command and return success status and output."""
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, f"{tool_name} timed out after 5 minutes"
        except FileNotFoundError:
            return False, f"{tool_name} not found. Install it first."
        except Exception as e:
            return False, f"Error running {tool_name}: {str(e)}"
    
    def check_python(self):
        """Run Python code quality checks."""
        print("\n=== Python Code Quality ===")
        
        # Black - Code formatting
        print("Running black...")
        success, output = self.run_command(
            ["black", "--check", "--diff", "."],
            "black"
        )
        self.results.append(("Black (formatter)", success, output))
        
        # isort - Import sorting
        print("Running isort...")
        success, output = self.run_command(
            ["isort", "--check-only", "--diff", "."],
            "isort"
        )
        self.results.append(("isort (import sorting)", success, output))
        
        # flake8 - Linting
        print("Running flake8...")
        success, output = self.run_command(
            ["flake8", "."],
            "flake8"
        )
        self.results.append(("flake8 (linter)", success, output))
        
        # mypy - Type checking
        print("Running mypy...")
        success, output = self.run_command(
            ["mypy", "."],
            "mypy"
        )
        self.results.append(("mypy (type checker)", success, output))
        
        # pylint - Advanced linting
        print("Running pylint...")
        success, output = self.run_command(
            ["pylint", "src/"],
            "pylint"
        )
        self.results.append(("pylint (linter)", success, output))
        
        # pytest - Tests
        print("Running pytest...")
        success, output = self.run_command(
            ["pytest", "--cov=src", "--cov-report=term", "-v"],
            "pytest"
        )
        self.results.append(("pytest (tests)", success, output))
    
    def check_csharp(self):
        """Run C# code quality checks."""
        print("\n=== C# Code Quality ===")
        
        # dotnet format
        print("Running dotnet format...")
        success, output = self.run_command(
            ["dotnet", "format", "--verify-no-changes"],
            "dotnet format"
        )
        self.results.append(("dotnet format", success, output))
        
        # dotnet build
        print("Running dotnet build...")
        success, output = self.run_command(
            ["dotnet", "build", "/warnaserror"],
            "dotnet build"
        )
        self.results.append(("dotnet build", success, output))
        
        # dotnet test
        print("Running dotnet test...")
        success, output = self.run_command(
            ["dotnet", "test", "/p:CollectCoverage=true"],
            "dotnet test"
        )
        self.results.append(("dotnet test", success, output))
    
    def check_typescript(self):
        """Run TypeScript/Node.js code quality checks."""
        print("\n=== TypeScript Code Quality ===")
        
        # ESLint
        print("Running eslint...")
        success, output = self.run_command(
            ["npx", "eslint", "src/", "--ext", ".ts,.tsx"],
            "eslint"
        )
        self.results.append(("ESLint (linter)", success, output))
        
        # Prettier
        print("Running prettier...")
        success, output = self.run_command(
            ["npx", "prettier", "--check", "src/"],
            "prettier"
        )
        self.results.append(("Prettier (formatter)", success, output))
        
        # TypeScript compiler
        print("Running tsc...")
        success, output = self.run_command(
            ["npx", "tsc", "--noEmit"],
            "tsc"
        )
        self.results.append(("TypeScript compiler", success, output))
        
        # Jest tests
        print("Running jest...")
        success, output = self.run_command(
            ["npm", "test", "--", "--coverage"],
            "jest"
        )
        self.results.append(("Jest (tests)", success, output))
    
    def detect_project_type(self) -> List[str]:
        """Detect which project types are present."""
        project_types = []
        
        # Check for Python
        if (self.project_root / "setup.py").exists() or \
           (self.project_root / "pyproject.toml").exists() or \
           (self.project_root / "requirements.txt").exists():
            project_types.append("python")
        
        # Check for C#
        if list(self.project_root.glob("*.sln")) or \
           list(self.project_root.glob("**/*.csproj")):
            project_types.append("csharp")
        
        # Check for TypeScript/Node.js
        if (self.project_root / "package.json").exists():
            project_types.append("typescript")
        
        return project_types
    
    def generate_report(self):
        """Generate and print quality report."""
        print("\n" + "="*60)
        print("CODE QUALITY REPORT")
        print("="*60)
        
        passed = 0
        failed = 0
        
        for tool, success, output in self.results:
            status = "✓ PASS" if success else "✗ FAIL"
            if success:
                passed += 1
            else:
                failed += 1
            
            print(f"\n{status} - {tool}")
            if not success and output:
                # Show first 10 lines of error output
                lines = output.split('\n')[:10]
                for line in lines:
                    print(f"  {line}")
                if len(output.split('\n')) > 10:
                    print(f"  ... ({len(output.split('\n')) - 10} more lines)")
        
        print("\n" + "="*60)
        print(f"SUMMARY: {passed} passed, {failed} failed")
        print("="*60)
        
        return failed == 0


def main():
    """Main entry point."""
    project_root = Path.cwd()
    
    print(f"Checking code quality in: {project_root}")
    
    checker = QualityChecker(project_root)
    project_types = checker.detect_project_type()
    
    if not project_types:
        print("No supported project type detected.")
        print("Looking for: Python (setup.py, pyproject.toml), C# (*.sln, *.csproj), TypeScript/Node.js (package.json)")
        sys.exit(1)
    
    print(f"Detected project types: {', '.join(project_types)}")
    
    # Run checks for each detected project type
    for project_type in project_types:
        if project_type == "python":
            checker.check_python()
        elif project_type == "csharp":
            checker.check_csharp()
        elif project_type == "typescript":
            checker.check_typescript()
    
    # Generate report
    success = checker.generate_report()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
