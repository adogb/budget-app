"""Category rules that the API can refuse a request for."""


class CategoryError(Exception):
    """The change would break a rule, e.g. a duplicate name or a second income
    group (spec §1, plan 03 C3 and C4)."""


class CategoryNotFoundError(Exception):
    """No category group or category has that id."""
