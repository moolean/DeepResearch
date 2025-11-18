#!/usr/bin/env python3
"""
Main test runner for all API tests
Runs all API availability tests and reports overall status
"""
import os
import sys
import subprocess
from pathlib import Path

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(message):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")

def run_test(test_file):
    """Run a single test file and return success status"""
    test_name = test_file.stem
    print(f"\n{Colors.BOLD}Running {test_name}...{Colors.END}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=False,
            timeout=60
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"{Colors.RED}❌ Test timed out{Colors.END}")
        return False
    except Exception as e:
        print(f"{Colors.RED}❌ Test execution failed: {str(e)}{Colors.END}")
        return False

def main():
    """Main test execution function"""
    print_header("DeepResearch API Availability Tests")
    
    # Check if .env file exists
    env_file = Path(__file__).parent.parent / '.env'
    if not env_file.exists():
        print(f"\n{Colors.RED}{Colors.BOLD}ERROR: .env file not found{Colors.END}")
        print(f"Please copy .env.example to .env and configure your settings:")
        print(f"  cp .env.example .env")
        sys.exit(1)
    
    # Load environment variables from .env
    print(f"\n{Colors.GREEN}✓ .env file found{Colors.END}")
    from dotenv import load_dotenv
    load_dotenv(env_file)
    
    # Get enabled tools from environment
    enabled_tools_str = os.environ.get('ENABLED_TOOLS', 'search,visit,google_scholar,PythonInterpreter,parse_file')
    enabled_tools = [tool.strip() for tool in enabled_tools_str.split(',')]
    
    print(f"\n{Colors.BOLD}Enabled tools:{Colors.END} {', '.join(enabled_tools)}")
    
    # Map tools to test files
    tool_test_mapping = {
        'search': 'test_api_search.py',
        'visit': 'test_api_visit.py',
        'google_scholar': 'test_api_scholar.py',
        'PythonInterpreter': 'test_api_python.py',
        'parse_file': 'test_api_file.py',
    }
    
    # Determine which tests to run
    tests_dir = Path(__file__).parent
    tests_to_run = []
    
    for tool in enabled_tools:
        if tool in tool_test_mapping:
            test_file = tests_dir / tool_test_mapping[tool]
            if test_file.exists():
                tests_to_run.append(test_file)
            else:
                print(f"{Colors.YELLOW}⚠ Warning: Test file not found for tool '{tool}': {test_file}{Colors.END}")
    
    if not tests_to_run:
        print(f"\n{Colors.YELLOW}No tests to run based on ENABLED_TOOLS configuration{Colors.END}")
        sys.exit(0)
    
    print(f"\n{Colors.BOLD}Running {len(tests_to_run)} test(s)...{Colors.END}")
    
    # Run all tests
    results = {}
    for test_file in tests_to_run:
        test_name = test_file.stem
        success = run_test(test_file)
        results[test_name] = success
    
    # Print summary
    print_header("Test Results Summary")
    
    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed
    
    print(f"\n{Colors.BOLD}Tests Run:{Colors.END} {len(results)}")
    print(f"{Colors.GREEN}{Colors.BOLD}Passed:{Colors.END} {passed}")
    print(f"{Colors.RED}{Colors.BOLD}Failed:{Colors.END} {failed}")
    
    print(f"\n{Colors.BOLD}Detailed Results:{Colors.END}")
    for test_name, success in results.items():
        status = f"{Colors.GREEN}✅ PASSED{Colors.END}" if success else f"{Colors.RED}❌ FAILED{Colors.END}"
        print(f"  {test_name}: {status}")
    
    # Final verdict
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    if all(results.values()):
        print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED - Environment is ready!{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
        sys.exit(0)
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ SOME TESTS FAILED - Please fix the issues before running inference{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
