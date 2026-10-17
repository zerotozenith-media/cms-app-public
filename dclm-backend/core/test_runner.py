"""Test runner that makes the test suite safe and correct on any server.

On the live server the production settings force HTTPS and keep files in
Azure Blob Storage. The tests talk plain HTTP to Django's test client, so
every request was redirected (301), and any test that saves a receipt or
report would have written into the church's real storage. While the tests
run, this switches HTTPS forcing off and keeps files in a temporary folder
that is deleted afterwards. Nothing changes for the running app.
"""
import shutil
import tempfile

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class SafeTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._media = tempfile.mkdtemp(prefix="dclm-test-media-")
        self._override = override_settings(
            SECURE_SSL_REDIRECT=False,
            SECURE_HSTS_SECONDS=0,
            SESSION_COOKIE_SECURE=False,
            CSRF_COOKIE_SECURE=False,
            MEDIA_ROOT=self._media,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            },
        )
        self._override.enable()

    def teardown_test_environment(self, **kwargs):
        self._override.disable()
        shutil.rmtree(self._media, ignore_errors=True)
        super().teardown_test_environment(**kwargs)
