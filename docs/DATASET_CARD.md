# Dele-bench dataset card (v0.1)

## Status

**Spec + seed corpus.** Tasks, private references, one organization fixture, and pristine world
seeds are present. Runnable mock environments, policy engine, and graders are **not** shipped in
v0.1.

## What is included

| Asset | Count | Notes |
|---|---:|---|
| Public tasks | 18 | Goal-only instructions, opaque fixture ids |
| Private references | 18 | Capability routes, state predicates, handoffs |
| Organizations | 1 | `product-company-v1` |
| World fixtures | 18 | Pristine seeds that fail positive assertions |
| Schemas | 5 | organization, task, reference, event, world |

## Tracks

- `workflow` — stateful operational work
- `approval` — policy-gated restraint outcomes
- `mixed` — state + decision + staged external effects
- `resilience` — capacity, recovery, and duplicate-work traps

## Predicate semantics

| Op | Meaning |
|---|---|
| `exists` / `absent` | Path present or missing in exported world |
| `eq` / `neq` | Exact scalar match |
| `contains` | String or collection membership |
| `lt` / `lte` / `gt` / `gte` | Numeric comparison |
| `count` | Cardinality of a collection at `path` |

## Validation gates (structural)

`python3 validate.py` checks:

- task/reference parity
- no private-key leakage in public tasks
- capabilities exist in the organization
- at least two participating roles per task
- routable gold handoffs
- handoff capabilities ⊆ required capabilities
- policy citations resolve
- world fixture files exist

## Not yet validated

- pristine-fail against a live grader
- oracle pass on a reference adapter
- all-tools / dump-to-executive / do-it-myself / always-handoff baselines
- executable policy engine
- second non-product organization

## License

MIT. See `LICENSE`.
