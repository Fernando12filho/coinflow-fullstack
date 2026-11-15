"""Static checks for the desktop build workflow (PLAN.md Phase 8.4).

GitHub Actions can't run here, so these pin down the properties that matter:
every platform is built and smoke-tested, releases only come from version tags,
and macOS signing only runs when the Apple secrets exist.
"""
from pathlib import Path

import pytest

yaml = pytest.importorskip('yaml')

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / '.github' / 'workflows' / 'desktop.yml'


@pytest.fixture(scope='module')
def workflow():
    data = yaml.safe_load(WORKFLOW.read_text())
    data['on'] = data.pop(True, data.get('on'))  # YAML 1.1 reads the key `on` as True
    return data


def steps_text(job):
    return '\n'.join(str(step) for step in job['steps'])


def test_runs_on_version_tags_and_by_hand(workflow):
    assert workflow['on']['push']['tags'] == ['v*']
    assert 'workflow_dispatch' in workflow['on']


def test_tests_run_before_building(workflow):
    assert workflow['jobs']['build']['needs'] == 'test'
    assert 'pytest' in steps_text(workflow['jobs']['test'])


def test_builds_every_platform(workflow):
    runners = {entry['os'] for entry in workflow['jobs']['build']['strategy']['matrix']['include']}
    assert any(r.startswith('macos') for r in runners)
    assert any(r.startswith('windows') for r in runners)
    assert any(r.startswith('ubuntu') for r in runners)
    assert len([r for r in runners if r.startswith('macos')]) == 2   # Apple Silicon and Intel


def test_every_build_is_smoke_tested_and_checksummed(workflow):
    text = steps_text(workflow['jobs']['build'])
    assert 'pyinstaller --noconfirm coinflow.spec' in text
    assert '--smoke-test' in text
    assert 'sha256' in text.lower()


def test_tag_must_match_the_app_version(workflow):
    assert 'app/version.py' in steps_text(workflow['jobs']['build']) or \
        '__version__' in steps_text(workflow['jobs']['build'])


def test_signing_only_with_secrets(workflow):
    build = workflow['jobs']['build']
    signing = [s for s in build['steps'] if 'codesign' in str(s.get('run', '')) or 'notarytool' in str(s.get('run', ''))]
    assert signing, 'no signing steps'
    for step in signing:
        assert 'APPLE_' in str(step.get('if', '')) or 'APPLE_' in str(build.get('env', {})), step.get('name')
        assert "runner.os == 'macOS'" in str(step.get('if', ''))


def test_release_only_from_tags_with_write_access(workflow):
    release = workflow['jobs']['release']
    assert "startsWith(github.ref, 'refs/tags/v')" in release['if']
    assert release['permissions'] == {'contents': 'write'}
    assert workflow.get('permissions') == {'contents': 'read'}   # everything else is read-only


def test_releasing_guide_lists_the_secrets():
    guide = (ROOT / 'RELEASING.md').read_text()
    for secret in ('APPLE_CERTIFICATE_P12', 'APPLE_CERTIFICATE_PASSWORD', 'APPLE_SIGNING_IDENTITY',
                   'APPLE_API_KEY_ID', 'APPLE_API_ISSUER_ID', 'APPLE_API_KEY_P8'):
        assert secret in guide, secret
        assert secret in WORKFLOW.read_text(), secret
