"""
Finds every API route by itself, so a new endpoint is covered by the matrix tests without anyone editing them.
Used by core/test_api_matrix.py.
"""
import re
import uuid
from dataclasses import dataclass, field

from django.urls import get_resolver

API_PREFIX = 'api/v1/'
FAKE_ID = '00000000-0000-4000-8000-000000000001'   # never exists: asks "would this request be allowed?" without touching data
_SKIP_METHODS = {'options', 'head', 'trace'}


@dataclass
class Route:
    template: str            # e.g. api/v1/tasks/tasks/{pk}/move/
    view_cls: type
    methods: dict = field(default_factory=dict)   # http method -> action name (None for a plain APIView)

    @property
    def has_pk(self):
        return '{pk}' in self.template

    @property
    def list_template(self):
        """The collection this detail route belongs to (api/v1/tasks/tasks/ for .../tasks/{pk}/move/)."""
        return self.template.split('{pk}')[0]

    def url(self, pk=FAKE_ID):
        path = self.template.replace('{pk}', str(pk)).replace('{company_id}', str(uuid.UUID(FAKE_ID))).replace('{resource}', 'employees')
        return '/' + path

    def label(self, method):
        return f'{method.upper()} /{self.template}'

    def required_permission(self, method):
        """The Permission codename the view demands for this method, or None."""
        view = self.view_cls()
        view.action = self.methods.get(method)
        getter = getattr(view, 'get_required_permission', None)
        return getter() if callable(getter) else getattr(view, 'required_permission', None)

    def permission_class_names(self):
        return [c.__name__ for c in getattr(self.view_cls, 'permission_classes', [])]


def _clean(pattern_text):
    text = re.sub(r'\(\?P<pk>\[\^/\.\]\+\)', '{pk}', pattern_text)
    text = text.replace('^', '').replace('$', '').replace('\\.', '.')
    text = text.replace('<uuid:company_id>', '{company_id}').replace('<str:resource>', '{resource}')
    return text


def discover_routes():
    routes = []

    def walk(patterns, prefix=''):
        for p in patterns:
            text = prefix + _clean(str(p.pattern))
            if hasattr(p, 'url_patterns'):
                walk(p.url_patterns, text)
                continue
            if not text.startswith(API_PREFIX) or 'format' in text:
                continue
            callback = p.callback
            cls = getattr(callback, 'cls', None) or getattr(callback, 'view_class', None)
            if cls is None:
                continue
            actions = getattr(callback, 'actions', None)
            if actions:
                methods = dict(actions)
            else:
                methods = {m: None for m in cls.http_method_names if m not in _SKIP_METHODS and hasattr(cls, m)}
            routes.append(Route(template=text, view_cls=cls, methods={m: a for m, a in methods.items() if m not in _SKIP_METHODS}))

    walk(get_resolver().url_patterns)
    return sorted(routes, key=lambda r: r.template)
