# Game Architecture Pattern Selection

Use this before adding a new gameplay feature, actor controller, AI system, reusable component, turn/action flow, or broad structure to a Godot project.

## Selection Workflow

1. Read the active project note first. Existing project architecture overrides these defaults.
2. Identify the problem shape before writing code:
   - Mutually exclusive actor modes: read `Architecture/Actor State Machines and State Charts`.
   - NPC, enemy, companion, boss, or agent decisions: read `Architecture/Game AI Behavior Patterns`.
   - Reusable actor capability, content definition, high-volume spawn/despawn, or update ownership: read `Architecture/Gameplay Components Resources and Pools`.
   - Input buffering, turn moves, replay, undo, animation-synchronized actions, or delayed requests: read `Architecture/Commands Event Queues and Turn Flow`.
   - Unclear feature ownership or multiple possible patterns: start with `Architecture/Game Feature Architecture Patterns`.
3. Prefer the smallest structure that makes the next feature clear. Do not introduce a framework just because a pattern exists.
4. Keep Godot's scene/resource model visible: prefer scene-owned nodes, typed child components, custom resources, signals, groups, and specialized engine nodes before script-only systems.
5. State the chosen structure briefly in the implementation notes when the choice affects future work.

## Default Biases

- Use a simple enum/match state machine for a small controller with a few states and little per-state data.
- Use node, resource, or RefCounted state objects when states have their own callbacks, timers, transitions, or data.
- Use hierarchical state machines or state charts when flat FSMs produce duplicated transitions or state explosion.
- Use behavior trees for modular AI task selection and reusable conditions/actions.
- Use utility AI or GOAP only when the design needs contextual scoring or multi-step planning, not just "patrol/chase/attack".
- Use child-node components for reusable runtime capabilities; use custom resources for reusable content data and definitions.
- Use commands/actions and queues when execution must be delayed, replayed, undone, serialized, or synchronized with animation/turn flow.
- Use object pools only when frequent creation/destruction shows up in profiling or is obviously part of the mechanic, such as projectiles, hit sparks, or repeated audio players.

## Vault Notes

- `Architecture/Game Feature Architecture Patterns`: routing guide and decision matrix.
- `Architecture/Actor State Machines and State Charts`: FSM, HFSM, state chart, and AnimationTree ownership.
- `Architecture/Game AI Behavior Patterns`: FSM vs behavior tree vs utility AI vs GOAP.
- `Architecture/Gameplay Components Resources and Pools`: child-node components, custom resources, update ownership, groups, and object pools.
- `Architecture/Commands Event Queues and Turn Flow`: command/action objects, event queues, turn queues, input buffers, replay, and undo.
