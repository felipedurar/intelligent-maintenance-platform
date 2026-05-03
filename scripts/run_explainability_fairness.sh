#!/usr/bin/env sh
set -eu

python -m evaluation.explainability_fairness "$@"
