"""Enables ``python -m reconciler ...`` as the CLI entry point."""
from reconciler.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
