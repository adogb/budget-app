"""Load the starter category tree from `app/categories/starter.json`.

On an empty database:

    uv run python -m scripts.seed_categories

To clear the tree and load it again:

    uv run python -m scripts.seed_categories --replace
"""

import argparse

from app.categories.errors import CategoryError
from app.categories.seed import apply_starter_tree
from app.db import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="delete the existing groups and categories first",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        try:
            groups, categories = apply_starter_tree(db, replace=args.replace)
        except CategoryError as error:
            raise SystemExit(f"{error}") from error

    print(f"Added {groups} groups and {categories} categories.")


if __name__ == "__main__":
    main()
