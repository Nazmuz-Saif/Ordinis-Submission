from analytics import services

ORDER = 85   # after tasks (40), attendance (50) and billing (80): it reads their numbers


def seed(ctx):
    """Today's health snapshot of the demo company. Running it again refreshes the same row."""
    _snapshot, created = services.take_snapshot(ctx.company, ctx.today)
    ctx.note('health snapshots', created)
