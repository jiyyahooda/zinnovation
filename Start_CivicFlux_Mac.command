#!/bin/zsh
cd "${0:A:h}" || exit 1
exec ./.venv/bin/python run_mac_app.py
