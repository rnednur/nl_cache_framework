#!/usr/bin/env python3
"""
Verification script for Enhanced Spaces Functionality Migration
This script verifies that the enhanced spaces migration was applied correctly.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add parent directory to path to import database configuration
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

try:
    from database import get_db_url, get_schema_name
except ImportError:
    # Fallback to environment variables
    def get_db_url():
        return os.getenv('DATABASE_URL', 
                         f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
                         f"{os.getenv('POSTGRES_PASSWORD', 'password')}@"
                         f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
                         f"{os.getenv('POSTGRES_PORT', '5432')}/"
                         f"{os.getenv('POSTGRES_DB', 'mcp_cache_db')}")
    
    def get_schema_name():
        return os.getenv('DB_SCHEMA', 'public')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationVerifier:
    """Verifies the enhanced spaces functionality migration."""
    
    def __init__(self):
        self.db_url = get_db_url()
        self.schema_name = get_schema_name()
        self.engine = create_engine(self.db_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.inspector = inspect(self.engine)
        self.verification_results = []
        
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log a verification result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        full_message = f"{status} {test_name}"
        if message:
            full_message += f": {message}"
        
        logger.info(full_message)
        self.verification_results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
        
    def verify_table_exists(self, table_name: str) -> bool:
        """Verify that a table exists."""
        exists = table_name in self.inspector.get_table_names(schema=self.schema_name)
        self.log_result(f"Table '{table_name}' exists", exists)
        return exists
        
    def verify_column_exists(self, table_name: str, column_name: str, expected_type: str = None) -> bool:
        """Verify that a column exists in a table."""
        columns = self.inspector.get_columns(table_name, schema=self.schema_name)
        column_info = next((col for col in columns if col['name'] == column_name), None)
        
        exists = column_info is not None
        message = ""
        
        if exists and expected_type:
            actual_type = str(column_info['type']).lower()
            expected_type_lower = expected_type.lower()
            type_matches = expected_type_lower in actual_type or actual_type in expected_type_lower
            if not type_matches:
                message = f"Expected type '{expected_type}', got '{actual_type}'"
                exists = False
            
        self.log_result(f"Column '{table_name}.{column_name}' exists", exists, message)
        return exists
        
    def verify_index_exists(self, index_name: str, table_name: str) -> bool:
        """Verify that an index exists."""
        try:
            check_sql = f"""
            SELECT 1 FROM pg_indexes 
            WHERE tablename = '{table_name}' 
            AND schemaname = '{self.schema_name}'
            AND indexname = '{index_name}';
            """
            result = self.session.execute(text(check_sql)).fetchone()
            exists = result is not None
            self.log_result(f"Index '{index_name}' exists", exists)
            return exists
        except Exception as e:
            self.log_result(f"Index '{index_name}' exists", False, str(e))
            return False
            
    def verify_constraint_exists(self, constraint_name: str, table_name: str) -> bool:
        """Verify that a constraint exists."""
        try:
            check_sql = f"""
            SELECT 1 FROM information_schema.table_constraints 
            WHERE table_name = '{table_name}' 
            AND table_schema = '{self.schema_name}'
            AND constraint_name = '{constraint_name}';
            """
            result = self.session.execute(text(check_sql)).fetchone()
            exists = result is not None
            self.log_result(f"Constraint '{constraint_name}' exists", exists)
            return exists
        except Exception as e:
            self.log_result(f"Constraint '{constraint_name}' exists", False, str(e))
            return False
            
    def verify_spaces_table_enhancements(self) -> bool:
        """Verify all enhancements to the spaces table."""
        logger.info("\n=== Verifying Spaces Table Enhancements ===")
        
        # Required columns with their expected types
        required_columns = [
            # Template functionality
            ("is_template", "boolean"),
            ("template_parameters", "jsonb"),
            ("template_schema", "jsonb"),
            ("base_query", "text"),
            ("source_query", "text"),
            
            # External storage
            ("storage_path", "varchar"),
            ("storage_backend", "varchar"),
            ("storage_size_bytes", "integer"),
            ("external_url", "varchar"),
            
            # Scheduling and automation
            ("schedule_type", "varchar"),
            ("schedule_config", "jsonb"),
            ("next_execution", "timestamp"),
            ("last_execution", "timestamp"),
            ("execution_count", "integer"),
            ("is_scheduled_active", "boolean"),
            
            # Enhanced sharing and permissions
            ("access_permissions", "jsonb"),
            ("team_id", "varchar"),
            
            # Expiration and cleanup
            ("expires_at", "timestamp"),
            ("auto_cleanup", "boolean"),
            ("retention_days", "integer")
        ]
        
        all_passed = True
        for column_name, expected_type in required_columns:
            if not self.verify_column_exists("spaces", column_name, expected_type):
                all_passed = False
                
        return all_passed
        
    def verify_space_access_table(self) -> bool:
        """Verify the space_access table structure."""
        logger.info("\n=== Verifying SpaceAccess Table ===")
        
        if not self.verify_table_exists("space_access"):
            return False
            
        # Required columns
        required_columns = [
            ("id", "integer"),
            ("space_id", "integer"),
            ("user_id", "integer"),
            ("granted_by", "integer"),
            ("access_level", "varchar"),
            ("is_active", "boolean"),
            ("access_count", "integer"),
            ("last_accessed", "timestamp"),
            ("expires_at", "timestamp"),
            ("restrictions", "jsonb"),
            ("created_at", "timestamp")
        ]
        
        all_passed = True
        for column_name, expected_type in required_columns:
            if not self.verify_column_exists("space_access", column_name, expected_type):
                all_passed = False
                
        return all_passed
        
    def verify_indexes(self) -> bool:
        """Verify that all required indexes exist."""
        logger.info("\n=== Verifying Indexes ===")
        
        required_indexes = [
            # Spaces indexes
            ("ix_spaces_is_template", "spaces"),
            ("ix_spaces_storage_backend", "spaces"),
            ("ix_spaces_schedule_type", "spaces"),
            ("ix_spaces_next_execution", "spaces"),
            ("ix_spaces_last_execution", "spaces"),
            ("ix_spaces_is_scheduled_active", "spaces"),
            ("ix_spaces_team_id", "spaces"),
            ("ix_spaces_expires_at", "spaces"),
            
            # SpaceAccess indexes
            ("ix_space_access_space_id", "space_access"),
            ("ix_space_access_user_id", "space_access"),
            ("ix_space_access_granted_by", "space_access"),
            ("ix_space_access_space_user", "space_access"),
            ("ix_space_access_active", "space_access"),
            ("ix_space_access_level", "space_access"),
            ("ix_space_access_last_accessed", "space_access")
        ]
        
        all_passed = True
        for index_name, table_name in required_indexes:
            if not self.verify_index_exists(index_name, table_name):
                all_passed = False
                
        return all_passed
        
    def verify_constraints(self) -> bool:
        """Verify that all required constraints exist."""
        logger.info("\n=== Verifying Constraints ===")
        
        required_constraints = [
            ("check_storage_backend", "spaces"),
            ("check_schedule_type", "spaces")
        ]
        
        all_passed = True
        for constraint_name, table_name in required_constraints:
            if not self.verify_constraint_exists(constraint_name, table_name):
                all_passed = False
                
        return all_passed
        
    def verify_foreign_keys(self) -> bool:
        """Verify foreign key relationships."""
        logger.info("\n=== Verifying Foreign Keys ===")
        
        try:
            # Check space_access foreign keys
            fk_check_sql = f"""
            SELECT 
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE 
                tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_name = 'space_access'
                AND tc.table_schema = '{self.schema_name}';
            """
            
            result = self.session.execute(text(fk_check_sql)).fetchall()
            
            expected_fks = {
                'space_id': 'spaces',
                'user_id': 'users',
                'granted_by': 'users'
            }
            
            found_fks = {}
            for row in result:
                column_name = row[2]
                foreign_table = row[3]
                found_fks[column_name] = foreign_table
                
            all_passed = True
            for column, expected_table in expected_fks.items():
                if column in found_fks and found_fks[column] == expected_table:
                    self.log_result(f"Foreign key '{column}' -> '{expected_table}'", True)
                else:
                    self.log_result(f"Foreign key '{column}' -> '{expected_table}'", False)
                    all_passed = False
                    
            return all_passed
            
        except Exception as e:
            self.log_result("Foreign key verification", False, str(e))
            return False
            
    def verify_data_integrity(self) -> bool:
        """Verify data integrity after migration."""
        logger.info("\n=== Verifying Data Integrity ===")
        
        try:
            # Check that existing spaces have default values
            check_sql = f"""
            SELECT COUNT(*) as total_spaces,
                   COUNT(*) FILTER (WHERE is_template = FALSE) as non_template_count,
                   COUNT(*) FILTER (WHERE storage_backend = 'local') as local_storage_count,
                   COUNT(*) FILTER (WHERE schedule_type = 'none') as no_schedule_count
            FROM {self.schema_name}.spaces;
            """
            
            result = self.session.execute(text(check_sql)).fetchone()
            
            if result:
                total = result[0]
                non_template = result[1]
                local_storage = result[2]
                no_schedule = result[3]
                
                self.log_result(f"Data integrity: {total} total spaces", True, 
                               f"{non_template} non-template, {local_storage} local storage, {no_schedule} no schedule")
                
                # All existing spaces should have these defaults
                integrity_ok = (non_template == total and local_storage == total and no_schedule == total)
                self.log_result("Existing spaces have proper defaults", integrity_ok)
                
                return integrity_ok
            else:
                self.log_result("Data integrity check", False, "No data returned")
                return False
                
        except Exception as e:
            self.log_result("Data integrity check", False, str(e))
            return False
            
    def run_verification(self) -> bool:
        """Run complete verification suite."""
        logger.info("🔍 Starting Enhanced Spaces Migration Verification...")
        
        try:
            # Run all verification tests
            spaces_ok = self.verify_spaces_table_enhancements()
            space_access_ok = self.verify_space_access_table()
            indexes_ok = self.verify_indexes()
            constraints_ok = self.verify_constraints()
            fks_ok = self.verify_foreign_keys()
            data_ok = self.verify_data_integrity()
            
            # Calculate overall results
            total_tests = len(self.verification_results)
            passed_tests = sum(1 for result in self.verification_results if result['passed'])
            failed_tests = total_tests - passed_tests
            
            # Print summary
            logger.info(f"\n=== Verification Summary ===")
            logger.info(f"Total tests: {total_tests}")
            logger.info(f"Passed: {passed_tests}")
            logger.info(f"Failed: {failed_tests}")
            
            if failed_tests > 0:
                logger.info(f"\n❌ Failed tests:")
                for result in self.verification_results:
                    if not result['passed']:
                        message = f" - {result['message']}" if result['message'] else ""
                        logger.info(f"  • {result['test']}{message}")
            
            overall_success = failed_tests == 0
            
            if overall_success:
                logger.info(f"\n✅ All verification tests passed! Enhanced spaces migration is complete and verified.")
            else:
                logger.info(f"\n❌ {failed_tests} verification tests failed. Please review the migration.")
                
            return overall_success
            
        except Exception as e:
            logger.error(f"Verification failed with error: {e}")
            return False
        finally:
            self.session.close()

def main():
    """Main entry point for the verification script."""
    verifier = MigrationVerifier()
    success = verifier.run_verification()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()