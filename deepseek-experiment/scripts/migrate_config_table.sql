-- Migration: Create bot_configurations table for versioned configuration management
-- Run this in your Supabase SQL editor

-- Create table for versioned bot configurations
CREATE TABLE IF NOT EXISTS bot_configurations (
    id SERIAL PRIMARY KEY,
    version INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config_json JSONB NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system'
);

-- Create unique constraint on version number
CREATE UNIQUE INDEX IF NOT EXISTS idx_bot_configurations_version ON bot_configurations(version);

-- Create index on is_active for quick lookups
CREATE INDEX IF NOT EXISTS idx_bot_configurations_active ON bot_configurations(is_active) WHERE is_active = TRUE;

-- Create index on is_default
CREATE INDEX IF NOT EXISTS idx_bot_configurations_default ON bot_configurations(is_default) WHERE is_default = TRUE;

-- Create index on created_at for sorting
CREATE INDEX IF NOT EXISTS idx_bot_configurations_created_at ON bot_configurations(created_at DESC);

-- Create index on config_json for JSON queries
CREATE INDEX IF NOT EXISTS idx_bot_configurations_config_json ON bot_configurations USING gin(config_json);

-- Ensure only one active configuration at a time
CREATE OR REPLACE FUNCTION ensure_single_active_config()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_active = TRUE THEN
        -- Deactivate all other configurations
        UPDATE bot_configurations
        SET is_active = FALSE
        WHERE id != NEW.id AND is_active = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to enforce single active configuration
DROP TRIGGER IF EXISTS trigger_single_active_config ON bot_configurations;
CREATE TRIGGER trigger_single_active_config
    BEFORE INSERT OR UPDATE ON bot_configurations
    FOR EACH ROW
    EXECUTE FUNCTION ensure_single_active_config();

-- Ensure only one default configuration
CREATE OR REPLACE FUNCTION ensure_single_default_config()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_default = TRUE THEN
        -- Unset default on all other configurations
        UPDATE bot_configurations
        SET is_default = FALSE
        WHERE id != NEW.id AND is_default = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to enforce single default configuration
DROP TRIGGER IF EXISTS trigger_single_default_config ON bot_configurations;
CREATE TRIGGER trigger_single_default_config
    BEFORE INSERT OR UPDATE ON bot_configurations
    FOR EACH ROW
    EXECUTE FUNCTION ensure_single_default_config();

-- Enable Row Level Security
ALTER TABLE bot_configurations ENABLE ROW LEVEL SECURITY;

-- Create policy for public access (adjust based on your security needs)
DROP POLICY IF EXISTS "Allow all operations on bot_configurations" ON bot_configurations;
CREATE POLICY "Allow all operations on bot_configurations" ON bot_configurations FOR ALL USING (true);

-- Function to get next version number
CREATE OR REPLACE FUNCTION get_next_config_version()
RETURNS INTEGER AS $$
DECLARE
    next_version INTEGER;
BEGIN
    SELECT COALESCE(MAX(version), 0) + 1 INTO next_version FROM bot_configurations;
    RETURN next_version;
END;
$$ LANGUAGE plpgsql;

-- Migrate existing bot_config entries to bot_configurations (if any exist)
-- This creates a default configuration from the old bot_config table
DO $$
DECLARE
    config_data JSONB;
    config_count INTEGER;
BEGIN
    -- Check if bot_config table exists and has data
    SELECT COUNT(*) INTO config_count FROM bot_config;
    
    IF config_count > 0 THEN
        -- Build JSONB object from bot_config key-value pairs
        SELECT jsonb_object_agg(key, value) INTO config_data
        FROM bot_config;
        
        -- Insert as default configuration if no configurations exist yet
        IF NOT EXISTS (SELECT 1 FROM bot_configurations WHERE is_default = TRUE) THEN
            INSERT INTO bot_configurations (
                version,
                name,
                description,
                config_json,
                is_active,
                is_default,
                created_by
            ) VALUES (
                get_next_config_version(),
                'Default Configuration',
                'Migrated from bot_config table',
                config_data,
                TRUE,
                TRUE,
                'migration'
            );
        END IF;
    END IF;
END $$;

-- Comment on table
COMMENT ON TABLE bot_configurations IS 'Versioned bot configurations with full JSON storage';
COMMENT ON COLUMN bot_configurations.version IS 'Sequential version number for this configuration';
COMMENT ON COLUMN bot_configurations.config_json IS 'Complete configuration as JSONB';
COMMENT ON COLUMN bot_configurations.is_active IS 'Whether this configuration is currently active';
COMMENT ON COLUMN bot_configurations.is_default IS 'Whether this is the default system configuration';

