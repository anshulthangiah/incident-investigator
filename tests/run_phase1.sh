#!/usr/bin/env bash
# Run the Phase 1 tests from the project root.
set -u
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -t . -v 2>&1
