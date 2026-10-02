ALTER TABLE fact_news
    ADD COLUMN IF NOT EXISTS raw_object_uri text,
    ADD COLUMN IF NOT EXISTS content_hash text,
    ADD COLUMN IF NOT EXISTS topics text[] NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS fact_news_claim (
    claim_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    news_id bigint NOT NULL REFERENCES fact_news(news_id) ON DELETE CASCADE,
    player_id bigint REFERENCES dim_player(player_id),
    claim_type text NOT NULL,
    claim_text text NOT NULL,
    claim_status text NOT NULL CHECK (claim_status IN ('REPORTED', 'CONFIRMED', 'CALCULATED')),
    evidence_url text NOT NULL,
    extracted_by_version text,
    data_as_of timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS fact_news_story_cluster_idx ON fact_news (story_cluster_id, published_at);
