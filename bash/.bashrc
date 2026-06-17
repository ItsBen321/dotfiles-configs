#
# ~/.bashrc
#
eval "$(starship init bash)"

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
alias ff='fzf'
PS1='[\u@\h \W]\$ '

# >>> Codex installer >>>
export PATH="/home/ben/.local/bin:$PATH"
# <<< Codex installer <<<
#
alias home='cd ~'

folder() {
  local dir
  if [[ -z "$1" ]]; then
    dir="$(find . -type d | fzf)" || return 1
  else
    dir="$(find . -type d | fzf --filter="$1" | head -n 1)" || return 1
  fi
  cd "$dir"
}

get() {
  local ext="${1:-}"
  find . -type f -name "*${ext}*" | ff || return 1
}

nget() {
  local ext="${1:-}"
  nvim "$(find . -type f -name "*${ext}*" | ff)" || return 1
}

copy() {
  local src dest
  if [[ "$1" == "-g" ]]; then
    src="$(find ~ | ff --prompt='source >')" || return 1
  else
    src="$(find . -maxdepth 1 | ff --prompt='source >')" || return 1
  fi
  dest="$(find ~ -type d | fzf --prompt='destination >')" || return 1
  cp -r "$src" "$dest"
  echo "copied $src > $dest"
}

move() {
  local src dest
  if [[ "$1" == "-g" ]]; then
    src="$(find ~ | ff --prompt='source >')" || return 1
  else
    src="$(find . -maxdepth 1 | ff --prompt='source >')" || return 1
  fi
  dest="$(find ~ -type d | fzf --prompt='destination >')" || return 1
  mv -r "$src" "$dest"
  echo "moved $src > $dest"
}
