#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
printf '\nCUE virtual environment is ready. Activate with:\nsource .venv/bin/activate\n'
