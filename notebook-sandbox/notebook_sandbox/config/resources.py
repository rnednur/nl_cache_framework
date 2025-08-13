"""
Resource configuration for notebook execution.
"""

import os
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ResourceConfig:
    """Configuration for execution resource limits."""
    
    max_memory_mb: int = 512
    max_cpu_time: int = 300  # seconds
    max_wall_time: int = 600  # seconds
    max_file_size_mb: int = 100
    max_processes: int = 10
    allow_errors: bool = False  # Allow notebook execution to continue on errors
    
    @classmethod
    def from_env(cls) -> 'ResourceConfig':
        """Create configuration from environment variables."""
        return cls(
            max_memory_mb=int(os.getenv('MAX_MEMORY_MB', '512')),
            max_cpu_time=int(os.getenv('MAX_CPU_TIME', '300')),
            max_wall_time=int(os.getenv('MAX_WALL_TIME', '600')),
            max_file_size_mb=int(os.getenv('MAX_FILE_SIZE_MB', '100')),
            max_processes=int(os.getenv('MAX_PROCESSES', '10')),
            allow_errors=os.getenv('ALLOW_ERRORS', 'false').lower() == 'true'
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ResourceConfig':
        """Create configuration from dictionary."""
        return cls(
            max_memory_mb=config_dict.get('max_memory_mb', 512),
            max_cpu_time=config_dict.get('max_cpu_time', 300),
            max_wall_time=config_dict.get('max_wall_time', 600),
            max_file_size_mb=config_dict.get('max_file_size_mb', 100),
            max_processes=config_dict.get('max_processes', 10),
            allow_errors=config_dict.get('allow_errors', False)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'max_memory_mb': self.max_memory_mb,
            'max_cpu_time': self.max_cpu_time,
            'max_wall_time': self.max_wall_time,
            'max_file_size_mb': self.max_file_size_mb,
            'max_processes': self.max_processes,
            'allow_errors': self.allow_errors
        }
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        if self.max_cpu_time <= 0:
            raise ValueError("max_cpu_time must be positive")
        if self.max_wall_time <= 0:
            raise ValueError("max_wall_time must be positive")
        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")
        if self.max_processes <= 0:
            raise ValueError("max_processes must be positive")
        
        return True