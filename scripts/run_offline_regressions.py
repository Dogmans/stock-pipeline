"""Run targeted regressions with temporary storage and network access blocked."""
import logging
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    original_directory = Path.cwd()
    with tempfile.TemporaryDirectory(prefix='stock-pipeline-tests-') as temporary:
        os.chdir(temporary)
        try:
            with ExitStack() as stack:
                stack.enter_context(patch('dotenv.load_dotenv', return_value=False))
                stack.enter_context(patch.dict(os.environ, {'FINANCIAL_MODELING_PREP_API_KEY': 'offline-test'}))
                for target in ('requests.sessions.Session.request',
                               'curl_cffi.requests.Session.request',
                               'socket.socket.connect'):
                    stack.enter_context(patch(target, side_effect=AssertionError('Network access is forbidden in offline tests')))
                suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_regressions')
                result = unittest.TextTestRunner(verbosity=2).run(suite)
                return 0 if result.wasSuccessful() else 1
        finally:
            cache_module = sys.modules.get('cache_config')
            if cache_module is not None:
                cache_module.cache.close()
            logging.shutdown()
            os.chdir(original_directory)


if __name__ == '__main__':
    raise SystemExit(main())
