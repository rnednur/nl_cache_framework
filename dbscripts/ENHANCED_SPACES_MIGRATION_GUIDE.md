# Enhanced Spaces Functionality Migration Guide

This guide covers the migration process for adding enhanced spaces functionality to the ThinkForge framework, including templates, scheduling, external storage, and granular access control.

## Overview

The enhanced spaces migration adds the following functionality:

### 🎯 **Template Functionality**
- Parameterized spaces that can be executed with different inputs
- JSON schema validation for template parameters
- Template rendering with parameter substitution

### 📅 **Scheduling & Automation**
- Interval-based scheduling (every N minutes)
- CRON expression scheduling
- Webhook-triggered execution
- Next execution time tracking

### 💾 **External Storage**
- Support for local, S3, GCS, and Azure storage backends
- Webpage export for sharing
- Public URL generation with expiration

### 🔐 **Granular Access Control**
- Fine-grained permissions (VIEW, COMMENT, EDIT, ADMIN)
- User-specific access grants with expiration
- Team-based sharing capabilities

### ⏰ **Expiration & Cleanup**
- Space expiration dates
- Automatic cleanup policies
- Retention period management

## Prerequisites

1. **Existing Database**: The base ThinkForge database with the original spaces table must exist
2. **Dependencies**: Ensure required Python packages are installed:
   ```bash
   pip install sqlalchemy psycopg2-binary python-dotenv croniter boto3 google-cloud-storage azure-storage-blob
   ```
3. **Database Access**: User must have privileges to alter tables and create indexes
4. **Environment Variables**: Proper database connection configuration

## Migration Options

### Option 1: SQL Migration (Fast)

For simple environments where you want a quick SQL-based migration:

```bash
# Set environment variables for your database
export DB_SCHEMA=public  # or your schema name

# Run the SQL migration
psql -h localhost -U your_user -d your_database \
     -v schema_name=${DB_SCHEMA} \
     -f add_enhanced_spaces_functionality.sql
```

### Option 2: Python Migration (Recommended)

For production environments with better error handling and validation:

```bash
# Ensure your .env file is configured with database credentials
python add_enhanced_spaces_functionality.py
```

The Python migration provides:
- ✅ Comprehensive error handling
- ✅ Idempotent operations (safe to re-run)
- ✅ Detailed logging
- ✅ Automatic rollback on failure
- ✅ Column existence checking

## Migration Steps

The migration performs the following operations:

### 1. **Add Enhanced Columns to Spaces Table**

```sql
-- Template functionality
ALTER TABLE spaces ADD COLUMN is_template BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE spaces ADD COLUMN template_parameters JSONB;
ALTER TABLE spaces ADD COLUMN template_schema JSONB;
ALTER TABLE spaces ADD COLUMN base_query TEXT;
ALTER TABLE spaces ADD COLUMN source_query TEXT;

-- External storage
ALTER TABLE spaces ADD COLUMN storage_path VARCHAR(500);
ALTER TABLE spaces ADD COLUMN storage_backend VARCHAR(20) NOT NULL DEFAULT 'local';
ALTER TABLE spaces ADD COLUMN storage_size_bytes INTEGER NOT NULL DEFAULT 0;
ALTER TABLE spaces ADD COLUMN external_url VARCHAR(1000);

-- Scheduling and automation
ALTER TABLE spaces ADD COLUMN schedule_type VARCHAR(20) NOT NULL DEFAULT 'none';
ALTER TABLE spaces ADD COLUMN schedule_config JSONB;
ALTER TABLE spaces ADD COLUMN next_execution TIMESTAMP WITH TIME ZONE;
ALTER TABLE spaces ADD COLUMN last_execution TIMESTAMP WITH TIME ZONE;
ALTER TABLE spaces ADD COLUMN execution_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE spaces ADD COLUMN is_scheduled_active BOOLEAN NOT NULL DEFAULT FALSE;

-- Enhanced sharing and permissions
ALTER TABLE spaces ADD COLUMN access_permissions JSONB;
ALTER TABLE spaces ADD COLUMN team_id VARCHAR(100);

-- Expiration and cleanup
ALTER TABLE spaces ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE spaces ADD COLUMN auto_cleanup BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE spaces ADD COLUMN retention_days INTEGER;
```

### 2. **Create SpaceAccess Table**

```sql
CREATE TABLE space_access (
    id SERIAL PRIMARY KEY,
    space_id INTEGER NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    granted_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_level VARCHAR(20) NOT NULL DEFAULT 'view',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    restrictions JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CHECK (access_level IN ('view', 'comment', 'edit', 'admin')),
    UNIQUE (space_id, user_id)
);
```

### 3. **Add Constraints and Indexes**

- Check constraints for valid enum values
- Performance indexes for new columns
- Composite indexes for common query patterns

### 4. **Update Existing Data**

- Set default values for existing spaces
- Ensure data consistency

## Verification

After migration, verify the changes using the verification script:

```bash
python verify_enhanced_spaces_migration.py
```

The verification script checks:

- ✅ All new columns exist with correct types
- ✅ SpaceAccess table created successfully
- ✅ All indexes are present
- ✅ Constraints are properly applied
- ✅ Foreign key relationships are correct
- ✅ Existing data has proper default values

## Manual Verification Queries

You can also manually verify the migration:

```sql
-- Check new columns in spaces table
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'spaces' AND table_schema = 'public'
ORDER BY ordinal_position;

-- Verify space_access table exists
SELECT table_name FROM information_schema.tables 
WHERE table_name = 'space_access' AND table_schema = 'public';

-- Check indexes
SELECT indexname, tablename FROM pg_indexes 
WHERE tablename IN ('spaces', 'space_access') 
AND schemaname = 'public'
ORDER BY tablename, indexname;

-- Verify constraints
SELECT constraint_name, table_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name IN ('spaces', 'space_access')
AND table_schema = 'public';

-- Check foreign keys for space_access
SELECT 
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
AND tc.table_name = 'space_access';
```

## Testing the New Functionality

After migration, test the enhanced functionality:

### 1. **Template Creation**
```python
# Create a template space
space = Space(
    name="sales_report_template",
    is_template=True,
    template_parameters=[
        {"name": "start_date", "type": "date", "required": True},
        {"name": "region", "type": "string", "required": False}
    ],
    base_query="SELECT * FROM sales WHERE date >= {start_date} AND region = {region}"
)
```

### 2. **Scheduling**
```python
# Schedule a space for execution
space.schedule_type = ScheduleType.INTERVAL
space.schedule_config = {"interval_minutes": 60}
space.is_scheduled_active = True
```

### 3. **Access Control**
```python
# Grant access to another user
access = SpaceAccess(
    space_id=space.id,
    user_id=other_user_id,
    granted_by=current_user_id,
    access_level=AccessLevel.VIEW,
    expires_at=datetime.utcnow() + timedelta(days=30)
)
```

### 4. **External Storage**
```python
# Configure external storage
space.storage_backend = StorageBackend.S3
space.external_url = "https://bucket.s3.amazonaws.com/spaces/123/report.html"
```

## Rollback Instructions

If you need to rollback the migration:

### ⚠️ **Warning**: Rollback will lose all enhanced spaces data

```sql
-- Drop the space_access table
DROP TABLE IF EXISTS space_access CASCADE;

-- Remove enhanced columns from spaces (this will lose data!)
ALTER TABLE spaces DROP COLUMN IF EXISTS is_template;
ALTER TABLE spaces DROP COLUMN IF EXISTS template_parameters;
ALTER TABLE spaces DROP COLUMN IF EXISTS template_schema;
ALTER TABLE spaces DROP COLUMN IF EXISTS base_query;
ALTER TABLE spaces DROP COLUMN IF EXISTS source_query;
ALTER TABLE spaces DROP COLUMN IF EXISTS storage_path;
ALTER TABLE spaces DROP COLUMN IF EXISTS storage_backend;
ALTER TABLE spaces DROP COLUMN IF EXISTS storage_size_bytes;
ALTER TABLE spaces DROP COLUMN IF EXISTS external_url;
ALTER TABLE spaces DROP COLUMN IF EXISTS schedule_type;
ALTER TABLE spaces DROP COLUMN IF EXISTS schedule_config;
ALTER TABLE spaces DROP COLUMN IF EXISTS next_execution;
ALTER TABLE spaces DROP COLUMN IF EXISTS last_execution;
ALTER TABLE spaces DROP COLUMN IF EXISTS execution_count;
ALTER TABLE spaces DROP COLUMN IF EXISTS is_scheduled_active;
ALTER TABLE spaces DROP COLUMN IF EXISTS access_permissions;
ALTER TABLE spaces DROP COLUMN IF EXISTS team_id;
ALTER TABLE spaces DROP COLUMN IF EXISTS expires_at;
ALTER TABLE spaces DROP COLUMN IF EXISTS auto_cleanup;
ALTER TABLE spaces DROP COLUMN IF EXISTS retention_days;

-- Drop associated indexes
DROP INDEX IF EXISTS ix_spaces_is_template;
DROP INDEX IF EXISTS ix_spaces_storage_backend;
DROP INDEX IF EXISTS ix_spaces_schedule_type;
-- ... (continue for all indexes)
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Ensure database user has ALTER TABLE privileges
   - Grant necessary permissions: `GRANT ALL ON SCHEMA public TO your_user;`

2. **Column Already Exists**
   - Migration is idempotent - safe to re-run
   - Check if previous migration partially completed

3. **Foreign Key Violations**
   - Ensure users table exists before creating space_access
   - Verify referential integrity

4. **Enum Type Issues**
   - PostgreSQL enum additions may require specific handling
   - Check if content_type enum exists

### Migration Logs

Check migration logs for detailed information:
```bash
# Python migration logs to stdout
python add_enhanced_spaces_functionality.py 2>&1 | tee migration.log

# Check PostgreSQL logs
tail -f /var/log/postgresql/postgresql-*.log
```

### Performance Considerations

- **Large Tables**: For tables with millions of rows, consider:
  - Running during maintenance windows
  - Adding columns in batches
  - Monitoring disk space for index creation

- **Index Creation**: Can be slow on large tables
  - Consider creating indexes separately after migration
  - Use `CREATE INDEX CONCURRENTLY` for production

## Post-Migration Tasks

1. **Update Application Code**: Ensure your application uses the new enhanced models
2. **Update API Documentation**: Document new endpoints and functionality
3. **Configure External Storage**: Set up S3/GCS/Azure credentials if using external storage
4. **Set Up Monitoring**: Monitor the new scheduled execution functionality
5. **User Training**: Train users on new template and sharing features

## Support

If you encounter issues:

1. Check the verification script output
2. Review migration logs
3. Verify database permissions
4. Check foreign key constraints
5. Ensure all prerequisites are met

For additional support, check the ThinkForge documentation or create an issue in the repository.