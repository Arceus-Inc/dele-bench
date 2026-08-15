# Runtime adapter contract

The benchmark owns tasks, organization semantics, canonical events, and grading. A runtime adapter owns
execution.

```python
class OrganizationAdapter(Protocol):
    def load_organization(self, organization: dict) -> None: ...
    def seed_world(self, fixture_id: str) -> None: ...
    def deliver(self, *, task_id: str, entry_role: str, instruction: str) -> None: ...
    def run_until_quiescent(self, *, deadline_ticks: int) -> None: ...
    def export_events(self) -> list[dict]: ...
    def export_world(self) -> dict: ...
    def reset(self) -> None: ...
```

## Conformance requirements

1. **Role isolation is enforced twice**: tool visibility and server-side identity authorization.
2. Every state-changing action produces a canonical `tool_called` and/or `state_mutated` event.
3. Every cross-role request produces `handoff_sent`; acceptance/refusal is explicit.
4. Handoffs expose structured context and artifact references to the grader.
5. Child completion returns to its parent through `callback_delivered`.
6. Logical ticks, event IDs, and work lineage are stable enough for deterministic replay.
7. `export_world()` returns business state, not an agent-authored summary.
8. `reset()` produces an isolated pristine world for the next task.

## Mapping guidance

Do not synthesize success events from natural-language messages. Emit events only when the runtime has
durably accepted or executed the corresponding operation.

| Canonical event | Minimum payload |
|---|---|
| `handoff_sent` | target role, kind, intent, context, artifact refs |
| `handoff_refused` | target role, reason |
| `tool_called` | system, tool, structured arguments |
| `state_mutated` | system, entity identity, semantic delta |
| `approval_resolved` | decision, rule citations, required docs |
| `work_completed` | work identity, outcome refs |
| `callback_delivered` | parent work identity, child outcome refs |

## Arceus/Chorus example

This is one mapping, not benchmark law:

| Native concept | Canonical projection |
|---|---|
| Horizon goal submission | initial `work_started` |
| Chorus delegated root | root work identity |
| Chorus `decompose` child | `handoff_sent` |
| authority denial | `handoff_refused` |
| child task terminal state | `work_completed` |
| integration wake/packet | `callback_delivered` |
| role artifacts and ledger projections | `artifact_created` / exported world |

Framework-specific properties—management profiles, mission teams, depth-cap error strings, Podium run
modes—may be retained in an optional `native` event envelope. Private references must not depend on
them.

## EntCollab-style peer service example

| Native concept | Canonical projection |
|---|---|
| `ask_<role>_by_http` | `handoff_sent` |
| downstream HTTP acceptance | `handoff_accepted` |
| MCP call | `tool_called` |
| database diff | `state_mutated` |
| downstream response | `work_completed` + `callback_delivered` |

## Contract tests

An adapter is accepted only if it passes:

- unauthorized tool invocation is rejected server-side;
- a legal two-role handoff preserves typed context;
- a refused handoff creates no business-state mutation;
- child completion is observable by the parent;
- two runs of one fixture do not share state;
- exported canonical events validate against `schemas/event.schema.json`.

