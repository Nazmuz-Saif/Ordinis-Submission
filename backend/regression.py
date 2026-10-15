"""
The two regression commands (run them from the backend folder):

    python regression.py backend          every backend test (all apps), one line per test, exit code 1 if any fails
    python regression.py selenium         every Selenium test case, PASS / FAIL per case  (see --help for options)
    python regression.py all              backend first, then Selenium

Never run a bare "python manage.py test": it would also pick up the Selenium files in tests/.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def app_labels():
    apps_dir = os.path.join(BASE_DIR, 'apps')
    return sorted(
        name for name in os.listdir(apps_dir)
        if os.path.isfile(os.path.join(apps_dir, name, '__init__.py'))
    )


def run_backend():
    # A real "manage.py test": the settings switch to a fast password hasher only when "test" is on the command line.
    import subprocess
    command = [sys.executable, os.path.join(BASE_DIR, 'manage.py'), 'test', *app_labels(), '--verbosity', '2']
    return subprocess.call(command, cwd=BASE_DIR)


def run_selenium(argv):
    sys.path.insert(0, os.path.join(BASE_DIR, 'tests'))
    import selenium_runner
    return selenium_runner.main(argv)


def main(argv):
    command = argv[0] if argv else ''
    if command == 'backend':
        return run_backend()
    if command == 'selenium':
        return run_selenium(argv[1:])
    if command == 'all':
        backend = run_backend()
        return backend or run_selenium(argv[1:])
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
