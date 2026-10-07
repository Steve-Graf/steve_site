"""Builds the Odds client into a temp dir and runs every browser check against it.

    venv/bin/python tests/odds_ui/run_all.py

Needs playwright + chromium in the venv. The checks mock the API, so no server is required.
Screenshots land in tests/odds_ui/out/.
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT = os.path.join(HERE, '..', '..', 'client')
SCRIPTS = ['verify_ui.py', 'verify_help_survivor.py', 'verify_close.py', 'verify_recap.py', 'verify_cards.py', 'verify_prefs.py']

with tempfile.TemporaryDirectory() as dist:
    build = subprocess.run(['npx', 'vite', 'build', '--outDir', dist, '--emptyOutDir'], cwd=CLIENT, capture_output=True, text=True)
    if build.returncode != 0:
        print(build.stdout[-2000:], build.stderr[-2000:])
        sys.exit('build failed')
    env = dict(os.environ, ODDS_DIST=dist)
    failed = []
    for script in SCRIPTS:
        print(f'\n===== {script}')
        if subprocess.run([sys.executable, os.path.join(HERE, script)], env=env).returncode != 0:
            failed.append(script)

print('\nFAILED: ' + ', '.join(failed) if failed else '\nAll browser checks passed.')
sys.exit(1 if failed else 0)
