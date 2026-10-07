from decimal import Decimal


def gross_amount(structure):
    """Base salary plus all allowances."""
    return structure.base_salary + sum((Decimal(str(v)) for v in structure.allowances.values()), Decimal('0'))
