CREATE TABLE IF NOT EXISTS fact_transfer (
    transfer_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id bigint REFERENCES dim_player(player_id),
    provider text NOT NULL,
    provider_transfer_id text NOT NULL,
    transfer_date date,
    from_team_id bigint REFERENCES dim_team(team_id),
    to_team_id bigint REFERENCES dim_team(team_id),
    transfer_status text NOT NULL,
    fee_amount numeric,
    fee_currency char(3),
    fee_disclosed boolean,
    raw_fee_text text,
    data_as_of timestamptz NOT NULL,
    provenance_raw_object_uri text NOT NULL,
    UNIQUE (provider, provider_transfer_id)
);

CREATE TABLE IF NOT EXISTS fact_player_market_value (
    market_value_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id bigint NOT NULL REFERENCES dim_player(player_id),
    provider text NOT NULL,
    valuation_date date NOT NULL,
    amount numeric NOT NULL CHECK (amount >= 0),
    currency char(3) NOT NULL,
    valuation_type text NOT NULL,
    data_as_of timestamptz NOT NULL,
    provenance_raw_object_uri text NOT NULL,
    UNIQUE (player_id, provider, valuation_date, valuation_type)
);

CREATE TABLE IF NOT EXISTS fact_news (
    news_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider text NOT NULL,
    provider_article_id text NOT NULL,
    canonical_url text NOT NULL,
    title text NOT NULL,
    permitted_snippet text,
    publisher text,
    published_at timestamptz,
    language text,
    story_cluster_id text,
    data_as_of timestamptz NOT NULL,
    UNIQUE (provider, provider_article_id)
);

CREATE TABLE IF NOT EXISTS bridge_news_player (
    news_id bigint NOT NULL REFERENCES fact_news(news_id),
    player_id bigint NOT NULL REFERENCES dim_player(player_id),
    confidence numeric(5,4) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    match_method text NOT NULL,
    PRIMARY KEY (news_id, player_id)
);

CREATE TABLE IF NOT EXISTS fact_social_aggregate (
    social_aggregate_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    platform text NOT NULL,
    player_id bigint NOT NULL REFERENCES dim_player(player_id),
    aggregate_date date NOT NULL,
    topic text NOT NULL,
    mention_count integer NOT NULL CHECK (mention_count >= 0),
    sentiment_mean numeric CHECK (sentiment_mean BETWEEN -1 AND 1),
    model_version text,
    data_as_of timestamptz NOT NULL,
    UNIQUE (platform, player_id, aggregate_date, topic)
);

CREATE TABLE IF NOT EXISTS pipeline_run (
    pipeline_run_id text PRIMARY KEY,
    job_name text NOT NULL,
    provider text,
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    status text NOT NULL CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED', 'PARTIAL')),
    rows_read bigint NOT NULL DEFAULT 0,
    rows_written bigint NOT NULL DEFAULT 0,
    rows_quarantined bigint NOT NULL DEFAULT 0,
    quota_used bigint,
    error_summary text,
    commit_sha text
);
