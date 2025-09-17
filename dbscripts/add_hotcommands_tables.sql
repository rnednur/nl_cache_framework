-- Hot Commands Database Schema Extension for ThinkForge
-- This script adds Hot Commands and Spaces functionality to the existing ThinkForge database

-- Set search path to use the configured schema
SET search_path TO ${DB_SCHEMA:-public};

-- Drop tables if they exist (for development/testing)
DROP TABLE IF EXISTS feedback CASCADE;
DROP TABLE IF EXISTS spaces CASCADE; 
DROP TABLE IF EXISTS command_executions CASCADE;
DROP TABLE IF EXISTS hot_commands CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Users table for authentication and authorization
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    display_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- User preferences and metadata
    domains TEXT[],
    permissions TEXT[],
    roles TEXT[],
    preferences JSONB,
    command_count INTEGER NOT NULL DEFAULT 0,
    favorite_commands TEXT[],
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Hot Commands table for storing user-created command shortcuts
CREATE TABLE hot_commands (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Command identification
    command_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(255),
    description TEXT,
    
    -- Query definition
    query_text TEXT NOT NULL,
    query_type VARCHAR(20) NOT NULL DEFAULT 'nl2sql',
    original_command TEXT,
    
    -- Categorization
    domain VARCHAR(50),
    category VARCHAR(50),
    tags TEXT[],
    
    -- Parameters and configuration
    parameters JSONB,
    parameter_schema JSONB,
    default_values JSONB,
    
    -- Status and permissions
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    is_template BOOLEAN NOT NULL DEFAULT FALSE,
    shared_with INTEGER[],
    team_id VARCHAR(50),
    permissions JSONB,
    
    -- Usage statistics
    usage_count INTEGER NOT NULL DEFAULT 0,
    success_rate REAL NOT NULL DEFAULT 0.0,
    avg_execution_time REAL, -- in milliseconds
    last_used TIMESTAMP WITH TIME ZONE,
    
    -- User feedback
    rating REAL NOT NULL DEFAULT 0.0,
    rating_count INTEGER NOT NULL DEFAULT 0,
    
    -- Output configuration
    output_format VARCHAR(20) NOT NULL DEFAULT 'table',
    visualization_config JSONB,
    export_settings JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CHECK (query_type IN ('nl2sql', 'direct_sql', 'tool_call', 'workflow')),
    CHECK (status IN ('active', 'draft', 'deprecated', 'private')),
    CHECK (output_format IN ('table', 'chart', 'report', 'simple')),
    CHECK (rating >= 0.0 AND rating <= 5.0),
    CHECK (success_rate >= 0.0 AND success_rate <= 1.0)
);

-- Command Executions table for tracking usage and performance
CREATE TABLE command_executions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    hot_command_id INTEGER REFERENCES hot_commands(id) ON DELETE SET NULL,
    
    -- Execution context
    session_id VARCHAR(255),
    command_name VARCHAR(100) NOT NULL,
    parameters JSONB,
    raw_input TEXT,
    
    -- Categorization
    domain VARCHAR(50),
    category VARCHAR(50),
    
    -- Execution results
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    execution_time_ms INTEGER,
    result_size_bytes INTEGER,
    result_rows INTEGER,
    result_data JSONB,
    
    -- Error handling
    error_message TEXT,
    error_code VARCHAR(50),
    
    -- Output configuration
    output_format VARCHAR(20),
    visualization_type VARCHAR(50),
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CHECK (status IN ('success', 'error', 'timeout', 'cancelled', 'pending'))
);

-- Spaces table for sharing and storing query results
CREATE TABLE spaces (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Space identification
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(255),
    description TEXT,
    
    -- Space type and content
    space_type VARCHAR(20) NOT NULL DEFAULT 'personal',
    content_type VARCHAR(20) NOT NULL DEFAULT 'query_result',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Content storage
    content_data JSONB,
    content_metadata JSONB,
    
    -- Source tracking
    source_command_id INTEGER REFERENCES hot_commands(id) ON DELETE SET NULL,
    source_execution_id INTEGER REFERENCES command_executions(id) ON DELETE SET NULL,
    
    -- Categorization
    domain VARCHAR(50),
    category VARCHAR(50),
    tags TEXT[],
    
    -- Sharing and permissions
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    shared_with INTEGER[],
    permissions JSONB,
    
    -- Usage statistics
    view_count INTEGER NOT NULL DEFAULT 0,
    share_count INTEGER NOT NULL DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CHECK (space_type IN ('personal', 'team', 'public', 'temporary')),
    CHECK (content_type IN ('query_result', 'visualization', 'report', 'dashboard', 'dataset'))
);

-- Feedback table for collecting user feedback
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Feedback targets
    execution_id INTEGER REFERENCES command_executions(id) ON DELETE SET NULL,
    hot_command_id INTEGER REFERENCES hot_commands(id) ON DELETE SET NULL,
    space_id INTEGER REFERENCES spaces(id) ON DELETE SET NULL,
    
    -- Feedback content
    feedback_type VARCHAR(30) NOT NULL DEFAULT 'comment',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    description TEXT,
    
    -- Context
    domain VARCHAR(50),
    category VARCHAR(50),
    command_name VARCHAR(100),
    tags TEXT[],
    
    -- Priority and helpfulness
    priority VARCHAR(10) NOT NULL DEFAULT 'medium',
    helpful_count INTEGER NOT NULL DEFAULT 0,
    unhelpful_count INTEGER NOT NULL DEFAULT 0,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CHECK (feedback_type IN ('thumbs_up', 'thumbs_down', 'rating', 'comment', 'bug_report', 'feature_request', 'improvement')),
    CHECK (status IN ('active', 'reviewed', 'resolved', 'dismissed')),
    CHECK (priority IN ('low', 'medium', 'high', 'critical'))
);

-- Create indexes for performance
-- Users indexes
CREATE INDEX ix_users_username ON users(username);
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_active ON users(is_active);

-- Hot Commands indexes
CREATE INDEX ix_hot_commands_user_id ON hot_commands(user_id);
CREATE INDEX ix_hot_commands_command_name ON hot_commands(command_name);
CREATE INDEX ix_hot_commands_user_command ON hot_commands(user_id, command_name);
CREATE INDEX ix_hot_commands_domain ON hot_commands(domain);
CREATE INDEX ix_hot_commands_category ON hot_commands(category);
CREATE INDEX ix_hot_commands_domain_category ON hot_commands(domain, category);
CREATE INDEX ix_hot_commands_status ON hot_commands(status);
CREATE INDEX ix_hot_commands_is_public ON hot_commands(is_public);
CREATE INDEX ix_hot_commands_status_public ON hot_commands(status, is_public);
CREATE INDEX ix_hot_commands_rating_usage ON hot_commands(rating, usage_count);
CREATE INDEX ix_hot_commands_created_at ON hot_commands(created_at);

-- Command Executions indexes
CREATE INDEX ix_command_executions_user_id ON command_executions(user_id);
CREATE INDEX ix_command_executions_hot_command_id ON command_executions(hot_command_id);
CREATE INDEX ix_command_executions_session_id ON command_executions(session_id);
CREATE INDEX ix_command_executions_command_name ON command_executions(command_name);
CREATE INDEX ix_command_executions_domain ON command_executions(domain);
CREATE INDEX ix_command_executions_category ON command_executions(category);
CREATE INDEX ix_command_executions_status ON command_executions(status);
CREATE INDEX ix_command_executions_status_created ON command_executions(status, created_at);
CREATE INDEX ix_command_executions_created_at ON command_executions(created_at);

-- Spaces indexes
CREATE INDEX ix_spaces_owner_id ON spaces(owner_id);
CREATE INDEX ix_spaces_name ON spaces(name);
CREATE INDEX ix_spaces_space_type ON spaces(space_type);
CREATE INDEX ix_spaces_content_type ON spaces(content_type);
CREATE INDEX ix_spaces_owner_type ON spaces(owner_id, space_type);
CREATE INDEX ix_spaces_source_command_id ON spaces(source_command_id);
CREATE INDEX ix_spaces_source_execution_id ON spaces(source_execution_id);
CREATE INDEX ix_spaces_domain ON spaces(domain);
CREATE INDEX ix_spaces_category ON spaces(category);
CREATE INDEX ix_spaces_is_public ON spaces(is_public);
CREATE INDEX ix_spaces_created_at ON spaces(created_at);

-- Feedback indexes
CREATE INDEX ix_feedback_user_id ON feedback(user_id);
CREATE INDEX ix_feedback_execution_id ON feedback(execution_id);
CREATE INDEX ix_feedback_hot_command_id ON feedback(hot_command_id);
CREATE INDEX ix_feedback_space_id ON feedback(space_id);
CREATE INDEX ix_feedback_feedback_type ON feedback(feedback_type);
CREATE INDEX ix_feedback_status ON feedback(status);
CREATE INDEX ix_feedback_type_status ON feedback(feedback_type, status);
CREATE INDEX ix_feedback_domain ON feedback(domain);
CREATE INDEX ix_feedback_category ON feedback(category);
CREATE INDEX ix_feedback_command_name ON feedback(command_name);
CREATE INDEX ix_feedback_priority ON feedback(priority);
CREATE INDEX ix_feedback_created_at ON feedback(created_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_hot_commands_updated_at BEFORE UPDATE ON hot_commands FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_spaces_updated_at BEFORE UPDATE ON spaces FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ${DB_SCHEMA:-public} TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ${DB_SCHEMA:-public} TO your_app_user;

COMMENT ON TABLE users IS 'User accounts for authentication and authorization';
COMMENT ON TABLE hot_commands IS 'User-created command shortcuts that map to NL queries or SQL';
COMMENT ON TABLE command_executions IS 'Log of command executions for performance tracking and debugging';
COMMENT ON TABLE spaces IS 'Persistent storage areas for sharing query results and visualizations';
COMMENT ON TABLE feedback IS 'User feedback on commands, executions, and spaces';