"""Canonical paths shared by research tools and the local application."""
import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get('CIVICFLUX_ROOT', Path(__file__).resolve().parent)).expanduser().resolve()
ML_SOURCE = PROJECT_ROOT / 'src' / 'civicflux'
ARTIFACTS = PROJECT_ROOT / 'artifacts'
MODEL_REGISTRY = ARTIFACTS / 'model_validation' / 'v1.0.0' / 'model_registry.json'
DATA = PROJECT_ROOT / 'data'
CONFIG = PROJECT_ROOT / 'config'
BACKEND = PROJECT_ROOT / 'backend'
REPORTS = PROJECT_ROOT / 'reports'
