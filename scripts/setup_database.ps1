#!/usr/bin/env pwsh
# Run as: .\scripts\setup_database.ps1 -PgPassword "your_postgres_password"
# This creates the reai_user and renewable_energy_ai database.

param(
    [string]$PgHost = "localhost",
    [string]$PgPort = "5432",
    [string]$PgUser = "postgres",
    [string]$PgPassword = "postgres"
)

$env:PATH += ";C:\Program Files\PostgreSQL\18\bin"
$env:PGPASSWORD = $PgPassword

Write-Host "Creating database user reai_user..."
psql -U $PgUser -h $PgHost -p $PgPort -c "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'reai_user') THEN CREATE USER reai_user WITH PASSWORD 'reai_password'; END IF; END `$`$;"

Write-Host "Creating database renewable_energy_ai..."
psql -U $PgUser -h $PgHost -p $PgPort -c "CREATE DATABASE renewable_energy_ai OWNER reai_user;" 2>&1

Write-Host "Granting privileges..."
psql -U $PgUser -h $PgHost -p $PgPort -c "GRANT ALL PRIVILEGES ON DATABASE renewable_energy_ai TO reai_user;"

Write-Host "Database setup complete."
Write-Host "Now run: .\venv\Scripts\alembic upgrade head"
