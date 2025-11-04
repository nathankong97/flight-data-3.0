#!/usr/bin/env python
"""CLI wrapper to refresh the flights_commercial view from filtered_airlines.txt."""
import sys

from src.admin.update_flights_commercial_view import main as _main

if __name__ == "__main__":
    # Allow DATABASE_URL to be provided via environment; passthrough to admin main.
    try:
        _main()
    except SystemExit as e:
        # Preserve exit codes/messages for CLI usage
        raise
    except Exception as exc:
        print(f"Error updating flights_commercial view: {exc}", file=sys.stderr)
        sys.exit(1)
