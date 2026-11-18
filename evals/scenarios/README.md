# Scenarios

One JSON file per scenario (S1a, S1b, S2 to S15 and S17 to S22; 22 files). Each has:

- `question`: what the PM types.
- `generate`: how the mock data, mock API behaviour and mock repositories are built.
- `expected`: the answer, written before any generator or agent code existed.

`expected.lock.json` holds a hash of every `expected` block. A test fails if an expected answer changes without the lock being regenerated on purpose
(`python3 evals/lock_expected.py`). If an expected answer is changed after results exist, say so in CHANGELOG.md and in the evals README.

One real-model baseline over these 22 scenarios is published (129 of 154 checks; see [docs/EVALUATION_RESULTS.md](../../docs/EVALUATION_RESULTS.md) and [evals/published/](../published/README.md)). The scoring rule for required phrases was revised after the first round, and the expected answer of S12 was re-locked; both are disclosed there.

All values are invented: names, numbers, error codes and timestamps. Any failure wording marked `(mock wording)`, or described as a mock or placeholder in `notes`, is invented and not taken from any real provider.
