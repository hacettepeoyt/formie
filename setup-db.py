#!/usr/bin/env python3

import sys

from formie import create_app, models


def main():
    try:
        version: int = int(sys.argv[1])
    except (IndexError, ValueError):
        print(f"USAGE: {sys.argv[0]} <version>")
        print()
        print("Setups or upgrades the database depending on the version argument.")
        print()
        print("0 - full setup")
        print("1 - form access control flags upgrade")
        sys.exit(1)

    if version == 0:
        with create_app().app_context():
            models.db.create_all()
    elif version == 1:
        with create_app().app_context():
            with models.db.engine.begin() as conn:
                conn.execute("ALTER TABLE Form ADD COLUMN access_control_flags INT NOT NULL DEFAULT 0;")
    else:
        print("ERROR: invalid version", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
