#!/bin/sh
set -e

# The codex-cli feature's postCreateCommand ends by deleting its own setup.sh, but
# /usr/local/codex-cli is root-owned while lifecycle commands run as remoteUser.
# The rm fails, the feature's postCreate exits 1, and the devcontainer CLI then skips
# every user-provided command after it -- including .devcontainer/postCreateCommand.sh.
# onCreateCommand runs before any feature postCreate, so hand the directory over here.
if [ -d /usr/local/codex-cli ]; then
  sudo chown -R $(whoami):$(whoami) /usr/local/codex-cli
fi