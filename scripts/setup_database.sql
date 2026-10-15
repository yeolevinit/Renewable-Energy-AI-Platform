-- Run this as the PostgreSQL superuser (e.g. postgres) to set up the project database.
-- Usage: psql -U postgres -f scripts/setup_database.sql

-- Create the application user (skip if it already exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'reai_user') THEN
        CREATE USER reai_user WITH PASSWORD 'reai_password';
    END IF;
END
$$;

-- Create the database (run separately if needed; cannot be inside a transaction)
-- psql -U postgres -c "CREATE DATABASE renewable_energy_ai OWNER reai_user;"

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE renewable_energy_ai TO reai_user;
