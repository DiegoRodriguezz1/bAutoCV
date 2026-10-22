-- Instrumentación del experimento A/B (corte 2). Idempotente: se puede ejecutar varias veces.
-- Uso: psql "$DATABASE_URL" -v app_role=bautocv_app -f sql/002_instrumentation.sql
-- (DATABASE_URL sin el prefijo "+asyncpg"). Si no pasas app_role, se omite el REVOKE.

ALTER TABLE "EXPERIMENT_SESSION"
    ADD COLUMN IF NOT EXISTS section_times JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS ats_breakdown JSONB,
    ADD COLUMN IF NOT EXISTS user_agent TEXT,
    ADD COLUMN IF NOT EXISTS a11y_prefs JSONB;

ALTER TABLE "SKILL"
    ADD COLUMN IF NOT EXISTS normalized_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS removed_at TIMESTAMPTZ;

ALTER TABLE "SURVEY_RESPONSE"
    ADD COLUMN IF NOT EXISTS item SMALLINT CHECK (item BETWEEN 1 AND 4);

ALTER TABLE "APPLICATION_STATUS"
    ADD COLUMN IF NOT EXISTS job_ref TEXT;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'application_status_status_check') THEN
        ALTER TABLE "APPLICATION_STATUS"
            ADD CONSTRAINT application_status_status_check
            CHECK (status IN ('enviada', 'vista', 'entrevista', 'rechazada'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS skill_session_active_idx ON "SKILL" (session_id) WHERE removed_at IS NULL;
CREATE INDEX IF NOT EXISTS event_log_type_idx ON "EVENT_LOG" (event_type);

-- EVENT_LOG es solo inserción: cualquier UPDATE o DELETE lanza un error.
CREATE OR REPLACE FUNCTION event_log_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'EVENT_LOG es de solo inserción (% no permitido)', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS event_log_no_update_delete ON "EVENT_LOG";
CREATE TRIGGER event_log_no_update_delete
    BEFORE UPDATE OR DELETE ON "EVENT_LOG"
    FOR EACH ROW EXECUTE FUNCTION event_log_immutable();

-- Además se le quita el permiso al rol con el que se conecta la API.
\if :{?app_role}
REVOKE UPDATE, DELETE, TRUNCATE ON "EVENT_LOG" FROM :"app_role";
\endif
