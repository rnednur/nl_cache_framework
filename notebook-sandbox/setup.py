#!/usr/bin/env python3
"""
Setup script for notebook-sandbox package.
A reusable secure notebook execution environment.
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Secure notebook execution environment"

# Read requirements
def read_requirements(filename):
    req_path = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="notebook-sandbox",
    version="1.0.0",
    description="Secure notebook execution environment with wrapper service integration",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="ThinkForge Team",
    author_email="team@thinkforge.dev",
    url="https://github.com/thinkforge/notebook-sandbox",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'notebook_sandbox': [
            'config/*.yml',
            'config/*.yaml',
            'docker/*',
            'examples/*'
        ]
    },
    python_requires=">=3.8",
    install_requires=read_requirements('requirements.txt'),
    extras_require={
        'dev': read_requirements('requirements-dev.txt'),
        'mcp': ['mcp-client>=1.0.0'],
        'all': read_requirements('requirements-dev.txt') + ['mcp-client>=1.0.0']
    },
    entry_points={
        'console_scripts': [
            'notebook-sandbox=notebook_sandbox.cli:main',
            'sandbox-server=notebook_sandbox.core.api_server:main',
            'sandbox-executor=notebook_sandbox.core.executor:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Code Generators",
        "Topic :: System :: Shells",
        "Topic :: Scientific/Engineering",
    ],
    keywords="notebook jupyter execution sandbox docker security workflow automation",
    project_urls={
        "Bug Reports": "https://github.com/thinkforge/notebook-sandbox/issues",
        "Source": "https://github.com/thinkforge/notebook-sandbox",
        "Documentation": "https://notebook-sandbox.readthedocs.io/",
    },
)