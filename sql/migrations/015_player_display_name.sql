ALTER TABLE dim_player
    ADD COLUMN IF NOT EXISTS display_name text,
    ADD COLUMN IF NOT EXISTS display_name_source text;
