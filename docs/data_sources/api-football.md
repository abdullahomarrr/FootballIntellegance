# API-Football candidate provider

- Access: authenticated API key and paid/free plan subject to current terms.
- Intended role: broad historical statistics, fixtures and live 2026/27 discovery.
- Discovery: `/leagues` season coverage payload; never hardcode provider support.
- Candidate grains: league-season capability, fixture, player-fixture statistics, transfers and injuries.
- Known limits: endpoint presence does not establish field completeness, historical depth, persistence rights or spatial event coverage.
- Current status: adapter and fixture tests are implemented; production calls are disabled without `API_FOOTBALL_KEY`.

Approval requires persisted authenticated discovery, quota/cost estimates, old/recent/live samples, null-rate and minute reconciliation, and accepted storage/derived-use terms.
