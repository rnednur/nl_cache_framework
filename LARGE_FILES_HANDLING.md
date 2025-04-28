# Large Files Handling

This document describes how large binary files are handled in this repository.

## Identified Large Files

The following large files were identified in the repository:

- `frontend/node_modules/@next/swc-darwin-arm64/next-swc.darwin-arm64.node`
- `venv/lib/python3.11/site-packages/torch/lib/libtorch_cpu.dylib`
- `venv/lib/python3.11/site-packages/torch/lib/libtorch_python.dylib`
- `venv/lib/python3.11/site-packages/cryptography/hazmat/bindings/_rust.abi3.so`

These files are automatically generated when setting up the development environment and don't need to be tracked in version control.

## Actions Taken

### 1. Updated .gitignore

The `.gitignore` file was updated to exclude these large binary files:

```
# Large binary files
frontend/node_modules/@next/swc-darwin-arm64/next-swc.darwin-arm64.node
venv/lib/python3.11/site-packages/torch/lib/libtorch_cpu.dylib
venv/lib/python3.11/site-packages/torch/lib/libtorch_python.dylib
venv/lib/python3.11/site-packages/cryptography/hazmat/bindings/_rust.abi3.so
```

### 2. Cleaned Git History

Used `git-filter-repo` to remove large files from the Git history:

```bash
# First removal
git filter-repo --path-glob 'frontend/node_modules/@next/swc-darwin-arm64/next-swc.darwin-arm64.node' --path-glob 'venv/lib/python3.11/site-packages/torch/lib/libtorch_cpu.dylib' --invert-paths --force

# Second removal
git filter-repo --path-glob 'venv/lib/python3.11/site-packages/torch/lib/libtorch_python.dylib' --path-glob 'venv/lib/python3.11/site-packages/cryptography/hazmat/bindings/_rust.abi3.so' --invert-paths --force
```

### 3. Added Pre-commit Hook

Created a pre-commit hook (`.git/hooks/pre-commit`) to prevent large files from being committed:

- Checks all staged files
- Rejects commits containing files larger than 10MB
- Provides feedback to the user about which files are too large

### 4. Updated Documentation

- Added a section to the README.md about handling large files
- Created this document to explain the cleanup process

## Repository Size

After cleanup:
- Repository size: ~1.4G
- Git directory size: ~68M

## For New Contributors

When setting up a new development environment:

1. Clone the repository
2. Create and activate a virtual environment: `python -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Set up the frontend: `cd frontend && npm install`

This will generate all necessary binary files that are excluded from version control.

## Best Practices Going Forward

1. Never commit large binary files directly to the repository
2. Follow the pre-commit hook guidelines
3. If large binary files need to be shared, consider using:
   - Artifact storage systems
   - Cloud storage with download scripts
   - Package managers for dependencies 