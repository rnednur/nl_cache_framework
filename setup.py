from setuptools import setup, find_packages
import os

# Read requirements.txt
lib_folder = os.path.dirname(os.path.realpath(__file__))
requirement_path = os.path.join(lib_folder, "requirements.txt")
install_requires = []
if os.path.isfile(requirement_path):
    with open(requirement_path) as f:
        install_requires = [
            line for line in f.read().splitlines() if line and not line.startswith("#")
        ]

# Read README.md for long description
readme_path = os.path.join(lib_folder, "README.md")
long_description = ""
if os.path.isfile(readme_path):
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()

# Get version from __init__.py
__version__ = ""
init_path = os.path.join(lib_folder, "nl_cache_framework", "__init__.py")
if os.path.isfile(init_path):
    with open(init_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                version_ns = {}
                exec(line, version_ns)
                __version__ = version_ns["__version__"]
                break
if not __version__:
    print("Warning: Could not find __version__ in __init__.py. Defaulting to 0.0.1.")
    __version__ = "0.0.1"

setup(
    name="nl_cache_framework",
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    description="A reusable framework for caching natural language to template translations.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="NL Cache Framework Team",
    author_email="contact@example.com",
    url="https://github.com/example/nl_cache_framework",
    license="MIT",
    install_requires=install_requires,
    python_requires=">=3.8",
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
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Database",
        "Topic :: Text Processing :: Linguistic",
    ],
    keywords="nlp cache semantic-search entity-substitution sql api workflow fastapi sqlalchemy sentence-transformers",
)
