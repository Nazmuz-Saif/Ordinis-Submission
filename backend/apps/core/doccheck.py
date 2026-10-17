"""
Checks that the documents only name things the code really has.
  * every /api/v1/... path is a real route
  * every `Name` or `Name.field` in backticks that looks like a class is a real class (and the field exists, for a model)
A line that says "future", "planned", "not built" or "not yet" is allowed to name something that does not exist yet.
Run:  python manage.py check_docs [--docs-dir DIR]
"""
import ast
import os
import re

from core import docgen
from core.api_matrix import discover_routes

BACKEND_DIR = os.path.dirname(docgen.APPS_DIR)
FUTURE = re.compile(r'future|planned|not built|not yet|roadmap|layer 3|layer 4|layer 5|out of scope|deferred', re.I)
PATH_RE = re.compile(r'/api/v1/[A-Za-z0-9_\-/{}<>:\.]*')
# `ClassName` (two or more words, CamelCase) or `Model.field`. A single capitalised word is too often just a word.
TOKEN_RE = re.compile(r'`([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+|[A-Z][A-Za-z0-9]+(?=\.))(?:\.([a-z_][a-z0-9_]*))?(?:\(\))?`')
# Names that belong to Python, Django, DRF or simplejwt, not to this project.
OUTSIDE = {
    'ValueError', 'IntegrityError', 'ContentType', 'GenericForeignKey', 'ModelViewSet', 'AnonymousUser', 'IsAuthenticated',
    'AllowAny', 'ReadOnlyModelViewSet', 'DefaultRouter', 'ModelSerializer', 'TokenObtainPairView', 'AbstractBaseUser',
    'PermissionDenied', 'ValidationError', 'SQLite', 'PostgreSQL', 'TypeError', 'RuntimeError', 'ProtectedError',
    'UUIDField', 'GenericRelation', 'ForeignKey', 'OneToOneField', 'ManyToManyField', 'PermissionsMixin',
}
FRONTEND_SRC = os.path.join(os.path.dirname(BACKEND_DIR), 'frontend', 'src')


def known_classes():
    """Every class name defined in the backend code (models, serializers, views, permission classes, mixins...)."""
    names = {}
    for root, _dirs, files in os.walk(docgen.APPS_DIR):
        for name in files:
            if name.endswith('.py') and 'migrations' not in root:
                try:
                    tree = ast.parse(open(os.path.join(root, name), encoding='utf-8').read())
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        names[node.name] = True
    return names


def frontend_names():
    """React component and helper names defined in frontend/src (file names and top-level declarations)."""
    names = set()
    if not os.path.isdir(FRONTEND_SRC):
        return names
    for root, _dirs, files in os.walk(FRONTEND_SRC):
        for name in files:
            if name.endswith(('.jsx', '.js')):
                names.add(os.path.splitext(name)[0])
                text = open(os.path.join(root, name), encoding='utf-8', errors='ignore').read()
                names.update(re.findall(r'(?:function|const|class)\s+([A-Z][A-Za-z0-9]+)', text))
    return names


def model_fields():
    fields = {}
    for _app, models_ in docgen.our_models():
        for model in models_:
            fields[model.__name__] = ({f.name for f in model._meta.get_fields()} | {'id', 'pk', 'objects'} |
                                      {n for n in dir(model) if not n.startswith('_')})   # methods count too
    return fields


def _route_regexes():
    patterns = []
    for route in discover_routes():
        template = '/' + route.template
        escaped = re.escape(template)
        for ph in ('pk', 'company_id', 'resource'):
            escaped = escaped.replace(re.escape('{' + ph + '}'), r'[^/]+')
        patterns.append(re.compile('^' + escaped + '$'))
    return patterns


def _normalise(path):
    path = path.rstrip('.,);:`')
    path = re.sub(r'<[^>]*>|\{[^}]*\}', 'X', path)
    if not path.endswith('/'):
        path += '/'
    return path.replace('//', '/')


def check_text(text, source='doc'):
    """List of problems found in one document's text."""
    problems = []
    classes, fields, routes = known_classes(), model_fields(), _route_regexes()
    classes = set(classes) | frontend_names() | OUTSIDE
    for number, line in enumerate(text.splitlines(), start=1):
        if FUTURE.search(line):
            continue
        for raw in PATH_RE.findall(line):
            path = _normalise(raw)
            if path.rstrip('/') in ('/api/v1',):
                continue
            if not any(p.match(path) for p in routes) and not any(p.match(path.rstrip('/') + '/X/') for p in routes):
                # a prefix such as /api/v1/tasks/ is fine when some route starts with it
                if not any(r.template.startswith(path.lstrip('/')) or ('/' + r.template).startswith(path.replace('X/', '')) for r in discover_routes()):
                    problems.append(f'{source}:{number}: endpoint {raw} does not exist')
        for cls, attr in TOKEN_RE.findall(line):
            if attr in ('md', 'py', 'js', 'jsx', 'json', 'xlsx', 'txt', 'css', 'html'):
                continue   # a file name such as `TESTING.md`
            if cls not in classes:
                problems.append(f'{source}:{number}: `{cls}` is not a class in the code')
            elif attr and cls in fields and attr not in fields[cls]:
                problems.append(f'{source}:{number}: `{cls}` has no field `{attr}`')
    return problems


def check_dir(docs_dir):
    problems = []
    for name in sorted(os.listdir(docs_dir)):
        path = os.path.join(docs_dir, name)
        if name.endswith('_differences.md'):
            continue   # a history report: it names the old, wrong things on purpose
        if name.endswith('.md') and os.path.isfile(path):
            problems += check_text(open(path, encoding='utf-8').read(), name)
    return problems
