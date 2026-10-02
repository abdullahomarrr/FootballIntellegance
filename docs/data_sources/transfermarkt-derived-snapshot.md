# Transfermarkt-derived public snapshot decision

Decision date: 2026-09-29  
Dataset publisher: `dcaribou/transfermarkt-datasets`

## Update 2026-10-01: approved by the product owner for portfolio use

The product owner approved loading the snapshot as a clearly labelled, frozen, third-party layer
for this non-commercial portfolio project. It is loaded by `load-market-snapshot`, never
scraped, stored as provider `transfermarkt_snapshot`, and linked to players with tiered
confidence (birth date, then name + nationality + position). It does not feed any trained
valuation model or performance score. The original reasoning below still applies to any other use.

## Decision

Do not load this snapshot into the canonical market, transfer, contract or model-training
tables without a product-owner legal review confirming that the intended use is permitted.

The repository applies CC0 to the work it publishes and makes prepared CSV/DuckDB artifacts
publicly downloadable. That is meaningful evidence of the publisher's reuse intent. However,
the CC0 legal text also explicitly says the affirmer does not clear rights held by other
people. The records are derived from Transfermarkt, and this project has not established
that the dataset publisher can waive every underlying contractual or database right. A
repository license alone therefore does not prove the requested downstream use is lawful.

This is a rights-provenance limitation, not a technical limitation. The platform does not
scrape Transfermarkt, evade access controls, or silently treat the snapshot as licensed.

## Technical verification

The three candidate artifacts were downloaded only into the gitignored local audit area so
their schema and integrity could be verified without canonical ingestion:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `player_valuations.csv.gz` | 7,197,935 | `608e32e5ad2231074f3505c469ad727be66d7e6efda6af918afd85379439631d` |
| `players.csv.gz` | 4,389,958 | `d22e407981d5b51a79bf8ff59835729f3526f7dc3495a6d8ed2f852ed2e86403` |
| `transfers.csv.gz` | 5,809,514 | `90326983daf7e6ac7aabdfe62b90936d9bf1dd2171e53dec75c3751eb1620a83` |

The published headers contain point-in-time player valuations, transfers, current club and
contract-expiration fields. The publisher states that updates are paused: valuations stop on
2026-06-12, appearances on 2026-06-28 and games on 2026-07-06; 2026/27 squads are absent.
Even if approved later, the data must be labelled historical/frozen and cannot satisfy a
current-contract claim.

## Consequence for valuation

There are currently no approved historical valuation targets in the canonical warehouse.
Training remains fail-closed because a numerical model without lawful point-in-time targets
would be fabricated confidence. The temporal feature contract, leakage checks and model
interface remain ready for an approved source; no estimate is displayed meanwhile.
