# GDScript Style

Use these defaults unless a more specific project note or repository rule overrides them.

## General

- Target Godot 4.x unless the project says otherwise.
- Prefer typed GDScript for variables, parameters, return values, and callbacks.
- Prefer explicit node casts or typed `@onready` variables when node type matters.
- Keep scripts readable and modular. Avoid clever, dense, or hyper-optimized code.
- Prefer composition over inheritance when either approach is reasonable.
- Treat each script as a small piece of a larger architecture.

## Naming

- Classes and custom resources: `PascalCase`.
- Functions, variables, node references, and signal names: `snake_case`.
- Constants and enum members: `CONSTANT_CASE`.
- Private helpers and private state: `_leading_underscore`.
- Signals should describe completed events when possible, such as `spin_finished`.

## Structure

- Keep exports, constants, signals, member variables, and lifecycle methods organized consistently with the surrounding code.
- Avoid giant nested blocks. Extract focused helpers when it improves scanning.
- Do not add comments that merely restate code. Use comments for non-obvious Godot lifecycle, scene, signal, or resource reasoning.

## Architecture

- Preserve scene ownership and node boundaries.
- Avoid using autoloads as dumping grounds.
- Prefer resources for reusable data/configuration when the project already uses that pattern.
- Prefer signals for decoupled event flow when direct ownership would create brittle coupling.
