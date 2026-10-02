-- Supports player spatial summaries and canonical player event trace queries.
CREATE INDEX IF NOT EXISTS fact_event_player_spatial_idx
    ON fact_event (player_id)
    INCLUDE (normalized_x_m, normalized_y_m, data_as_of)
    WHERE player_id IS NOT NULL;
