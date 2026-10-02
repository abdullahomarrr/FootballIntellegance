CREATE TABLE IF NOT EXISTS recruitment_role (
    role_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE,
    positions text[] NOT NULL,
    feature_weights jsonb NOT NULL,
    hard_constraints jsonb NOT NULL DEFAULT '{}'::jsonb,
    feature_set_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS shortlist (
    shortlist_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL,
    role_id bigint REFERENCES recruitment_role(role_id),
    status text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ARCHIVED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS shortlist_player (
    shortlist_id bigint NOT NULL REFERENCES shortlist(shortlist_id) ON DELETE CASCADE,
    player_id bigint NOT NULL REFERENCES dim_player(player_id),
    rank smallint,
    stage text NOT NULL DEFAULT 'IDENTIFIED',
    rationale text,
    added_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (shortlist_id, player_id)
);
