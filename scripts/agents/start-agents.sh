#!/usr/bin/env bash
#
# Bring up orchestrator / implementer / codex side by side in one tmux session.
#
#   ┌──────────────┬──────────────┐
#   │              │ implementer  │  Claude Code, does the implementation
#   │ orchestrator ├──────────────┤
#   │              │ codex        │  Codex CLI, design review and second opinions
#   └──────────────┴──────────────┘
#     Claude Code, runs the show
#
# orchestrator and implementer talk through Claude Code's own cross-session
# messaging (ListAgents / SendMessage); the name given to --name is the address.
# Codex has no such channel, so ask-agent.sh pastes into its pane over tmux.
#
# The container is the sandbox, so every approval check is off by default. Set
# CLAUDE_ARGS / CODEX_ARGS explicitly before running this anywhere that is not
# isolated.
#
# .vscode/tasks.json runs this on folderOpen, so a broken agent setup must still
# leave a usable terminal behind: every failure path falls back to a login shell.
#
# Environment:
#   AGENTS_TMUX         set to 0 to skip tmux and get a plain shell
#   AGENTS_SESSION      tmux session name                          (default: workspace directory name)
#   CLAUDE_ARGS         claude args for both Claude panes          (default: --dangerously-skip-permissions)
#   CODEX_ARGS          codex args                                 (default: --dangerously-bypass-approvals-and-sandbox)
#   CODEX_MODEL         --model for codex                          (default: none)
#   ORCHESTRATOR_ARGS   extra args for orchestrator only           (default: none)
#   ORCHESTRATOR_MODEL  --model for orchestrator                   (default: none)
#   IMPLEMENTER_ARGS    extra args for implementer only            (default: none)
#   IMPLEMENTER_MODEL   --model for implementer                    (default: none)
#
# CLAUDE_ARGS and CODEX_ARGS are read as ${VAR-default}, so exporting an empty
# string drops the default; only an unset variable gets it.
#
# Arguments:
#   --no-attach   build the session but do not attach (used by postAttachCommand)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPT_DIR/agent-session.sh"
SESSION="$AGENT_SESSION"

CLAUDE_ARGS="${CLAUDE_ARGS---dangerously-skip-permissions}"
CODEX_ARGS="${CODEX_ARGS---dangerously-bypass-approvals-and-sandbox}"
ORCHESTRATOR_ARGS="${ORCHESTRATOR_ARGS:-}"
IMPLEMENTER_ARGS="${IMPLEMENTER_ARGS:-}"
ATTACH=1
[ "${1:-}" = "--no-attach" ] && ATTACH=0

# Drop to a plain shell. This is launched from a task and from terminal
# profiles, so exiting here would close the VS Code terminal outright.
fallback_shell() {
  [ "$ATTACH" -eq 0 ] && exit 0
  exec "${SHELL:-/bin/zsh}" -l
}

[ "${AGENTS_TMUX:-1}" = "0" ] && fallback_shell

for cmd in tmux claude; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    printf '\033[33mwarning:\033[0m %s not found, starting a plain shell instead.\n' "$cmd" >&2
    fallback_shell
  fi
done

# Work continues with orchestrator and implementer alone, so a missing codex
# costs its pane and nothing else.
CODEX_OK=1
if ! command -v codex >/dev/null 2>&1; then
  CODEX_OK=0
  printf '\033[33mwarning:\033[0m codex not found, starting without the codex pane.\n' >&2
fi

# Never nest tmux: if this is called from inside a session, leave it alone.
[ -n "${TMUX:-}" ] && fallback_shell

if ! tmux has-session -t "=$SESSION" 2>/dev/null; then
  # ─── Commands for each pane ──────────────────────────────────────────
  model_flag() { [ -n "${1:-}" ] && printf -- '--model %q ' "$1"; return 0; }
  # Append <role>.md to the system prompt when it exists; warn and fall back to
  # a bare claude when it does not.
  prompt_flag() {
    local f="$SCRIPT_DIR/$1.md"
    if [ -r "$f" ]; then
      printf -- '--append-system-prompt "$(cat %q)" ' "$f"
    else
      printf '\033[33mwarning:\033[0m %s missing, starting %s as a bare claude.\n' "$f" "$1" >&2
    fi
    return 0
  }

  ORCH_CMD="claude --name orchestrator $(model_flag "${ORCHESTRATOR_MODEL:-}")$(prompt_flag orchestrator)${CLAUDE_ARGS} ${ORCHESTRATOR_ARGS}"
  IMPL_CMD="claude --name implementer $(model_flag "${IMPLEMENTER_MODEL:-}")$(prompt_flag implementer)${CLAUDE_ARGS} ${IMPLEMENTER_ARGS}"
  CODEX_CMD="codex $(model_flag "${CODEX_MODEL:-}")${CODEX_ARGS}"

  # ─── Build the session ───────────────────────────────────────────────
  tmux new-session -d -s "$SESSION" -c "$PWD" -n dev
  tmux split-window -h -t "$SESSION:dev" -c "$PWD"        # right column
  ROLES=(orchestrator implementer)
  if [ "$CODEX_OK" -eq 1 ]; then
    tmux split-window -v -t "$SESSION:dev.1" -c "$PWD"    # split the right column
    ROLES+=(codex)
  fi

  # Keep the role in a pane option: the TUIs rewrite pane_title, so the title is
  # not a reliable way to find a pane. ask-agent.sh routes on this @role.
  i=0
  for role in "${ROLES[@]}"; do
    tmux set-option -p -t "$SESSION:dev.$i" @role "$role"
    tmux select-pane -t "$SESSION:dev.$i" -T "$role"
    i=$((i + 1))
  done

  tmux set-option -t "$SESSION" -g pane-border-status top
  tmux set-option -t "$SESSION" -g pane-border-format ' #{@role} '
  # Deep scrollback so ask-agent.sh can read back a long answer.
  tmux set-option -t "$SESSION" -g history-limit 50000
  tmux set-option -t "$SESSION" -g mouse on

  tmux send-keys -t "$SESSION:dev.0" "$ORCH_CMD" C-m
  tmux send-keys -t "$SESSION:dev.1" "$IMPL_CMD" C-m
  [ "$CODEX_OK" -eq 1 ] && tmux send-keys -t "$SESSION:dev.2" "$CODEX_CMD" C-m

  tmux select-pane -t "$SESSION:dev.0"
fi

[ "$ATTACH" -eq 0 ] && exit 0

exec tmux attach-session -t "=$SESSION"
