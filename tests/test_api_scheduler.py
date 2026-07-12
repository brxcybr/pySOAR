#!/usr/bin/env python3

import unittest
from unittest.mock import MagicMock, patch

try:
    from fastapi.testclient import TestClient
    HAS_API = True
except ImportError:
    HAS_API = False


@unittest.skipUnless(HAS_API, "fastapi not installed")
class TestAPIServer(unittest.TestCase):
    def setUp(self):
        from api_server import create_app

        self.mock_cm = MagicMock()
        self.mock_pm = MagicMock()
        self.mock_cm.playbook_mgr = self.mock_pm
        self.mock_cm.enabled_integrations = []
        self.mock_cm.update_enabled_items = MagicMock()
        self.mock_pm.playbook_names = ['test']
        self.mock_pm.playbooks_data = {
            'test': {
                'enabled': True,
                'is_running': False,
                'integration_dependencies': ['misp'],
                'logic': [{'function': 'halt_playbook'}],
            }
        }
        self.mock_pm._load_all_playbooks_if_required = MagicMock()
        self.mock_pm.launch_playbook = MagicMock(return_value=True)
        self.app = create_app(self.mock_cm)
        self.client = TestClient(self.app)

    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_list_playbooks(self):
        response = self.client.get('/playbooks')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['name'], 'test')

    def test_run_playbook(self):
        response = self.client.post('/playbooks/test/run', json={'once': True})
        self.assertEqual(response.status_code, 200)
        self.mock_pm.launch_playbook.assert_called_once()


class TestScheduler(unittest.TestCase):
    @patch('scheduler.ConfigurationManager')
    def test_schedule_interval(self, mock_cm_cls):
        from scheduler import PlaybookScheduler

        mock_cm = MagicMock()
        mock_cm_cls.return_value = mock_cm
        sched = PlaybookScheduler(mock_cm)
        with patch('apscheduler.schedulers.background.BackgroundScheduler') as mock_sched_cls:
            mock_sched = mock_sched_cls.return_value
            job_id = sched.schedule_interval('test', 60, once=True)
            self.assertEqual(job_id, 'playbook-test')
            mock_sched.add_job.assert_called_once()


if __name__ == '__main__':
    unittest.main()
