"""
Execution Configuration Management for ThinkForge Framework

This module handles runtime parameters, credentials, and execution settings
for different types of tools and workflows.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import yaml

logger = logging.getLogger(__name__)


class ConfigScope(str, Enum):
    """Configuration scope levels."""
    GLOBAL = "global"
    WORKFLOW = "workflow"
    STEP = "step"
    TOOL = "tool"


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    host: str
    port: int
    database: str
    username: str
    password: str
    schema: Optional[str] = None
    ssl: bool = False
    connection_timeout: int = 30
    query_timeout: int = 300


@dataclass
class APIConfig:
    """API connection configuration."""
    base_url: str
    authentication: Dict[str, Any]
    headers: Dict[str, str]
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1


@dataclass
class ToolConfig:
    """Tool-specific configuration."""
    tool_type: str
    executable_path: Optional[str] = None
    environment: Dict[str, str] = None
    working_directory: Optional[str] = None
    timeout: int = 300
    resource_limits: Dict[str, Any] = None


@dataclass
class LLMConfig:
    """LLM service configuration."""
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "google/gemini-pro"
    temperature: float = 0.3
    max_tokens: int = 500
    timeout: int = 60
    retry_attempts: int = 2
    retry_delay: int = 1
    system_prompt: Optional[str] = None


@dataclass
class DuckDBConfig:
    """DuckDB configuration for workflow data persistence."""
    database_path: Optional[str] = None
    temp_dir: Optional[str] = None
    auto_cleanup: bool = True
    memory_limit: str = "1GB"
    threads: int = 4
    enable_extensions: List[str] = None
    pragmas: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.enable_extensions is None:
            self.enable_extensions = []
        if self.pragmas is None:
            self.pragmas = {}


@dataclass
class WorkflowConfig:
    """Workflow execution configuration."""
    parallel_limit: int = 5
    step_timeout: int = 300
    failure_strategy: str = "stop"  # "stop", "continue", "retry"
    retry_attempts: int = 3
    retry_delay: int = 5
    progress_reporting: bool = True
    enable_duckdb: bool = True
    duckdb_config: Optional[DuckDBConfig] = None
    
    def __post_init__(self):
        if self.enable_duckdb and self.duckdb_config is None:
            self.duckdb_config = DuckDBConfig()


class ExecutionConfigManager:
    """
    Manages execution configurations for ThinkForge workflows and tools.
    
    Supports hierarchical configuration with global defaults, workflow-specific
    settings, and step-level overrides.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to configuration file (JSON or YAML)
        """
        self.configs = {
            ConfigScope.GLOBAL: {},
            ConfigScope.WORKFLOW: {},
            ConfigScope.STEP: {},
            ConfigScope.TOOL: {}
        }
        
        # Load configuration from file if provided
        if config_path and os.path.exists(config_path):
            self.load_config_file(config_path)
        
        # Load from environment variables
        self._load_from_environment()
    
    def load_config_file(self, config_path: str) -> None:
        """Load configuration from a JSON or YAML file."""
        try:
            with open(config_path, 'r') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)
            
            # Organize configuration by scope
            for scope in ConfigScope:
                if scope.value in config_data:
                    self.configs[scope].update(config_data[scope.value])
            
            logger.info(f"Loaded configuration from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            # Database configuration
            'THINKFORGE_DB_HOST': ('global', 'database', 'host'),
            'THINKFORGE_DB_PORT': ('global', 'database', 'port'),
            'THINKFORGE_DB_NAME': ('global', 'database', 'database'),
            'THINKFORGE_DB_USER': ('global', 'database', 'username'),
            'THINKFORGE_DB_PASSWORD': ('global', 'database', 'password'),
            'THINKFORGE_DB_SCHEMA': ('global', 'database', 'schema'),
            
            # API configuration
            'THINKFORGE_API_BASE_URL': ('global', 'api', 'base_url'),
            'THINKFORGE_API_TIMEOUT': ('global', 'api', 'timeout'),
            'THINKFORGE_API_RETRY_ATTEMPTS': ('global', 'api', 'retry_attempts'),
            
            # Workflow configuration
            'THINKFORGE_PARALLEL_LIMIT': ('global', 'workflow', 'parallel_limit'),
            'THINKFORGE_STEP_TIMEOUT': ('global', 'workflow', 'step_timeout'),
            'THINKFORGE_FAILURE_STRATEGY': ('global', 'workflow', 'failure_strategy'),
        }
        
        for env_var, (scope, section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_config(scope, section, key, self._parse_env_value(value))
    
    def _parse_env_value(self, value: str) -> Union[str, int, bool, float]:
        """Parse environment variable value to appropriate type."""
        # Try to parse as int
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try to parse as float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try to parse as boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Return as string
        return value
    
    def _set_nested_config(self, scope: str, section: str, key: str, value: Any) -> None:
        """Set a nested configuration value."""
        scope_enum = ConfigScope(scope)
        if section not in self.configs[scope_enum]:
            self.configs[scope_enum][section] = {}
        self.configs[scope_enum][section][key] = value
    
    def get_database_config(
        self, 
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None
    ) -> Optional[DatabaseConfig]:
        """
        Get database configuration with scope resolution.
        
        Args:
            workflow_id: Optional workflow ID for workflow-specific config
            step_id: Optional step ID for step-specific config
            
        Returns:
            DatabaseConfig object or None if not configured
        """
        config = self._resolve_config('database', workflow_id, step_id)
        if not config:
            return None
        
        try:
            return DatabaseConfig(**config)
        except TypeError as e:
            logger.error(f"Invalid database configuration: {e}")
            return None
    
    def get_api_config(
        self,
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None
    ) -> Optional[APIConfig]:
        """
        Get API configuration with scope resolution.
        
        Args:
            workflow_id: Optional workflow ID for workflow-specific config
            step_id: Optional step ID for step-specific config
            
        Returns:
            APIConfig object or None if not configured
        """
        config = self._resolve_config('api', workflow_id, step_id)
        if not config:
            return None
        
        try:
            # Ensure required fields have defaults
            config.setdefault('authentication', {})
            config.setdefault('headers', {})
            return APIConfig(**config)
        except TypeError as e:
            logger.error(f"Invalid API configuration: {e}")
            return None
    
    def get_tool_config(
        self,
        tool_type: str,
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None
    ) -> Optional[ToolConfig]:
        """
        Get tool-specific configuration.
        
        Args:
            tool_type: Type of tool (sql, api, function, etc.)
            workflow_id: Optional workflow ID for workflow-specific config
            step_id: Optional step ID for step-specific config
            
        Returns:
            ToolConfig object or None if not configured
        """
        config = self._resolve_config(f'tools.{tool_type}', workflow_id, step_id)
        if not config:
            # Try generic tool config
            config = self._resolve_config('tool', workflow_id, step_id)
        
        if not config:
            return None
        
        try:
            config['tool_type'] = tool_type
            config.setdefault('environment', {})
            config.setdefault('resource_limits', {})
            return ToolConfig(**config)
        except TypeError as e:
            logger.error(f"Invalid tool configuration: {e}")
            return None
    
    def get_llm_config(
        self,
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None
    ) -> Optional[LLMConfig]:
        """
        Get LLM configuration with scope resolution.
        
        Args:
            workflow_id: Optional workflow ID for workflow-specific config
            step_id: Optional step ID for step-specific config
            
        Returns:
            LLMConfig object or None if not configured
        """
        config = self._resolve_config('llm', workflow_id, step_id)
        if not config:
            # Try to get from environment variables as fallback
            api_key = os.getenv('OPENROUTER_API_KEY')
            if api_key:
                config = {
                    'api_key': api_key,
                    'base_url': os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
                    'model': os.getenv('OPENROUTER_MODEL', 'google/gemini-pro')
                }
            else:
                return None
        
        try:
            return LLMConfig(**config)
        except TypeError as e:
            logger.error(f"Invalid LLM configuration: {e}")
            return None
    
    def get_duckdb_config(
        self,
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None
    ) -> Optional[DuckDBConfig]:
        """
        Get DuckDB configuration with scope resolution.
        
        Args:
            workflow_id: Optional workflow ID for workflow-specific config
            step_id: Optional step ID for step-specific config
            
        Returns:
            DuckDBConfig object or None if not configured
        """
        config = self._resolve_config('duckdb', workflow_id, step_id)
        if not config:
            # Try to get from environment variables as fallback
            config = {
                'temp_dir': os.getenv('DUCKDB_TEMP_DIR'),
                'memory_limit': os.getenv('DUCKDB_MEMORY_LIMIT', '1GB'),
                'threads': int(os.getenv('DUCKDB_THREADS', '4')),
                'auto_cleanup': os.getenv('DUCKDB_AUTO_CLEANUP', 'true').lower() == 'true'
            }
            # Remove None values
            config = {k: v for k, v in config.items() if v is not None}
            
            if not config:
                # Return default configuration
                return DuckDBConfig()
        
        try:
            return DuckDBConfig(**config)
        except TypeError as e:
            logger.error(f"Invalid DuckDB configuration: {e}")
            return DuckDBConfig()  # Return default on error
    
    def get_workflow_config(
        self,
        workflow_id: Optional[str] = None
    ) -> WorkflowConfig:
        """
        Get workflow configuration with defaults.
        
        Args:
            workflow_id: Optional workflow ID for workflow-specific config
            
        Returns:
            WorkflowConfig object with defaults
        """
        config = self._resolve_config('workflow', workflow_id) or {}
        
        # Apply defaults
        defaults = {
            'parallel_limit': 5,
            'step_timeout': 300,
            'failure_strategy': 'stop',
            'retry_attempts': 3,
            'retry_delay': 5,
            'progress_reporting': True
        }
        
        for key, default_value in defaults.items():
            config.setdefault(key, default_value)
        
        return WorkflowConfig(**config)
    
    def _resolve_config(
        self,
        config_key: str,
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve configuration with hierarchical precedence.
        
        Precedence order (highest to lowest):
        1. Step-specific configuration
        2. Workflow-specific configuration
        3. Global configuration
        """
        result = {}
        
        # Start with global config
        global_config = self._get_nested_config(self.configs[ConfigScope.GLOBAL], config_key)
        if global_config:
            result.update(global_config)
        
        # Override with workflow-specific config
        if workflow_id:
            workflow_config = self._get_nested_config(
                self.configs[ConfigScope.WORKFLOW].get(workflow_id, {}), 
                config_key
            )
            if workflow_config:
                result.update(workflow_config)
        
        # Override with step-specific config
        if step_id:
            step_config = self._get_nested_config(
                self.configs[ConfigScope.STEP].get(step_id, {}), 
                config_key
            )
            if step_config:
                result.update(step_config)
        
        return result if result else None
    
    def _get_nested_config(self, config: Dict[str, Any], key_path: str) -> Optional[Dict[str, Any]]:
        """Get nested configuration value using dot notation."""
        keys = key_path.split('.')
        current = config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current if isinstance(current, dict) else None
    
    def set_config(
        self,
        config_key: str,
        config_value: Dict[str, Any],
        scope: ConfigScope = ConfigScope.GLOBAL,
        scope_id: Optional[str] = None
    ) -> None:
        """
        Set configuration value.
        
        Args:
            config_key: Configuration key (supports dot notation)
            config_value: Configuration value
            scope: Configuration scope
            scope_id: Scope identifier (workflow_id or step_id)
        """
        if scope in [ConfigScope.WORKFLOW, ConfigScope.STEP] and scope_id:
            if scope_id not in self.configs[scope]:
                self.configs[scope][scope_id] = {}
            self._set_nested_value(self.configs[scope][scope_id], config_key, config_value)
        else:
            self._set_nested_value(self.configs[scope], config_key, config_value)
    
    def _set_nested_value(self, config: Dict[str, Any], key_path: str, value: Any) -> None:
        """Set nested configuration value using dot notation."""
        keys = key_path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def merge_execution_config(
        self,
        base_config: Dict[str, Any],
        template_type: str,
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Merge execution configuration for a specific template type.
        
        Args:
            base_config: Base execution configuration from cache entry
            template_type: Type of template (sql, api, function, etc.)
            workflow_id: Optional workflow ID
            step_id: Optional step ID
            
        Returns:
            Merged execution configuration
        """
        merged_config = base_config.copy()
        
        # Get type-specific configuration
        if template_type == 'sql':
            db_config = self.get_database_config(workflow_id, step_id)
            if db_config:
                merged_config['database'] = asdict(db_config)
        
        elif template_type == 'api':
            api_config = self.get_api_config(workflow_id, step_id)
            if api_config:
                merged_config.update(asdict(api_config))
        
        elif template_type == 'llm_step':
            llm_config = self.get_llm_config(workflow_id, step_id)
            if llm_config:
                merged_config['llm'] = asdict(llm_config)
        
        elif template_type == 'duckdb_sql':
            duckdb_config = self.get_duckdb_config(workflow_id, step_id)
            if duckdb_config:
                merged_config['duckdb'] = asdict(duckdb_config)
        
        # Get tool-specific configuration
        tool_config = self.get_tool_config(template_type, workflow_id, step_id)
        if tool_config:
            merged_config['tool'] = asdict(tool_config)
        
        # Get workflow configuration
        workflow_config = self.get_workflow_config(workflow_id)
        merged_config['workflow'] = asdict(workflow_config)
        
        return merged_config
    
    def validate_config(self, template_type: str, execution_config: Dict[str, Any]) -> List[str]:
        """
        Validate execution configuration for a template type.
        
        Args:
            template_type: Type of template
            execution_config: Execution configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if template_type == 'sql':
            db_config = execution_config.get('database', {})
            required_fields = ['host', 'port', 'database', 'username', 'password']
            
            for field in required_fields:
                if field not in db_config:
                    errors.append(f"Missing required database field: {field}")
        
        elif template_type == 'api':
            if 'base_url' not in execution_config:
                errors.append("Missing required field: base_url")
            
            # Validate authentication if present
            auth = execution_config.get('authentication', {})
            if auth:
                auth_type = auth.get('type')
                if auth_type == 'bearer' and 'token' not in auth:
                    errors.append("Bearer authentication requires 'token' field")
                elif auth_type == 'basic' and ('username' not in auth or 'password' not in auth):
                    errors.append("Basic authentication requires 'username' and 'password' fields")
        
        elif template_type in ['function', 'script']:
            tool_config = execution_config.get('tool', {})
            if 'timeout' in tool_config and tool_config['timeout'] <= 0:
                errors.append("Tool timeout must be positive")
        
        elif template_type == 'llm_step':
            llm_config = execution_config.get('llm', {})
            if not llm_config.get('api_key'):
                errors.append("LLM configuration requires 'api_key'")
            
            if 'temperature' in llm_config:
                temp = llm_config['temperature']
                if not isinstance(temp, (int, float)) or temp < 0 or temp > 1:
                    errors.append("LLM temperature must be between 0 and 1")
            
            if 'max_tokens' in llm_config:
                max_tokens = llm_config['max_tokens']
                if not isinstance(max_tokens, int) or max_tokens <= 0:
                    errors.append("LLM max_tokens must be a positive integer")
        
        elif template_type == 'duckdb_sql':
            duckdb_config = execution_config.get('duckdb', {})
            
            if 'threads' in duckdb_config:
                threads = duckdb_config['threads']
                if not isinstance(threads, int) or threads <= 0:
                    errors.append("DuckDB threads must be a positive integer")
            
            if 'memory_limit' in duckdb_config:
                memory_limit = duckdb_config['memory_limit']
                if not isinstance(memory_limit, str) or not memory_limit:
                    errors.append("DuckDB memory_limit must be a non-empty string")
            
            if 'database_path' in duckdb_config:
                db_path = duckdb_config['database_path']
                if db_path and not isinstance(db_path, str):
                    errors.append("DuckDB database_path must be a string")
        
        return errors
    
    def export_config(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Export current configuration.
        
        Args:
            include_sensitive: Whether to include sensitive data (passwords, tokens)
            
        Returns:
            Configuration dictionary
        """
        config = {}
        
        for scope in ConfigScope:
            scope_config = self.configs[scope].copy()
            
            if not include_sensitive:
                scope_config = self._redact_sensitive_data(scope_config)
            
            if scope_config:
                config[scope.value] = scope_config
        
        return config
    
    def _redact_sensitive_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive configuration data."""
        sensitive_keys = ['password', 'token', 'secret', 'key', 'credential']
        
        def redact_recursive(obj):
            if isinstance(obj, dict):
                return {
                    k: '***REDACTED***' if any(sensitive in k.lower() for sensitive in sensitive_keys)
                    else redact_recursive(v)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [redact_recursive(item) for item in obj]
            else:
                return obj
        
        return redact_recursive(config)


# Global configuration manager instance
_config_manager = None


def get_config_manager() -> ExecutionConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        # Look for config file in common locations
        config_paths = [
            'thinkforge_config.yaml',
            'thinkforge_config.json',
            os.path.expanduser('~/.thinkforge/config.yaml'),
            '/etc/thinkforge/config.yaml'
        ]
        
        config_path = None
        for path in config_paths:
            if os.path.exists(path):
                config_path = path
                break
        
        _config_manager = ExecutionConfigManager(config_path)
    
    return _config_manager


def reset_config_manager() -> None:
    """Reset the global configuration manager (mainly for testing)."""
    global _config_manager
    _config_manager = None