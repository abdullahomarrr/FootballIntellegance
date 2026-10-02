"""Group provider identities that are the same person, for profile display only.

Rule: an identical normalised full name of two or more words, held by exactly one StatsBomb
and exactly one Wyscout identity. The basis records whether the two also share a club. Facts are
never merged, so minutes and events are not double counted.
"""

from __future__ import annotations

from typing import Any

BUILD_SQL = """
WITH members AS (
    SELECT p.player_id, p.normalized_name, bridge.provider
    FROM dim_player p
    JOIN bridge_player_provider bridge
      ON bridge.player_id = p.player_id AND bridge.valid_to IS NULL
    WHERE array_length(string_to_array(p.normalized_name, ' '), 1) >= 2
), name_groups AS (
    SELECT normalized_name,
           min(player_id) FILTER (WHERE provider = 'statsbomb_open') AS statsbomb_id,
           min(player_id) FILTER (WHERE provider = 'wyscout_open') AS wyscout_id
    FROM members
    GROUP BY normalized_name
    HAVING count(*) FILTER (WHERE provider = 'statsbomb_open') = 1
       AND count(*) FILTER (WHERE provider = 'wyscout_open') = 1
       AND count(*) = 2
), tm_members AS (
    SELECT link.tm_player_id, link.player_id, bridge.provider
    FROM bridge_player_transfermarkt link
    JOIN bridge_player_provider bridge
      ON bridge.player_id = link.player_id AND bridge.valid_to IS NULL
    WHERE link.match_basis IN ('ID_CROSSWALK', 'NAME_AND_BIRTH_DATE', 'NAME_AND_NATIONALITY')
), tm_groups AS (
    SELECT tm_player_id,
           min(player_id) FILTER (WHERE provider = 'statsbomb_open') AS statsbomb_id,
           min(player_id) FILTER (WHERE provider = 'wyscout_open') AS wyscout_id
    FROM tm_members
    GROUP BY tm_player_id
    HAVING count(*) FILTER (WHERE provider = 'statsbomb_open') = 1
       AND count(*) FILTER (WHERE provider = 'wyscout_open') = 1
       AND count(*) = 2
), pairs AS (
    SELECT statsbomb_id, wyscout_id, 'FULL_NAME' AS basis FROM name_groups
    UNION
    SELECT statsbomb_id, wyscout_id, 'SHARED_TRANSFERMARKT_ID' AS basis FROM tm_groups
), collapsed AS (
    SELECT DISTINCT ON (statsbomb_id, wyscout_id) statsbomb_id, wyscout_id, basis FROM pairs
    ORDER BY statsbomb_id, wyscout_id, (basis = 'FULL_NAME') DESC
), unique_pairs AS (
    -- a record claimed by more than one counterpart is ambiguous and is never grouped
    SELECT statsbomb_id, wyscout_id, basis FROM (
        SELECT collapsed.*,
               count(*) OVER (PARTITION BY statsbomb_id) AS sb_claims,
               count(*) OVER (PARTITION BY wyscout_id) AS wy_claims
        FROM collapsed
    ) counted
    WHERE sb_claims = 1 AND wy_claims = 1
), teams AS (
    SELECT DISTINCT player_id, team_id FROM fact_player_match WHERE team_id IS NOT NULL
), evidence AS (
    SELECT g.statsbomb_id, g.wyscout_id, g.basis,
           EXISTS (
               SELECT 1 FROM teams a JOIN teams b ON a.team_id = b.team_id
               WHERE a.player_id = g.statsbomb_id AND b.player_id = g.wyscout_id
           ) AS shares_club
    FROM unique_pairs g
)
SELECT least(statsbomb_id, wyscout_id) AS person_id, player_id,
       CASE WHEN basis = 'SHARED_TRANSFERMARKT_ID' THEN 'SHARED_TRANSFERMARKT_ID'
            WHEN shares_club THEN 'FULL_NAME_AND_CLUB' ELSE 'FULL_NAME' END AS link_basis
FROM evidence
CROSS JOIN LATERAL (VALUES (statsbomb_id), (wyscout_id)) AS member(player_id)
"""


def rebuild_person_groups(connection: Any) -> int:
    """Replace the whole mapping; it is a deterministic function of the identity tables."""
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM player_person")
        cursor.execute(
            f"INSERT INTO player_person (person_id, player_id, link_basis) {BUILD_SQL}"
        )
        count = int(cursor.rowcount)
    connection.commit()
    return count
