# Jev launcher

The CLI is developed in its own Git repository at `~/projects/jev`.
This Stow package only installs its launcher at `~/.local/bin/jev`.

```sh
cd ~/dotfiles-configs
stow --target="$HOME" jev
jev
```

On another machine, clone the CLI repository to `~/projects/jev` first.
Set `JEV_SOURCE_DIR` if you use a different checkout location. Python 3.10+
is required. Add `~/.local/bin` to your shell's PATH if it is not already there.

Credentials are configured per machine with `jev` and kept outside dotfiles.
See the CLI repository's README for examples, storage options, agent usage,
and benchmark measurements.
