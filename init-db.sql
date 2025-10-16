-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a function to initialize the database
CREATE OR REPLACE FUNCTION init_database() RETURNS void AS $$
BEGIN
    RAISE NOTICE 'Database initialized with pgvector extension';
END;
$$ LANGUAGE plpgsql;

SELECT init_database();
