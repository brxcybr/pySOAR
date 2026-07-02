#!/usr/bin/env python3

import unittest
from unittest.mock import MagicMock, patch

from classes import ConfigurationManager, PlaybookFunction


class TestSmtpNotifier(unittest.TestCase):
    def _init(self, **params):
        init = MagicMock()
        init.url = params.get('url', 'mail.example.com:587')
        init.api_key = params.get('api_key', '')
        init.ssl = True
        init.verifycert = True
        init.params = {'smtp': params.get('smtp', {
            'from_addr': 'pysoar@example.com',
            'to_addrs': ['ops@example.com'],
        })}
        return init

    def test_mock_mode_send(self):
        import os

        from integrations.smtp_functions import SmtpFunction

        with patch.dict(os.environ, {'PYSOAR_MOCK_INTEGRATIONS': '1'}):
            smtp = SmtpFunction(self._init())
            result = smtp.send_email(subject='test', message='hello')
        self.assertTrue(result['email-status'])
        self.assertTrue(result.get('mock'))

    def test_no_recipients_fails_cleanly(self):
        import os

        from integrations.smtp_functions import SmtpFunction

        with patch.dict(os.environ, {'PYSOAR_MOCK_INTEGRATIONS': '1'}):
            smtp = SmtpFunction(self._init(smtp={'from_addr': 'x@y', 'to_addrs': []}))
            result = smtp.send_email(message='hello')
        self.assertFalse(result['email-status'])

    def test_host_port_parsing(self):
        import os

        from integrations.smtp_functions import SmtpFunction

        with patch.dict(os.environ, {'PYSOAR_MOCK_INTEGRATIONS': '1'}):
            smtp = SmtpFunction(self._init(url='smtp://relay.example.com:2525'))
            self.assertEqual(smtp._host_port(), ('relay.example.com', 2525))
            smtp2 = SmtpFunction(self._init(url='relay.example.com'))
            self.assertEqual(smtp2._host_port(), ('relay.example.com', 587))


class TestManifestRetries(unittest.TestCase):
    @patch('time.sleep')  # don't actually wait during backoff
    @patch.object(ConfigurationManager, 'resolve_callable')
    @patch('integrations.dispatch.find_integration_for_function')
    def test_retries_until_success(self, mock_find, mock_resolve, _sleep):
        from core.manifests import ActionManifest, ManifestRegistry

        registry = ManifestRegistry.get_instance()
        registry.register(ActionManifest(
            name='flaky_action',
            integration='testint',
            retries=2,
            retry_backoff_seconds=0.01,
        ))

        integration = MagicMock()
        integration.returns = []
        mock_find.return_value = integration

        attempts = {'count': 0}

        def flaky(**_kwargs):
            attempts['count'] += 1
            if attempts['count'] < 3:
                raise ConnectionError('flaky link')
            return True

        mock_resolve.return_value = (MagicMock(), flaky)

        step = PlaybookFunction(
            name='flaky_action',
            trigger={'type': 'always'},
            on_success='halt_playbook',
            on_fail='never',
        )
        _, next_step = step.execute({}, ConfigurationManager())
        self.assertEqual(attempts['count'], 3)
        self.assertEqual(next_step, 'halt_playbook')

    @patch('time.sleep')
    @patch.object(ConfigurationManager, 'resolve_callable')
    @patch('integrations.dispatch.find_integration_for_function')
    def test_exhausted_retries_route_to_on_fail(self, mock_find, mock_resolve, _sleep):
        from core.manifests import ActionManifest, ManifestRegistry

        ManifestRegistry.get_instance().register(ActionManifest(
            name='always_down',
            integration='testint',
            retries=1,
            retry_backoff_seconds=0.01,
        ))

        integration = MagicMock()
        integration.returns = []
        mock_find.return_value = integration

        def broken(**_kwargs):
            raise ConnectionError('down')

        mock_resolve.return_value = (MagicMock(), broken)

        step = PlaybookFunction(
            name='always_down',
            trigger={'type': 'always'},
            on_success='never',
            on_fail='halt_playbook',
        )
        _, next_step = step.execute({}, ConfigurationManager())
        self.assertEqual(next_step, 'halt_playbook')


if __name__ == '__main__':
    unittest.main()
