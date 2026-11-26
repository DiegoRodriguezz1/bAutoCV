-- Hojas de vida guardadas como YAML de RenderCV. Idempotente: se puede ejecutar varias veces.
-- La API también la crea al arrancar (create_all); este script es para crearla a mano.
-- Uso: psql "$DATABASE_URL" -f sql/003_saved_cv.sql

CREATE TABLE IF NOT EXISTS "SAVED_CV" (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    yaml_content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
