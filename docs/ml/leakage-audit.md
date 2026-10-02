# Temporal leakage audit

Audit date: 2026-09-28

## Result

Valuation training is blocked before dataset construction because licensed historical
targets are absent. No model metrics exist to audit, and the application fails closed. This
is preferable to training against current values, scraped values, or synthetic labels.

## Enforced contract

- `feature_as_of` must be on or before `target_date`.
- Features published or corrected after the cutoff are excluded.
- A player's future season, future transfer, and future valuation cannot appear in training
  features for an earlier target.
- Train/validation/test partitions must be chronological, with the final interval untouched
  until model selection is complete.
- Encoders, imputers, scalers, cohort statistics, and feature selection are fit on the
  training interval only.
- Repeated observations for one player cannot cross folds in a way that exposes future
  information.
- Injury, contract, transfer, news, and sentiment inputs use their observed-at time, not
  merely the event date.

Automated tests currently verify that a feature timestamp after the target is rejected and
that missing licensed targets return no prediction. Once targets are procured, this audit
must be rerun against actual feature SQL, split manifests, fitted preprocessing artifacts,
and untouched test predictions before the model status can change from blocked.

