#!/usr/bin/env python3
"""
Test Coverage Report Generator
Generates and analyzes test coverage across different languages.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional
import json
import xml.etree.ElementTree as ET


class CoverageAnalyzer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.coverage_data = {}
        
    def run_python_coverage(self) -> Optional[Dict]:
        """Run Python test coverage with pytest."""
        print("Running Python test coverage...")
        
        try:
            # Run pytest with coverage
            subprocess.run(
                ["pytest", "--cov=src", "--cov-report=xml", "--cov-report=term"],
                cwd=self.project_root,
                check=True
            )
            
            # Parse coverage.xml
            coverage_file = self.project_root / "coverage.xml"
            if coverage_file.exists():
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                
                line_rate = float(root.attrib.get('line-rate', 0)) * 100
                branch_rate = float(root.attrib.get('branch-rate', 0)) * 100
                
                # Get per-file coverage
                files = {}
                for package in root.findall('.//package'):
                    for cls in package.findall('.//class'):
                        filename = cls.attrib.get('filename', '')
                        line_coverage = float(cls.attrib.get('line-rate', 0)) * 100
                        files[filename] = {
                            'line_coverage': line_coverage,
                            'lines_covered': int(cls.attrib.get('lines-covered', 0)),
                            'lines_valid': int(cls.attrib.get('lines-valid', 0))
                        }
                
                return {
                    'overall_line_coverage': line_rate,
                    'overall_branch_coverage': branch_rate,
                    'files': files
                }
        except subprocess.CalledProcessError:
            print("Python tests failed")
            return None
        except Exception as e:
            print(f"Error analyzing Python coverage: {e}")
            return None
    
    def run_csharp_coverage(self) -> Optional[Dict]:
        """Run C# test coverage with coverlet."""
        print("Running C# test coverage...")
        
        try:
            # Run dotnet test with coverage
            result = subprocess.run(
                [
                    "dotnet", "test",
                    "/p:CollectCoverage=true",
                    "/p:CoverletOutputFormat=cobertura",
                    "/p:CoverletOutput=./coverage/"
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse coverage.cobertura.xml
            coverage_file = self.project_root / "coverage" / "coverage.cobertura.xml"
            if coverage_file.exists():
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                
                line_rate = float(root.attrib.get('line-rate', 0)) * 100
                branch_rate = float(root.attrib.get('branch-rate', 0)) * 100
                
                # Get per-file coverage
                files = {}
                for cls in root.findall('.//class'):
                    filename = cls.attrib.get('filename', '')
                    line_coverage = float(cls.attrib.get('line-rate', 0)) * 100
                    files[filename] = {
                        'line_coverage': line_coverage
                    }
                
                return {
                    'overall_line_coverage': line_rate,
                    'overall_branch_coverage': branch_rate,
                    'files': files
                }
        except subprocess.CalledProcessError:
            print("C# tests failed")
            return None
        except Exception as e:
            print(f"Error analyzing C# coverage: {e}")
            return None
    
    def run_typescript_coverage(self) -> Optional[Dict]:
        """Run TypeScript/JavaScript test coverage with Jest."""
        print("Running TypeScript/JavaScript test coverage...")
        
        try:
            # Run Jest with coverage
            subprocess.run(
                ["npm", "test", "--", "--coverage", "--coverageReporters=json", "--coverageReporters=text"],
                cwd=self.project_root,
                check=True
            )
            
            # Parse coverage/coverage-summary.json
            coverage_file = self.project_root / "coverage" / "coverage-summary.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    data = json.load(f)
                
                total = data.get('total', {})
                
                files = {}
                for filepath, file_data in data.items():
                    if filepath != 'total':
                        files[filepath] = {
                            'line_coverage': file_data.get('lines', {}).get('pct', 0),
                            'branch_coverage': file_data.get('branches', {}).get('pct', 0),
                            'function_coverage': file_data.get('functions', {}).get('pct', 0),
                            'statement_coverage': file_data.get('statements', {}).get('pct', 0)
                        }
                
                return {
                    'overall_line_coverage': total.get('lines', {}).get('pct', 0),
                    'overall_branch_coverage': total.get('branches', {}).get('pct', 0),
                    'overall_function_coverage': total.get('functions', {}).get('pct', 0),
                    'overall_statement_coverage': total.get('statements', {}).get('pct', 0),
                    'files': files
                }
        except subprocess.CalledProcessError:
            print("TypeScript/JavaScript tests failed")
            return None
        except Exception as e:
            print(f"Error analyzing TypeScript/JavaScript coverage: {e}")
            return None
    
    def analyze_coverage_gaps(self, coverage_data: Dict, threshold: float = 80.0):
        """Identify files with low coverage."""
        low_coverage_files = []
        
        for filepath, file_data in coverage_data.get('files', {}).items():
            line_coverage = file_data.get('line_coverage', 0)
            if line_coverage < threshold:
                low_coverage_files.append({
                    'file': filepath,
                    'coverage': line_coverage,
                    'gap': threshold - line_coverage
                })
        
        # Sort by gap (worst first)
        low_coverage_files.sort(key=lambda x: x['gap'], reverse=True)
        
        return low_coverage_files
    
    def generate_report(self):
        """Generate comprehensive coverage report."""
        print("\n" + "="*60)
        print("TEST COVERAGE REPORT")
        print("="*60)
        
        # Detect project types
        project_types = []
        if (self.project_root / "pytest.ini").exists() or \
           (self.project_root / "setup.py").exists():
            project_types.append("python")
        
        if list(self.project_root.glob("*.sln")):
            project_types.append("csharp")
        
        if (self.project_root / "package.json").exists():
            project_types.append("typescript")
        
        # Run coverage for each project type
        results = {}
        for project_type in project_types:
            if project_type == "python":
                results["Python"] = self.run_python_coverage()
            elif project_type == "csharp":
                results["C#"] = self.run_csharp_coverage()
            elif project_type == "typescript":
                results["TypeScript/JavaScript"] = self.run_typescript_coverage()
        
        # Display results
        for language, data in results.items():
            if data is None:
                continue
            
            print(f"\n{'='*60}")
            print(f"{language} Coverage")
            print(f"{'='*60}")
            
            print(f"\nOverall Metrics:")
            print(f"  Line Coverage:     {data.get('overall_line_coverage', 0):.2f}%")
            print(f"  Branch Coverage:   {data.get('overall_branch_coverage', 0):.2f}%")
            
            if 'overall_function_coverage' in data:
                print(f"  Function Coverage: {data.get('overall_function_coverage', 0):.2f}%")
            if 'overall_statement_coverage' in data:
                print(f"  Statement Coverage: {data.get('overall_statement_coverage', 0):.2f}%")
            
            # Show low coverage files
            low_coverage = self.analyze_coverage_gaps(data)
            if low_coverage:
                print(f"\nFiles Below 80% Coverage:")
                for item in low_coverage[:10]:  # Show worst 10
                    print(f"  {item['coverage']:.1f}% - {item['file']}")
            
            # Coverage status
            overall = data.get('overall_line_coverage', 0)
            if overall >= 90:
                status = "✓ EXCELLENT"
            elif overall >= 80:
                status = "✓ GOOD"
            elif overall >= 70:
                status = "⚠ ACCEPTABLE"
            else:
                status = "✗ NEEDS IMPROVEMENT"
            
            print(f"\nStatus: {status}")
        
        print("\n" + "="*60)
        print("RECOMMENDATIONS")
        print("="*60)
        
        print("""
Target Coverage Levels:
  - Critical business logic: 90-100%
  - Service layer: 80-90%
  - Controllers/APIs: 70-80%
  - Utility functions: 80-90%

Focus on:
  1. Files with 0% coverage (not tested at all)
  2. Files with <50% coverage (significant gaps)
  3. Complex logic with low coverage (high risk)

Don't waste time on:
  - Framework/library code
  - Simple getters/setters
  - Generated code
  - Configuration files
        """)


def main():
    """Main entry point."""
    project_root = Path.cwd()
    
    print(f"Analyzing test coverage in: {project_root}\n")
    
    analyzer = CoverageAnalyzer(project_root)
    analyzer.generate_report()


if __name__ == "__main__":
    main()
