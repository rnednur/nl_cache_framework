from setuptools import setup, find_packages
import os

# Initialize version to a default value
version = "0.0.0"

# Read version from __init__.py in the current directory (backend/)
with open("__init__.py", "r") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip("\"'")
            break

# Read requirements.txt
with open("requirements.txt", "r") as f:
    requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

# Read README.md from the parent directory (project root)
with open("../README.md", "r") as f:
    long_description = f.read()

setup(
    name="thinkforge-mcp",
    version=version,
    description="Model Context Protocol server for ThinkForge",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ThinkForge Team",
    author_email="contact@example.com",
    url="https://github.com/example/thinkforge-mcp",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "thinkforge-mcp=mcp_server.run:run_server",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
