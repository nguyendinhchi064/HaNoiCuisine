CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enum used by models.Place.status
DO $$ BEGIN
  CREATE TYPE place_status AS ENUM ('pending','approved','rejected');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Add missing columns (safe if some already exist)
ALTER TABLE places
  ADD COLUMN IF NOT EXISTS slug           text,
  ADD COLUMN IF NOT EXISTS is_public      boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS status         place_status NOT NULL DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS share_token    text,
  ADD COLUMN IF NOT EXISTS published_at   timestamptz,
  ADD COLUMN IF NOT EXISTS created_by     bigint,
  ADD COLUMN IF NOT EXISTS updated_by     bigint,
  ADD COLUMN IF NOT EXISTS created_at     timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS updated_at     timestamptz NOT NULL DEFAULT now();

-- FKs to users (ignore if already exist)
DO $$ BEGIN
  ALTER TABLE places
    ADD CONSTRAINT fk_places_created_by_users FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE places
    ADD CONSTRAINT fk_places_updated_by_users FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Helpful indexes (no-ops if already exist)
CREATE UNIQUE INDEX IF NOT EXISTS uq_places_slug         ON places (slug);
CREATE INDEX IF NOT EXISTS idx_places_geom               ON places USING gist (geom);
CREATE INDEX IF NOT EXISTS idx_places_name_trgm          ON places USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_places_addr_trgm          ON places USING gin (address gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_places_status             ON places (status);
CREATE INDEX IF NOT EXISTS idx_places_is_public          ON places (is_public);
