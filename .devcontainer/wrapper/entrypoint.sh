#!/bin/sh
set -e

MUSIC_TOKEN_PATH="/app/rootfs/data/data/com.apple.android.music/files/MUSIC_TOKEN"

if [ ! -f "$MUSIC_TOKEN_PATH" ]; then
  echo "MUSIC_TOKEN not found. Logging in..."
  exec wrapper \
    -L ${USERNAME}:${PASSWORD} \
    -F \
    -H 0.0.0.0 \
    "$@"
else
  echo "MUSIC_TOKEN found. Skipping login."
  exec wrapper \
    -H 0.0.0.0 \
    "$@"
fi
