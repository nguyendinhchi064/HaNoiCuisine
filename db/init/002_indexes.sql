CREATE INDEX IF NOT EXISTS idx_places_geom ON places USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_places_name_trgm ON places USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_places_addr_trgm ON places USING GIN (address gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_places_status ON places USING BTREE (status);
CREATE INDEX IF NOT EXISTS idx_places_is_public ON places USING BTREE (is_public);
DROP TABLE IF EXISTS places CASCADE;