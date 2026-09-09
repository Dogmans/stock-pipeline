"""Run targeted regressions with temporary storage and network access blocked."""
import logging
import os
from pathlib import Path
import socket
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
                               'curl_cffi.requests.Session.request'):
                    stack.enter_context(patch(target, side_effect=AssertionError('Network access is forbidden in offline tests')))
                real_connect = socket.socket.connect
                def local_connect(sock, address):
                    host = address[0] if isinstance(address, tuple) else ''
                    if host not in ('127.0.0.1', '::1', 'localhost'):
                        raise AssertionError('External network access is forbidden in offline tests')
                    return real_connect(sock, address)
                stack.enter_context(patch('socket.socket.connect', new=local_connect))
                suite = unittest.defaultTestLoader.loadTestsFromNames([
                    'tests.test_regressions', 'tests.test_fmp_transport', 'tests.test_workflow',
                    'tests.test_visual_api',
                ])
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
