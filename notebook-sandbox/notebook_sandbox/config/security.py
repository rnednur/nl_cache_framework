"""
Security configuration for notebook validation and execution.
"""

import os
from typing import Dict, Any, Set, List
from dataclasses import dataclass, field

@dataclass
class SecurityConfig:
    """Security configuration for notebook sandbox."""
    
    # Import restrictions
    dangerous_imports: Set[str] = field(default_factory=lambda: {
        'os', 'sys', 'subprocess', 'shutil', 'glob',
        'socket', 'urllib', 'requests', 'http',
        'ftplib', 'smtplib', 'poplib', 'imaplib',
        'telnetlib', 'xmlrpc', 'pickle', 'shelve',
        'marshal', 'ctypes', '__builtin__', 'builtins'
    })
    
    allowed_imports: Set[str] = field(default_factory=lambda: {
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
    })
    
    # Function restrictions
    dangerous_functions: Set[str] = field(default_factory=lambda: {
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input', 'raw_input',
        'execfile', 'reload', 'vars', 'locals', 'globals',
        'dir', 'hasattr', 'getattr', 'setattr', 'delattr'
    })
    
    # Pattern restrictions
    dangerous_patterns: List[str] = field(default_factory=lambda: [
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
    ])
    
    # Size limits
    max_cell_count: int = 100
    max_cell_lines: int = 1000
    max_output_size: int = 10 * 1024 * 1024  # 10MB
    
    # Validation strictness
    strict_mode: bool = True
    allow_network_access: bool = False
    allow_file_system_access: bool = False
    
    @classmethod
    def from_env(cls) -> 'SecurityConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Update from environment
        config.max_cell_count = int(os.getenv('MAX_CELL_COUNT', '100'))
        config.max_cell_lines = int(os.getenv('MAX_CELL_LINES', '1000'))
        config.max_output_size = int(os.getenv('MAX_OUTPUT_SIZE', str(10 * 1024 * 1024)))
        config.strict_mode = os.getenv('STRICT_MODE', 'true').lower() == 'true'
        config.allow_network_access = os.getenv('ALLOW_NETWORK_ACCESS', 'false').lower() == 'true'
        config.allow_file_system_access = os.getenv('ALLOW_FILE_SYSTEM_ACCESS', 'false').lower() == 'true'
        
        # Update import restrictions based on permissions
        if config.allow_network_access:
            config.allowed_imports.update(['requests', 'urllib', 'http', 'socket'])
            config.dangerous_imports -= {'requests', 'urllib', 'http', 'socket'}
        
        if config.allow_file_system_access:
            config.allowed_imports.update(['os', 'shutil', 'glob'])
            config.dangerous_imports -= {'os', 'shutil', 'glob'}
            config.dangerous_functions -= {'open', 'file'}
        
        return config
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'SecurityConfig':
        """Create configuration from dictionary."""
        config = cls()
        
        # Update basic settings
        for key in ['max_cell_count', 'max_cell_lines', 'max_output_size', 
                   'strict_mode', 'allow_network_access', 'allow_file_system_access']:
            if key in config_dict:
                setattr(config, key, config_dict[key])
        
        # Update sets and lists
        if 'dangerous_imports' in config_dict:
            config.dangerous_imports = set(config_dict['dangerous_imports'])
        if 'allowed_imports' in config_dict:
            config.allowed_imports = set(config_dict['allowed_imports'])
        if 'dangerous_functions' in config_dict:
            config.dangerous_functions = set(config_dict['dangerous_functions'])
        if 'dangerous_patterns' in config_dict:
            config.dangerous_patterns = list(config_dict['dangerous_patterns'])
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'dangerous_imports': list(self.dangerous_imports),
            'allowed_imports': list(self.allowed_imports),
            'dangerous_functions': list(self.dangerous_functions),
            'dangerous_patterns': self.dangerous_patterns,
            'max_cell_count': self.max_cell_count,
            'max_cell_lines': self.max_cell_lines,
            'max_output_size': self.max_output_size,
            'strict_mode': self.strict_mode,
            'allow_network_access': self.allow_network_access,
            'allow_file_system_access': self.allow_file_system_access
        }
    
    def get_security_policy(self):
        """Get a security policy object for the validator."""
        from ..core.validator import SecurityPolicy
        
        policy = SecurityPolicy()
        policy.dangerous_imports = self.dangerous_imports
        policy.allowed_imports = self.allowed_imports
        policy.dangerous_functions = self.dangerous_functions
        policy.dangerous_patterns = self.dangerous_patterns
        policy.max_cell_count = self.max_cell_count
        policy.max_cell_lines = self.max_cell_lines
        policy.max_output_size = self.max_output_size
        
        return policy
    
    def add_allowed_import(self, module_name: str):
        """Add an allowed import."""
        self.allowed_imports.add(module_name)
        self.dangerous_imports.discard(module_name)
    
    def add_dangerous_import(self, module_name: str):
        """Add a dangerous import."""
        self.dangerous_imports.add(module_name)
        self.allowed_imports.discard(module_name)
    
    def is_import_allowed(self, module_name: str) -> bool:
        """Check if an import is allowed."""
        if module_name in self.dangerous_imports:
            return False
        
        if module_name in self.allowed_imports:
            return True
        
        # Check if it's a submodule of an allowed module
        for allowed in self.allowed_imports:
            if module_name.startswith(f"{allowed}."):
                return True
        
        # In strict mode, default to not allowed
        return not self.strict_mode