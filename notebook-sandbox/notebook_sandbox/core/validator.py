"""
Notebook validation module for security and syntax checking.
"""

import json
import ast
import re
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import structlog

logger = structlog.get_logger()

class ValidationIssue:
    """Represents a validation issue found in a notebook."""
    
    def __init__(self, 
                 issue_type: str,
                 severity: str,
                 message: str,
                 cell_index: Optional[int] = None,
                 line_number: Optional[int] = None):
        self.issue_type = issue_type
        self.severity = severity  # 'error', 'warning', 'info'
        self.message = message
        self.cell_index = cell_index
        self.line_number = line_number
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.issue_type,
            "severity": self.severity,
            "message": self.message,
            "cell_index": self.cell_index,
            "line_number": self.line_number
        }

class SecurityPolicy:
    """Security policy configuration for notebook validation."""
    
    def __init__(self):
        # Dangerous imports and functions
        self.dangerous_imports = {
            'os', 'sys', 'subprocess', 'shutil', 'glob',
            'socket', 'urllib', 'requests', 'http',
            'ftplib', 'smtplib', 'poplib', 'imaplib',
            'telnetlib', 'xmlrpc', 'pickle', 'shelve',
            'marshal', 'ctypes', '__builtin__', 'builtins'
        }
        
        self.dangerous_functions = {
            'eval', 'exec', 'compile', '__import__',
            'open', 'file', 'input', 'raw_input',
            'execfile', 'reload', 'vars', 'locals', 'globals',
            'dir', 'hasattr', 'getattr', 'setattr', 'delattr'
        }
        
        # Dangerous patterns (regex)
        self.dangerous_patterns = [
            r'subprocess\.',
            r'os\.',
            r'sys\.',
            r'__.*__',  # Dunder methods
            r'import\s+os',
            r'import\s+sys',
            r'import\s+subprocess',
            r'from\s+os\s+import',
            r'from\s+sys\s+import',
            r'exec\s*\(',
            r'eval\s*\(',
            r'compile\s*\(',
            r'__import__\s*\(',
        ]
        
        # Allowed imports (whitelist)
        self.allowed_imports = {
            'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly',
            'scipy', 'sklearn', 'statsmodels', 'sympy',
            'json', 'csv', 'datetime', 'time', 'math',
            'random', 'string', 'itertools', 'collections',
            'functools', 'operator', 're', 'uuid',
            'base64', 'hashlib', 'hmac', 'secrets',
            'typing', 'dataclasses', 'enum', 'abc',
            'pathlib', 'tempfile', 'io', 'contextlib',
            'warnings', 'logging', 'traceback',
            'asyncio', 'concurrent', 'threading', 'multiprocessing',
            'aiohttp', 'httpx', 'pydantic', 'fastapi',
            'sqlalchemy', 'psycopg2', 'sqlite3',
            'jupyter', 'ipython', 'notebook',
        }
        
        # Maximum values
        self.max_cell_count = 100
        self.max_cell_lines = 1000
        self.max_output_size = 10 * 1024 * 1024  # 10MB
        
    def is_import_allowed(self, module_name: str) -> bool:
        """Check if an import is allowed by the security policy."""
        # Check if it's in dangerous imports
        if module_name in self.dangerous_imports:
            return False
        
        # Check if it's explicitly allowed
        if module_name in self.allowed_imports:
            return True
        
        # Check if it's a submodule of an allowed module
        for allowed in self.allowed_imports:
            if module_name.startswith(f"{allowed}."):
                return True
        
        # Default: not allowed
        return False

class NotebookValidator:
    """Validates Jupyter notebooks for security and syntax issues."""
    
    def __init__(self, security_policy: Optional[SecurityPolicy] = None):
        """Initialize validator with security policy."""
        self.security_policy = security_policy or SecurityPolicy()
        self.issues: List[ValidationIssue] = []
    
    def validate_notebook(self, notebook_path: Path) -> Dict[str, Any]:
        """Validate a notebook file and return validation results."""
        self.issues = []
        
        try:
            with open(notebook_path, 'r', encoding='utf-8') as f:
                notebook_data = json.load(f)
        except json.JSONDecodeError as e:
            self.issues.append(ValidationIssue(
                "json_error", "error", f"Invalid JSON format: {str(e)}"
            ))
            return self._build_result(False)
        except Exception as e:
            self.issues.append(ValidationIssue(
                "file_error", "error", f"Failed to read notebook: {str(e)}"
            ))
            return self._build_result(False)
        
        # Validate notebook structure
        self._validate_structure(notebook_data)
        
        # Validate cells
        if "cells" in notebook_data:
            self._validate_cells(notebook_data["cells"])
        
        # Check for security issues
        if "cells" in notebook_data:
            self._validate_security(notebook_data["cells"])
        
        # Determine if validation passed
        has_errors = any(issue.severity == "error" for issue in self.issues)
        
        result = self._build_result(not has_errors)
        
        logger.info("Notebook validation completed",
                   notebook_path=str(notebook_path),
                   valid=result["valid"],
                   issues_count=len(self.issues))
        
        return result
    
    def validate_notebook_content(self, notebook_content: str) -> Dict[str, Any]:
        """Validate notebook content string."""
        self.issues = []
        
        try:
            notebook_data = json.loads(notebook_content)
        except json.JSONDecodeError as e:
            self.issues.append(ValidationIssue(
                "json_error", "error", f"Invalid JSON format: {str(e)}"
            ))
            return self._build_result(False)
        
        # Validate notebook structure
        self._validate_structure(notebook_data)
        
        # Validate cells
        if "cells" in notebook_data:
            self._validate_cells(notebook_data["cells"])
        
        # Check for security issues
        if "cells" in notebook_data:
            self._validate_security(notebook_data["cells"])
        
        # Determine if validation passed
        has_errors = any(issue.severity == "error" for issue in self.issues)
        
        return self._build_result(not has_errors)
    
    def _validate_structure(self, notebook_data: Dict[str, Any]):
        """Validate basic notebook structure."""
        required_fields = ["cells", "metadata", "nbformat", "nbformat_minor"]
        
        for field in required_fields:
            if field not in notebook_data:
                self.issues.append(ValidationIssue(
                    "structure_error", "error", f"Missing required field: {field}"
                ))
        
        # Check nbformat version
        if "nbformat" in notebook_data:
            nbformat = notebook_data["nbformat"]
            if not isinstance(nbformat, int) or nbformat < 4:
                self.issues.append(ValidationIssue(
                    "version_error", "warning", 
                    f"Unsupported notebook format version: {nbformat}"
                ))
    
    def _validate_cells(self, cells: List[Dict[str, Any]]):
        """Validate notebook cells."""
        if len(cells) > self.security_policy.max_cell_count:
            self.issues.append(ValidationIssue(
                "cell_count_error", "error",
                f"Too many cells: {len(cells)} > {self.security_policy.max_cell_count}"
            ))
        
        for i, cell in enumerate(cells):
            self._validate_single_cell(cell, i)
    
    def _validate_single_cell(self, cell: Dict[str, Any], cell_index: int):
        """Validate a single notebook cell."""
        # Check required fields
        if "cell_type" not in cell:
            self.issues.append(ValidationIssue(
                "cell_error", "error", f"Cell {cell_index} missing 'cell_type'",
                cell_index=cell_index
            ))
            return
        
        if "source" not in cell:
            self.issues.append(ValidationIssue(
                "cell_error", "error", f"Cell {cell_index} missing 'source'",
                cell_index=cell_index
            ))
            return
        
        cell_type = cell["cell_type"]
        source = cell["source"]
        
        # Validate source format
        if isinstance(source, list):
            source_text = "".join(source)
        elif isinstance(source, str):
            source_text = source
        else:
            self.issues.append(ValidationIssue(
                "cell_error", "error", 
                f"Cell {cell_index} has invalid source format",
                cell_index=cell_index
            ))
            return
        
        # Check cell size
        if len(source_text.splitlines()) > self.security_policy.max_cell_lines:
            self.issues.append(ValidationIssue(
                "cell_size_error", "warning",
                f"Cell {cell_index} too large: {len(source_text.splitlines())} lines",
                cell_index=cell_index
            ))
        
        # Validate code cells
        if cell_type == "code":
            self._validate_code_cell(source_text, cell_index)
    
    def _validate_code_cell(self, source_text: str, cell_index: int):
        """Validate code cell syntax and content."""
        if not source_text.strip():
            return  # Empty cells are fine
        
        # Check Python syntax
        try:
            ast.parse(source_text)
        except SyntaxError as e:
            self.issues.append(ValidationIssue(
                "syntax_error", "error",
                f"Syntax error in cell {cell_index}: {str(e)}",
                cell_index=cell_index,
                line_number=e.lineno
            ))
    
    def _validate_security(self, cells: List[Dict[str, Any]]):
        """Validate cells for security issues."""
        for i, cell in enumerate(cells):
            if cell.get("cell_type") == "code":
                source = cell.get("source", "")
                if isinstance(source, list):
                    source_text = "".join(source)
                else:
                    source_text = str(source)
                
                self._check_dangerous_patterns(source_text, i)
                self._check_imports(source_text, i)
                self._check_dangerous_functions(source_text, i)
    
    def _check_dangerous_patterns(self, source_text: str, cell_index: int):
        """Check for dangerous regex patterns."""
        for pattern in self.security_policy.dangerous_patterns:
            matches = re.finditer(pattern, source_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = source_text[:match.start()].count('\n') + 1
                self.issues.append(ValidationIssue(
                    "security_pattern", "error",
                    f"Dangerous pattern '{pattern}' found in cell {cell_index}",
                    cell_index=cell_index,
                    line_number=line_num
                ))
    
    def _check_imports(self, source_text: str, cell_index: int):
        """Check for dangerous imports."""
        try:
            tree = ast.parse(source_text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self.security_policy.is_import_allowed(alias.name):
                            self.issues.append(ValidationIssue(
                                "dangerous_import", "error",
                                f"Dangerous import '{alias.name}' in cell {cell_index}",
                                cell_index=cell_index,
                                line_number=node.lineno
                            ))
                
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if not self.security_policy.is_import_allowed(module):
                        self.issues.append(ValidationIssue(
                            "dangerous_import", "error",
                            f"Dangerous import 'from {module}' in cell {cell_index}",
                            cell_index=cell_index,
                            line_number=node.lineno
                        ))
        except SyntaxError:
            # Syntax errors already caught in earlier validation
            pass
    
    def _check_dangerous_functions(self, source_text: str, cell_index: int):
        """Check for dangerous function calls."""
        try:
            tree = ast.parse(source_text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in self.security_policy.dangerous_functions:
                        self.issues.append(ValidationIssue(
                            "dangerous_function", "error",
                            f"Dangerous function '{func_name}' called in cell {cell_index}",
                            cell_index=cell_index,
                            line_number=node.lineno
                        ))
        except SyntaxError:
            # Syntax errors already caught in earlier validation
            pass
    
    def _build_result(self, valid: bool) -> Dict[str, Any]:
        """Build validation result dictionary."""
        issues_by_severity = {"error": 0, "warning": 0, "info": 0}
        for issue in self.issues:
            issues_by_severity[issue.severity] += 1
        
        return {
            "valid": valid,
            "issues": [issue.to_dict() for issue in self.issues],
            "issue_count": len(self.issues),
            "issues_by_severity": issues_by_severity,
            "error_count": issues_by_severity["error"],
            "warning_count": issues_by_severity["warning"],
            "info_count": issues_by_severity["info"]
        }