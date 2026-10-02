# Wyscout open soccer event dataset

- Access: Figshare collection `10.6084/m9.figshare.c.4415000.v5`.
- License: CC BY 4.0 as returned by Figshare article metadata.
- Files: competitions, teams, players, matches archive, events archive, dictionaries and supporting research artifacts.
- Grain: entity dictionaries, match and event.
- Canonical mapping: percentage-like 0–100 coordinates are retained raw and normalized to 105 × 68 metres; tags survive in qualifiers.
- Known limits: 2017/18 research release, no native xG and no live coverage.
- Current evidence: verified archive MD5 values from Figshare and complete ingestion of the
  five 2017/18 Big Five leagues: 1,826 matches, 3,071,392 accepted canonical events and
  50,584 player-match rows. Three malformed coordinate events were quarantined, and 6 of
  50,590 observed match participants remained explicitly unresolved. Match `2500089` remains
  the small trace example used in low-level regression evidence, not the production scope.

The downloader validates both advertised byte size and MD5 before replacing the target file. Derived xT is project-generated and separately versioned.
