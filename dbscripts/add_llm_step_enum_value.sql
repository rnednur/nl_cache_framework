-- Add 'llm_step' value to the template_type ENUM
-- This script adds the 'llm_step' value to the existing template_type enum

-- Check if the enum value already exists
DO $$
BEGIN
    -- Check if llm_step already exists in the enum
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'llm_step' 
        AND enumtypid = (
            SELECT oid FROM pg_type WHERE typname = 'template_type'
        )
    ) THEN
        -- Add the new enum value
        ALTER TYPE template_type ADD VALUE 'llm_step';
        RAISE NOTICE 'Added llm_step value to template_type enum';
    ELSE
        RAISE NOTICE 'llm_step value already exists in template_type enum';
    END IF;
END $$;