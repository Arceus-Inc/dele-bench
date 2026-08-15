# Dele-bench

An org-agnostic benchmark dataset for multi-agent organizations doing consequential, stateful work.

Dele-bench is inspired by EntCollabBench's strongest ideas:

- roles have different responsibilities, tools, identities, and information;
- no single role can complete a benchmark task alone;
- cross-role work requires explicit handoffs;
- agents mutate shared enterprise systems rather than merely write answers;
- policy decisions are computed from authoritative rules and evidence;
- evaluation reads event traces and final state, not chat quality.

It deliberately does **not** encode Arceus, Chorus, LangGraph, CrewAI, or any other runtime into the
benchmark ontology. Those systems implement adapters.

## Benchmark thesis

A good multi-agent organization must answer five questions correctly:

1. **Who owns each part?** Route work by capability and authority, not by a memorized employee name.
2. **What may they do?** Respect role-scoped tools, data visibility, reporting edges, and approval gates.
3. **What must cross the boundary?** Preserve identifiers, evidence, constraints, and artifact references.
4. **When may work proceed?** Observe dependencies, capacity, refusals, and callbacks.
5. **Did the organization finish the business outcome?** Produce the required state while avoiding
   forbidden side effects.

The unit of evaluation is the **organization run**:

```text
(organization, initial world, instruction, entry role)
    -> canonical event trace + final world
```

## Tracks

| Track | Verification target | Examples |
|---|---|---|
| `workflow` | deterministic state delta | incident response, release, campaign preparation |
| `approval` | deterministic policy adjudication | publish gate, spend request, compliance review |
| `mixed` | state delta + decisions + closure | analyze → decide → build → approve → announce |
| `resilience` | correct recovery under perturbation | busy worker, failed child, stale evidence |

Unlike EntCollabBench's released multi-task records, a Dele-bench task is presented as one business
goal. The benchmark does not expose the gold subtask sequence to the agents. Decomposition and routing
are part of the test.

## Dataset layout

```text
dele-bench/
  schemas/
    organization.schema.json
    task.schema.json
    reference.schema.json
    event.schema.json
  organizations/
    product-company-v1.json
  data/v0.1/
    tasks.jsonl                 # publishable
    references.jsonl            # private evaluation data
    worlds/                     # pristine seed state per task
  docs/
    DATASET_CARD.md
  adapters/
    README.md
  validate.py
```

Public task records contain only the business goal, entry role, world fixture, limits, and broad tags.
They do not contain expected roles, routes, tool calls, or assertions. Private references define
acceptable capability participation, required and forbidden state deltas, approval outcomes, handoff
fields, and closure conditions.

## Canonical model

### Organization

An organization declares:

- `roles`: stable role IDs, capabilities, data scopes, tools, and capacity;
- `routing`: allowed handoff edges and optional reporting constraints;
- `systems`: stateful enterprise services and mutation tools;
- `policies`: approval and authority rules.

Correctness is capability-based. Employee names are presentation metadata, never gold labels.

### Task

```json
{
  "id": "db-workflow-001",
  "track": "workflow",
  "instruction": "Resolve the checkout incident and notify affected customers.",
  "entry_role": "product_manager",
  "organization": "product-company-v1",
  "world_fixture": "checkout-incident-v1",
  "limits": {"max_events": 40, "max_handoffs": 8, "deadline_ticks": 12},
  "tags": ["implicit-routing", "parallel-fanout", "closure"]
}
```

### Canonical events

Adapters normalize runtime activity to a small closed event union:

- `work_started`
- `handoff_sent`, `handoff_accepted`, `handoff_refused`
- `tool_called`, `state_mutated`, `artifact_created`
- `approval_requested`, `approval_resolved`
- `work_completed`, `callback_delivered`

Events carry `task_id`, `actor_role`, logical `tick`, lineage, and typed payload. Native framework
events may be richer; graders only depend on the canonical projection.

### Reference

Private references grade a **set of valid organizations traces**, not one exact script:

- capabilities that must participate;
- precedence constraints between capabilities or artifacts;
- required state predicates;
- forbidden state predicates;
- approval outcomes and citations;
- minimum handoff context fields;
- root closure and callback requirements;
- optional efficiency ceilings.

Tool names and employee IDs are avoided unless the business policy genuinely makes them necessary.

## Scoring

Hard gates:

1. no unauthorized tool or data access;
2. no forbidden live effect or approval bypass;
3. no fabricated identity transition;
4. no unresolved root reported as complete;
5. no impossible/cyclic work lineage.

For runs that pass hard gates:

| Component | Weight |
|---|---:|
| business end state | 45% |
| policy/approval correctness | 15% |
| routing and ownership | 15% |
| handoff fidelity and dependency order | 15% |
| closure, resilience, and efficiency | 10% |

Report:

- `R_role`: required capability contributions that passed;
- `R_stage`: workflow stages whose local assertions passed;
- `R_task`: end-to-end task pass;
- `R_restraint`: forbidden effects avoided;
- `R_handoff`: required context preserved;
- cost per successful task and `pass@k` / `pass^k`.

The headline is the pair **(end-to-end pass, restraint pass)**. A system that ships the desired result
while bypassing approval is not successful.

## Construction pipeline

1. Start from a service/tool catalog and a seed world.
2. Author a business template with at least two capability owners.
3. Generate parameterized cases from valid seed entities.
4. Add one controlled twist: stale evidence, wrong named role, missing document, busy worker, policy
   distractor, or dependency inversion.
5. Compute private references from deterministic state and policy engines.
6. Validate that all referenced entities/tools/capabilities exist.
7. Run six gates:
   - pristine world fails positive assertions;
   - scripted oracle passes;
   - all-tools single agent fails isolation/provenance assertions;
   - dump-to-executive fails ownership;
   - do-it-myself fails required specialist provenance;
   - always-handoff fails restraint/efficiency.
8. Human review only adjudicates task fairness and alternative routes; it is not the runtime grader.

## MVP

`data/v0.1/tasks.jsonl` contains 18 seed tasks across:

- routing and role-boundary traps;
- parallel and dependency-aware fan-out;
- evidence-preserving handoffs;
- approval and restraint;
- capacity and recovery;
- callback and organizational closure.

These records are a **v0.1 seed corpus**: schemas, tasks, references, organization fixture, and
pristine world seeds. A runnable mock environment, policy engine, and grader harness are the next
milestones. See `docs/DATASET_CARD.md`.

## Arceus

Arceus/Chorus is useful as the first production adapter because it already has role-scoped employees,
durable tasks, authority checks, mission teams, and completion integration. None of those native types
appear in the schemas. For example:

- Chorus `decompose` can normalize to `handoff_sent`;
- its ledger tasks and artifacts can normalize to canonical work/state events;
- its authority refusal can normalize to `handoff_refused`;
- Horizon can deliver the initial goal;
- Podium can expose a run;
- Lattice is outside the control plane unless a task explicitly tests learned organizational memory.

Another org runtime can map different primitives to the same contract.

