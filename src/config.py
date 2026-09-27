"""
src/config.py
==============
Centralised, config-driven path resolution.

Instead of hardcoding DATA_DIR inside every notebook (which forces an
evaluator to edit source before they can run the project), this module
resolves it once, in priority order:

  1. An OLIST_DATA_DIR environment variable, if set.
  2. A `data_dir:` key in config.yaml at the project root.
  3. A sensible local default (./02_Data/01_Raw), for convenience during
     day-to-day development.

Relative paths (env var or config.yaml) are resolved against PROJECT_ROOT,
not the current working directory -- notebooks are usually run from
03_Notebooks/, so resolving against cwd would silently look in the wrong
place (03_Notebooks/02_Data/01_Raw instead of 02_Data/01_Raw).

Usage in a notebook:

    import sys
    sys.path.append("..")  # if notebooks/ sits one level below project root
    from src.config import get_data_dir

    DATA_DIR = get_data_dir()
"""

import os
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
DEFAULT_DATA_DIR = PROJECT_ROOT / "02_Data" / "01_Raw"


def _resolve_against_root(value: str) -> Path:
    """Resolve a path string against PROJECT_ROOT if it's relative, so the
    result doesn't depend on the caller's current working directory."""
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p.resolve()


def get_data_dir(config_path: Path | str | None = None) -> Path:
    """
    Resolve the directory containing the nine raw Olist CSVs.

    Priority: OLIST_DATA_DIR env var > config.yaml `data_dir` key >
    default local path. Raises a clear error if the resolved path
    doesn't exist, rather than failing later with a confusing
    file-not-found error deep inside a DuckDB query.
    """
    env_value = os.environ.get("OLIST_DATA_DIR")
    if env_value:
        resolved = _resolve_against_root(env_value)
        source = "OLIST_DATA_DIR environment variable"
    else:
        cfg_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        resolved = None
        if cfg_path.exists() and yaml is not None:
            with open(cfg_path, "r") as f:
                cfg = yaml.safe_load(f) or {}
            data_dir_value = cfg.get("data_dir")
            if data_dir_value:
                resolved = _resolve_against_root(data_dir_value)
                source = f"config.yaml ({cfg_path})"
        if resolved is None:
            resolved = DEFAULT_DATA_DIR.resolve()
            source = "default path (no env var or config.yaml entry found)"

    if not resolved.is_dir():
        raise FileNotFoundError(
            f"Resolved data directory does not exist: {resolved}\n"
            f"(source: {source})\n\n"
            "Fix this by either:\n"
            "  1. Setting the OLIST_DATA_DIR environment variable, e.g.\n"
            "     export OLIST_DATA_DIR=/path/to/olist_csvs\n"
            "  2. Adding a 'data_dir: /path/to/olist_csvs' line to config.yaml\n"
            "  3. Placing the nine Olist CSVs in ./02_Data/01_Raw\n\n"
            "See README.md 'Data provenance' section for the download link."
        )
    return resolved


def get_duckdb_path(config_path: Path | str | None = None) -> Path:
    """Resolve the DuckDB database file path, same priority order as get_data_dir."""
    env_value = os.environ.get("OLIST_DUCKDB_PATH")
    if env_value:
        return _resolve_against_root(env_value)

    cfg_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if cfg_path.exists() and yaml is not None:
        with open(cfg_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
        duckdb_value = cfg.get("duckdb_path")
        if duckdb_value:
            return _resolve_against_root(duckdb_value)

    return (PROJECT_ROOT / "04_DuckDB" / "olist_capstone.duckdb").resolve()


if __name__ == "__main__":
    # Quick manual check: python -m src.config
    print("Resolved data dir:  ", get_data_dir())
    print("Resolved duckdb path:", get_duckdb_path())