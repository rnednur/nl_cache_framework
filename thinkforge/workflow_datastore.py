"""
Workflow Data Store for ThinkForge Framework

This module provides embedded DuckDB-based data persistence for workflow execution,
enabling SQL-based data transformations and persistent intermediate results.
"""

import os
import json
import logging
import uuid
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union, Iterator
from pathlib import Path
import pandas as pd
from dataclasses import dataclass

try:
    import duckdb
    import pyarrow as pa
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    duckdb = None
    pa = None

logger = logging.getLogger(__name__)


@dataclass
class TableInfo:
    """Information about a table in the workflow datastore."""
    name: str
    step_id: str
    created_at: datetime
    rows: int
    columns: List[str]
    schema: Dict[str, str]
    size_bytes: int


class WorkflowDataStore:
    """
    Embedded DuckDB-based data store for workflow execution.
    
    Provides persistent storage for step outputs, SQL analytics capabilities,
    and efficient data passing between workflow steps.
    """
    
    def __init__(
        self,
        workflow_id: str,
        run_id: Optional[str] = None,
        database_path: Optional[str] = None,
        temp_dir: Optional[str] = None,
        auto_cleanup: bool = True
    ):
        """
        Initialize workflow data store.
        
        Args:
            workflow_id: Unique identifier for the workflow
            run_id: Unique identifier for this execution run
            database_path: Path to database file (if None, creates temporary)
            temp_dir: Directory for temporary files
            auto_cleanup: Whether to cleanup temporary files on close
        """
        if not DUCKDB_AVAILABLE:
            raise ImportError("DuckDB not available. Install with: pip install duckdb pandas pyarrow")
        
        self.workflow_id = workflow_id
        self.run_id = run_id or str(uuid.uuid4())
        self.auto_cleanup = auto_cleanup
        self._connection = None
        self._database_path = database_path
        self._temp_dir = temp_dir or tempfile.gettempdir()
        
        # Create database path if not provided
        if not self._database_path:
            db_name = f"workflow_{self.workflow_id}_{self.run_id}.duckdb"
            self._database_path = os.path.join(self._temp_dir, db_name)
        
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(self._database_path), exist_ok=True)
        
        # Initialize connection and schema
        self._initialize_database()
        
        logger.info(f"WorkflowDataStore initialized: {self._database_path}")
    
    def _initialize_database(self) -> None:
        """Initialize database connection and create system tables."""
        try:
            self._connection = duckdb.connect(self._database_path)
            
            # Create system tables for metadata
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS workflow_metadata (
                    workflow_id VARCHAR,
                    run_id VARCHAR,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    status VARCHAR,
                    metadata JSON
                )
            """)
            
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS step_metadata (
                    step_id VARCHAR,
                    table_name VARCHAR,
                    created_at TIMESTAMP,
                    step_type VARCHAR,
                    template_type VARCHAR,
                    execution_time_ms INTEGER,
                    rows INTEGER,
                    columns JSON,
                    metadata JSON
                )
            """)
            
            # Insert workflow metadata
            self._connection.execute("""
                INSERT INTO workflow_metadata 
                (workflow_id, run_id, created_at, updated_at, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                self.workflow_id,
                self.run_id,
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
                'running',
                json.dumps({'initialized': True})
            ])
            
            self._connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def store_step_output(
        self,
        step_id: str,
        data: Any,
        template_type: str = "unknown",
        execution_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store step output data in DuckDB.
        
        Args:
            step_id: Unique identifier for the step
            data: Output data from the step
            template_type: Type of template that generated the data
            execution_time_ms: Execution time in milliseconds
            metadata: Additional metadata about the step
            
        Returns:
            Table name where data was stored
        """
        table_name = f"step_{step_id}_{int(datetime.now().timestamp())}"
        
        try:
            # Convert data to DataFrame
            df = self._normalize_data_to_dataframe(data, step_id)
            
            # Store DataFrame in DuckDB
            self._connection.register(f"temp_{table_name}", df)
            self._connection.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_{table_name}")
            self._connection.unregister(f"temp_{table_name}")
            
            # Store metadata
            columns_info = [{"name": col, "type": str(df[col].dtype)} for col in df.columns]
            
            self._connection.execute("""
                INSERT INTO step_metadata 
                (step_id, table_name, created_at, step_type, template_type, 
                 execution_time_ms, rows, columns, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                step_id,
                table_name,
                datetime.now(timezone.utc),
                'output',
                template_type,
                execution_time_ms,
                len(df),
                json.dumps(columns_info),
                json.dumps(metadata or {})
            ])
            
            self._connection.commit()
            
            logger.info(f"Stored {len(df)} rows for step {step_id} in table {table_name}")
            return table_name
            
        except Exception as e:
            logger.error(f"Failed to store step output for {step_id}: {e}")
            raise
    
    def get_step_output(
        self,
        step_id: str,
        as_dict: bool = False,
        limit: Optional[int] = None
    ) -> Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]:
        """
        Retrieve step output data.
        
        Args:
            step_id: Step identifier
            as_dict: Whether to return as dictionary/list instead of DataFrame
            limit: Maximum number of rows to return
            
        Returns:
            Step output data as DataFrame or dict/list
        """
        try:
            # Find the most recent table for this step
            result = self._connection.execute("""
                SELECT table_name 
                FROM step_metadata 
                WHERE step_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, [step_id]).fetchone()
            
            if not result:
                raise ValueError(f"No data found for step: {step_id}")
            
            table_name = result[0]
            
            # Query the data
            query = f"SELECT * FROM {table_name}"
            if limit:
                query += f" LIMIT {limit}"
            
            df = self._connection.execute(query).fetch_df()
            
            if as_dict:
                if len(df) == 1:
                    return df.to_dict('records')[0]
                else:
                    return df.to_dict('records')
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get step output for {step_id}: {e}")
            raise
    
    def execute_sql(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        as_dataframe: bool = True
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Execute SQL query against workflow data.
        
        Args:
            query: SQL query string
            parameters: Query parameters for substitution
            as_dataframe: Whether to return as DataFrame
            
        Returns:
            Query results as DataFrame or list of dicts
        """
        try:
            # Substitute parameters if provided
            if parameters:
                for key, value in parameters.items():
                    if isinstance(value, str):
                        query = query.replace(f":{key}", f"'{value}'")
                    else:
                        query = query.replace(f":{key}", str(value))
            
            result = self._connection.execute(query)
            
            if as_dataframe:
                return result.fetch_df()
            else:
                columns = [desc[0] for desc in result.description]
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to execute SQL query: {e}")
            raise
    
    def get_available_tables(self) -> List[TableInfo]:
        """
        Get information about all available tables.
        
        Returns:
            List of TableInfo objects
        """
        try:
            result = self._connection.execute("""
                SELECT 
                    step_id,
                    table_name,
                    created_at,
                    template_type,
                    rows,
                    columns
                FROM step_metadata
                ORDER BY created_at DESC
            """).fetchall()
            
            tables = []
            for row in result:
                step_id, table_name, created_at, template_type, rows, columns_json = row
                columns_info = json.loads(columns_json)
                
                # Get table size
                size_result = self._connection.execute(f"""
                    SELECT pg_total_relation_size('{table_name}') as size
                """).fetchone()
                size_bytes = size_result[0] if size_result else 0
                
                table_info = TableInfo(
                    name=table_name,
                    step_id=step_id,
                    created_at=created_at,
                    rows=rows,
                    columns=[col['name'] for col in columns_info],
                    schema={col['name']: col['type'] for col in columns_info},
                    size_bytes=size_bytes
                )
                tables.append(table_info)
            
            return tables
            
        except Exception as e:
            logger.error(f"Failed to get available tables: {e}")
            return []
    
    def create_view(
        self,
        view_name: str,
        query: str,
        step_id: Optional[str] = None
    ) -> None:
        """
        Create a SQL view for reusable queries.
        
        Args:
            view_name: Name of the view to create
            query: SQL query defining the view
            step_id: Optional step ID to associate with the view
        """
        try:
            self._connection.execute(f"CREATE OR REPLACE VIEW {view_name} AS {query}")
            
            # Record view metadata
            if step_id:
                self._connection.execute("""
                    INSERT INTO step_metadata 
                    (step_id, table_name, created_at, step_type, template_type, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    step_id,
                    view_name,
                    datetime.now(timezone.utc),
                    'view',
                    'sql',
                    json.dumps({'query': query, 'type': 'view'})
                ])
            
            self._connection.commit()
            logger.info(f"Created view: {view_name}")
            
        except Exception as e:
            logger.error(f"Failed to create view {view_name}: {e}")
            raise
    
    def export_table(
        self,
        table_or_step_id: str,
        file_path: str,
        format: str = "csv"
    ) -> None:
        """
        Export table data to file.
        
        Args:
            table_or_step_id: Table name or step ID
            file_path: Output file path
            format: Export format (csv, parquet, json)
        """
        try:
            # Determine if it's a table name or step ID
            if table_or_step_id.startswith("step_"):
                table_name = table_or_step_id
            else:
                # Look up table by step ID
                result = self._connection.execute("""
                    SELECT table_name 
                    FROM step_metadata 
                    WHERE step_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, [table_or_step_id]).fetchone()
                
                if not result:
                    raise ValueError(f"No table found for step: {table_or_step_id}")
                table_name = result[0]
            
            # Export based on format
            if format.lower() == "csv":
                self._connection.execute(f"COPY {table_name} TO '{file_path}' (FORMAT CSV, HEADER)")
            elif format.lower() == "parquet":
                self._connection.execute(f"COPY {table_name} TO '{file_path}' (FORMAT PARQUET)")
            elif format.lower() == "json":
                self._connection.execute(f"COPY {table_name} TO '{file_path}' (FORMAT JSON)")
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Exported {table_name} to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export table: {e}")
            raise
    
    def cleanup_old_data(self, keep_latest_n: int = 10) -> None:
        """
        Clean up old step data, keeping only the latest N entries per step.
        
        Args:
            keep_latest_n: Number of latest entries to keep per step
        """
        try:
            # Get tables to drop
            result = self._connection.execute(f"""
                SELECT table_name 
                FROM (
                    SELECT table_name,
                           ROW_NUMBER() OVER (PARTITION BY step_id ORDER BY created_at DESC) as rn
                    FROM step_metadata
                ) ranked
                WHERE rn > {keep_latest_n}
            """).fetchall()
            
            # Drop old tables
            for (table_name,) in result:
                try:
                    self._connection.execute(f"DROP TABLE IF EXISTS {table_name}")
                    self._connection.execute(
                        "DELETE FROM step_metadata WHERE table_name = ?",
                        [table_name]
                    )
                    logger.info(f"Cleaned up old table: {table_name}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup table {table_name}: {e}")
            
            self._connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    def get_data_lineage(self) -> Dict[str, List[str]]:
        """
        Get data lineage information showing step dependencies.
        
        Returns:
            Dictionary mapping step IDs to their data dependencies
        """
        try:
            # This is a simplified version - in a full implementation,
            # you'd track which steps read from which tables
            result = self._connection.execute("""
                SELECT step_id, table_name, created_at
                FROM step_metadata
                ORDER BY created_at
            """).fetchall()
            
            lineage = {}
            for step_id, table_name, created_at in result:
                lineage[step_id] = []  # Would populate with actual dependencies
            
            return lineage
            
        except Exception as e:
            logger.error(f"Failed to get data lineage: {e}")
            return {}
    
    def _normalize_data_to_dataframe(self, data: Any, step_id: str) -> pd.DataFrame:
        """
        Convert various data types to pandas DataFrame.
        
        Args:
            data: Input data in various formats
            step_id: Step identifier for context
            
        Returns:
            Normalized pandas DataFrame
        """
        if isinstance(data, pd.DataFrame):
            return data
        
        elif isinstance(data, dict):
            # Single record
            return pd.DataFrame([data])
        
        elif isinstance(data, list):
            if not data:
                # Empty list - create DataFrame with step metadata
                return pd.DataFrame([{
                    'step_id': step_id,
                    'result': None,
                    'timestamp': datetime.now(timezone.utc)
                }])
            
            # List of records
            if isinstance(data[0], dict):
                return pd.DataFrame(data)
            else:
                # List of values
                return pd.DataFrame({'value': data})
        
        elif isinstance(data, str):
            try:
                # Try to parse as JSON
                parsed = json.loads(data)
                return self._normalize_data_to_dataframe(parsed, step_id)
            except json.JSONDecodeError:
                # Treat as single text value
                return pd.DataFrame([{
                    'step_id': step_id,
                    'text_result': data,
                    'timestamp': datetime.now(timezone.utc)
                }])
        
        else:
            # Single value of other type
            return pd.DataFrame([{
                'step_id': step_id,
                'result': str(data),
                'result_type': type(data).__name__,
                'timestamp': datetime.now(timezone.utc)
            }])
    
    def close(self) -> None:
        """Close database connection and cleanup if requested."""
        if self._connection:
            try:
                # Update workflow status
                self._connection.execute("""
                    UPDATE workflow_metadata 
                    SET status = 'completed', updated_at = ?
                    WHERE workflow_id = ? AND run_id = ?
                """, [datetime.now(timezone.utc), self.workflow_id, self.run_id])
                
                self._connection.commit()
                self._connection.close()
                
            except Exception as e:
                logger.warning(f"Error during close: {e}")
            
            self._connection = None
        
        # Cleanup temporary files if requested
        if self.auto_cleanup and self._database_path:
            try:
                if os.path.exists(self._database_path):
                    os.remove(self._database_path)
                    logger.info(f"Cleaned up database file: {self._database_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup database file: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.close()


class DataStoreManager:
    """
    Manager for workflow data stores.
    
    Handles creation, caching, and lifecycle management of WorkflowDataStore instances.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize data store manager.
        
        Args:
            base_path: Base path for storing workflow databases
        """
        self.base_path = base_path or tempfile.gettempdir()
        self._active_stores: Dict[str, WorkflowDataStore] = {}
    
    def get_datastore(
        self,
        workflow_id: str,
        run_id: Optional[str] = None,
        **kwargs
    ) -> WorkflowDataStore:
        """
        Get or create a workflow data store.
        
        Args:
            workflow_id: Workflow identifier
            run_id: Run identifier
            **kwargs: Additional arguments for WorkflowDataStore
            
        Returns:
            WorkflowDataStore instance
        """
        key = f"{workflow_id}_{run_id or 'default'}"
        
        if key not in self._active_stores:
            db_path = os.path.join(self.base_path, f"workflow_{key}.duckdb")
            
            self._active_stores[key] = WorkflowDataStore(
                workflow_id=workflow_id,
                run_id=run_id,
                database_path=db_path,
                **kwargs
            )
        
        return self._active_stores[key]
    
    def close_all(self) -> None:
        """Close all active data stores."""
        for store in self._active_stores.values():
            store.close()
        self._active_stores.clear()
    
    def cleanup_old_workflows(self, max_age_days: int = 7) -> None:
        """
        Clean up old workflow databases.
        
        Args:
            max_age_days: Maximum age in days before cleanup
        """
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
        
        for file_path in Path(self.base_path).glob("workflow_*.duckdb"):
            if file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    logger.info(f"Cleaned up old workflow database: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {file_path}: {e}")


# Global data store manager instance
_datastore_manager = DataStoreManager()


def get_workflow_datastore(
    workflow_id: str,
    run_id: Optional[str] = None,
    **kwargs
) -> WorkflowDataStore:
    """
    Convenience function to get a workflow data store.
    
    Args:
        workflow_id: Workflow identifier
        run_id: Run identifier
        **kwargs: Additional arguments
        
    Returns:
        WorkflowDataStore instance
    """
    return _datastore_manager.get_datastore(workflow_id, run_id, **kwargs)