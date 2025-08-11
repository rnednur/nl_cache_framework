#!/usr/bin/env python3
"""
Run all tests for the NL Cache Framework

This script runs the unit tests and API integration tests for the NL Cache Framework.
It provides a convenient way to verify that all functionality is working as expected.

Usage:
    python run_tests.py
"""

import sys
import subprocess
import logging

from argparse import ArgumentParser

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_command(command, description):
    """Run a shell command and log the result"""
    logger.info(f"Running {description}...")
    try:
        subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info(f"{description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"{description} failed with exit code {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False


def run_pytest(pytest_args):
    """Runs pytest with specified arguments."""
    command = [sys.executable, "-m", "pytest"] + pytest_args
    print(f"Running command: {' '.join(command)}")
    subprocess.run(command, check=True)


def run_flake8(exclude_dirs=None):
    # This function needs an implementation or a pass statement
    pass


def main():
    """Run all tests"""
    # Track test results
    results = {}

    # Run unit tests
    results["unit_tests"] = run_command(
        "python -m pytest tests/test_controller.py -v", "Unit Tests"
    )

    # Run API integration test (if desired)
    run_api_test = (
        input("Do you want to run the API integration test? (y/n) [y]: ").lower() or "y"
    )
    if run_api_test == "y":
        results["api_integration"] = run_command(
            "python -m tests.api_integration_test", "API Integration Test"
        )

    # Print summary
    logger.info("\n--- Test Summary ---")
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        all_passed = all_passed and passed

    # Return appropriate exit code
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
