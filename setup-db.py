#!/usr/bin/env python3
from formie import create_app, models


def main():
    with create_app().app_context():
        models.db.create_all()


if __name__ == "__main__":
    main()
