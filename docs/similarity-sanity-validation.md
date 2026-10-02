# Similarity football sanity validation

Validation date: 2026-09-29. This is an engineering/football plausibility sample, not an
independent expert endorsement or proof that one feature set captures every recruitment role.

The live API was queried after the final StatsBomb replay, full-season ingestion and dbt
build. One 900-plus-minute target was selected from each broad position group. Every returned
candidate was from the same competition, season and broad position group as the target, had
at least 900 minutes, and was compared on all eight published event features.

| Target | Group | Five highest-ranked peers |
|---|---|---|
| Wes Morgan | DF | Sebastian Prödl (98.31), Joleon Lescott (97.11), Robert Huth (96.85), Gary Cahill (94.92), John Terry (94.73) |
| Rubén Castro Martín | FW | Cédric Bakambu (97.29), Borja González Tomás (97.20), Imanol Agirretxe Arruti (97.19), Charles Días Barbosa de Oliveira (96.91), Kevin Gameiro (93.09) |
| Kasper Schmeichel | GK | Petr Čech (99.61), Hugo Lloris (99.18), Costel Fane Pantilimon (98.71), Rob Elliot (98.30), Jack Butland (97.79) |
| Andrew Surman | MD | Glenn Whelan (90.73), Graham Dorrans (89.55), Michael Carrick (87.13), John Obi Mikel (85.73), Leon Britton (83.16) |

The samples are positionally and stylistically plausible for the deliberately broad v2
population: centre-back peers for Morgan, same-league starting goalkeepers for Schmeichel,
La Liga forwards for Castro, and possession/holding midfielders for Surman. Scores are
descriptive percentile similarity, not transfer recommendations, causal quality estimates or
guarantees of tactical fit. The API exposes the population, minutes, feature count, per-feature
differences, version and confidence so a scout can challenge the ranking.

Known limits remain visible: goalkeeper similarity currently uses the same eight generic
event metrics because the open sources do not provide a validated specialist goalkeeper
feature set across all populated seasons. Role-specific weights and richer physical,
contract, injury and current-season context require authorized data and human review.
