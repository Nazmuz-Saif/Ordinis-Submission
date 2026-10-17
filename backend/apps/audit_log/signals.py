from django.db.models.signals import post_delete, post_save, pre_save

from . import context
from .services import EXCLUDED_MODELS, SKIP_FIELDS, SPECIAL, company_of, module_of, our_app_labels, safe_record

_labels = None


def _audited(sender):
    global _labels
    if _labels is None:
        _labels = our_app_labels()
    return sender._meta.app_label in _labels and sender.__name__ not in EXCLUDED_MODELS and not sender._meta.abstract


def _repr(instance):
    try:
        return str(instance)
    except Exception:   # noqa: BLE001
        return f'{type(instance).__name__} {instance.pk}'


def _remember_old_values(sender, instance, raw=False, **kwargs):
    """Before an update, keep the stored values so we can name the fields that really changed."""
    if raw or instance._state.adding or not _audited(sender) or not context.current()[3]:
        return
    fields = [f.attname for f in sender._meta.concrete_fields]
    instance._audit_old = sender._base_manager.filter(pk=instance.pk).values(*fields).first()


def _log(instance, action, changed=None):
    user, ip, label, active = context.current()
    if not active:
        return
    company = company_of(instance)
    if company is None:
        return
    special_action, special_status = SPECIAL.get(type(instance).__name__, (None, None))
    status = special_status or ('warning' if action == 'delete' else 'success')
    safe_record(
        company=company, actor=user, actor_email=(user.email if user else label), action=special_action or action,
        module=module_of(type(instance)), model_name=type(instance).__name__, object_id=instance.pk,
        object_repr=_repr(instance), changed_fields=changed or [], status=status, ip_address=ip,
    )


def _after_save(sender, instance, created, raw=False, update_fields=None, **kwargs):
    if raw or not _audited(sender) or not context.current()[3]:
        return
    if created:
        _log(instance, 'create')
        return
    old = getattr(instance, '_audit_old', None)
    if old is None:
        return
    names = [f.name for f in sender._meta.concrete_fields
             if f.name not in SKIP_FIELDS and (update_fields is None or f.name in update_fields or f.attname in update_fields)]
    changed = [n for n in names if old.get(sender._meta.get_field(n).attname) != getattr(instance, sender._meta.get_field(n).attname)]
    if changed:   # a save that changed nothing is not an action
        _log(instance, 'update', changed)
    instance._audit_old = None


def _after_delete(sender, instance, **kwargs):
    if not _audited(sender) or not context.current()[3]:
        return
    _log(instance, 'delete')


pre_save.connect(_remember_old_values, dispatch_uid='audit_pre_save')
post_save.connect(_after_save, dispatch_uid='audit_post_save')
post_delete.connect(_after_delete, dispatch_uid='audit_post_delete')
