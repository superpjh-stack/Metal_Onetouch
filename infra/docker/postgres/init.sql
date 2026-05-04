-- ====================================================================
-- Onetouch AI+MES - PostgreSQL Initialization
-- This script runs once on the first container start.
-- It enables TimescaleDB, pgcrypto, and creates baseline schemas.
-- ====================================================================

-- Required extensions ------------------------------------------------
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Logical schemas (Clean Architecture: domain segmentation) ----------
CREATE SCHEMA IF NOT EXISTS auth;          -- users, roles, sessions
CREATE SCHEMA IF NOT EXISTS mes;           -- master data, work orders, BOM
CREATE SCHEMA IF NOT EXISTS sensor;        -- timeseries data (TimescaleDB hypertables)
CREATE SCHEMA IF NOT EXISTS ai;            -- model registry, predictions
CREATE SCHEMA IF NOT EXISTS audit;         -- audit logs

-- Default search path for the app user -------------------------------
ALTER DATABASE onetouch_mes
    SET search_path TO public, mes, auth, sensor, ai, audit;

-- Tuning hints for TimescaleDB (will be respected by Alembic migrations)
-- Hypertables will be created in Alembic migrations once entity models
-- are defined, e.g.:
--   SELECT create_hypertable('sensor.process_metric', 'time');
--   SELECT create_hypertable('sensor.equipment_metric', 'time');

-- Confirm extensions ---------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE 'TimescaleDB version: %', (SELECT extversion FROM pg_extension WHERE extname = 'timescaledb');
    RAISE NOTICE 'pgcrypto version:    %', (SELECT extversion FROM pg_extension WHERE extname = 'pgcrypto');
END $$;
