#!/usr/bin/env bash
# Owner: Dev 1. Kept for old habits; the logic is in scripts/dev.py.
cd "$(dirname "$0")/.." && exec "$(command -v python3 || command -v python)" scripts/dev.py verify
