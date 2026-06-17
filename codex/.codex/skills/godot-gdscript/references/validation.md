# Godot Validation

Choose validation based on the project and task. Do not invent a passing state: run commands when possible and report any blocker.

## Find Godot

Common executable names:

```powershell
Get-Command godot, godot4, godot-mono -ErrorAction SilentlyContinue
```

If the project documents a specific Godot binary, use that.

## Useful Godot CLI Patterns

Run the project headlessly when possible:

```powershell
godot --headless --path "C:\path\to\project" --quit-after 1
```

Open/import project resources in CI-style workflows:

```powershell
godot --headless --path "C:\path\to\project" --import
```

Parse a command-line script:

```powershell
godot --headless --path "C:\path\to\project" --check-only --script "res://path/to/script.gd"
```

Run a specific scene when the task is scene-specific:

```powershell
godot --headless --path "C:\path\to\project" --scene "res://path/to/scene.tscn" --quit-after 1
```

## Linters And Formatters

If installed and used by the project, prefer the project-pinned tool. Common options include:

- GDQuest `gdscript-formatter` for Godot 4 formatting and linting.
- `gdformat` and `gdlint` from Godot GDScript Toolkit, if the project already uses them.

Do not apply repo-wide formatting unless the task asks for it.

## Tests

Use the project's existing framework and commands. Common Godot test frameworks include GdUnit4 and GUT.

For behavior changes, prefer the narrowest relevant test or scene smoke test first, then broader checks if the change touches shared systems.
