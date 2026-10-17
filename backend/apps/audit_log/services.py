import logging
from functools import lru_cache

from django.apps import apps as django_apps

from core import docgen
from .models import AuditLog

logger = logging.getLogger(__name__)

# Models whose saves are not "actions" (the log itself, and notices the system sends by itself).
EXCLUDED_MODELS = {'AuditLog', 'Notification', 'PlatformActionLog'}
# A model whose row IS an action of its own kind: (action, status).
SPECIAL = {'ImpersonationLog': ('read', 'warning')}
SKIP_FIELDS = {'updated_at', 'created_at'}


def our_app_labels():
    return {c.label for c in django_apps.get_app_configs() if c.path.startswith(docgen.APPS_DIR)}


@lru_cache(maxsize=None)
def _company_path(model):
    """Attribute names that lead from a record to its Company: ('company',) or ('task', 'company')... None if none."""
    from tenants.models import Company
    if model is Company:
        return ('__self__',)
    frontier = [((), model)]
    for _depth in range(3):
        nxt = []
        for path, current in frontier:
            for field in current._meta.concrete_fields:
                if field.is_relation and (field.many_to_one or field.one_to_one):
                    if field.related_model is Company:
                        return path + (field.name,)
                    nxt.append((path + (field.name,), field.related_model))
        frontier = nxt
    return None


def company_of(instance):
    path = _company_path(type(instance))
    if path is None:
        return None
    if path == ('__self__',):
        return instance
    value = instance
    for name in path:
        value = getattr(value, name, None)
        if value is None:
            return None
    return value


def module_of(model):
    return django_apps.get_app_config(model._meta.app_label).name


def record(*, company, actor, actor_email, action, module, model_name='', object_id='', object_repr='',
           changed_fields=None, status='success', ip_address=None):
    """Write one row. Used by the signals and by code that logs an action that is not a save (export, refused request)."""
    return AuditLog.objects.create(
        company=company, company_name=(company.name if company else ''),
        actor=actor, actor_email=actor_email or (actor.email if actor else ''),
        action=action, status=status, module=module, model_name=model_name,
        object_id=str(object_id or ''), object_repr=(object_repr or '')[:255],
        changed_fields=changed_fields or [], ip_address=ip_address,
    )


def safe_record(**kwargs):
    """A logging error is written to the server log and never blocks the action itself."""
    try:
        return record(**kwargs)
    except Exception:   # noqa: BLE001
        logger.exception('audit log row could not be written')
        return None
