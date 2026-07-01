"""Integration Specific Functions"""
import os

from pymisp import PyMISP
from pymisp import MISPEvent
from classes import Log
from integrations.base import use_mock_mode

MOCK_INDICATORS = {
    'ip-dst': ['203.0.113.10', '203.0.113.20', '198.51.100.5'],
    'domain': ['malicious.example.com'],
}


def _use_mock_mode(misp_init):
    return use_mock_mode(misp_init)


class MispFunction:
    """Class for MISP functions."""
    CERT_PATH = './certs/api_user.crt'
    CA_CERT_PATH = './certs/CA.crt'
    KEY_PATH = './certs/api_user.key'

    FEEDS_BY_DATA_TYPE = {
        'ip-dst': ['firehol_level1', 'malsilo.ipv4'],
        'domain': ['Domains from High-Confidence DGA-based C&C Domains Actively Resolving', 'malsilo.domain'],
        'url': ['CyberCure - Blocked URL Feed'],
        'hostname': ['hostname_feed_1'],
        'hash': ['CyberCure - Hash Feed', 'http://cybercrime-tracker.net hashlist'],
        'filename': ['filename_feed_id_1', 'filename_feed_id_2'],
        'email': ['email_feed_id_1', 'email_feed_id_2'],
    }

    def __init__(self, misp_init):
        self.log = Log.get_instance()
        self._mock = _use_mock_mode(misp_init)
        if self._mock:
            self.log.warning("MISP integration running in mock/offline mode")
            self.misp_api = None
            self._feeds = self._mock_feeds()
            self.enabled_feeds = self.get_enabled_feeds()
            return
        self.misp_api = PyMISP(
            misp_init.url,
            misp_init.api_key,
            misp_init.ssl,
            misp_init.verifycert,
        )
        self._feeds = self._get_feeds()
        self.enabled_feeds = self.get_enabled_feeds()

    def _mock_feeds(self):
        return [
            {
                'Feed': {
                    'id': '1',
                    'name': 'firehol_level1',
                    'enabled': True,
                    'event_id': '1',
                }
            }
        ]

    def get_enabled_feeds(self):
        """Get the list of enabled feeds from MISP."""
        self.log.info("Getting enabled feeds from MISP...")
        enabled_feeds = {}
        for feed in self.feeds:
            if feed['Feed']['enabled']:
                feed_type = next(
                    (
                        data_type
                        for data_type, feed_list in self.FEEDS_BY_DATA_TYPE.items()
                        if feed['Feed']['name'] in feed_list
                    ),
                    None,
                )
                enabled_feeds[feed['Feed']['name']] = {
                    'feed_id': feed['Feed']['id'],
                    'data_types': feed_type,
                    'metadata': feed['Feed'],
                }
        for feed_name, feed_data in enabled_feeds.items():
            feed_data['metadata'].pop('name', None)
            feed_data['metadata'].pop('id', None)
        self.log.debug(f"Enabled feeds: {enabled_feeds}")
        return enabled_feeds

    def send_to_misp(self, event):
        """Send an event to MISP."""
        if isinstance(event, dict):
            misp_event = MISPEvent()
            misp_event.from_dict(event)
            return self.misp_api.add_event(misp_event, pythonify=True)
        return self.misp_api.add_event(event, pythonify=True)

    def get_misp_event(self, event_id):
        """Get an event from MISP."""
        return self.misp_api.get_event(event_id, pythonify=True)

    def create_misp_event(self, info, distribution, threat_level_id, analysis, date=None):
        """Create a new event in MISP."""
        event = MISPEvent()
        event.info = info
        event.distribution = distribution
        event.threat_level_id = threat_level_id
        event.analysis = analysis
        if date:
            event.date = date
        return self.misp_api.add_event(event, pythonify=True)

    def enable_threat_feed(self, feed_id=None, data_type='ip-dst'):
        """Enable a threat feed by id/name, or auto-enable for a data type."""
        if self._mock:
            return True
        if feed_id is None:
            return self.ensure_feed_enabled(data_type)
        self.misp_api.enable_feed(feed_id)
        self._cache_feed(feed_id)
        return True

    def disable_threat_feed(self, feed_id):
        """Disable a threat feed in MISP by its id or name."""
        self.misp_api.disable_feed(feed_id)
        return True

    def check_enabled_by_name(self, feed_name):
        """Check if a feed is enabled in MISP by name."""
        return bool(
            next(
                (
                    feed['Feed']
                    for feed in self.feeds
                    if feed['Feed']['name'] == feed_name and feed['Feed']['enabled']
                ),
                None,
            )
        )

    def ensure_feed_enabled(self, data_type):
        """Ensure at least one feed for the given data type is enabled."""
        potential_feeds = self.FEEDS_BY_DATA_TYPE.get(data_type, [])
        enabled_feed_name = next(
            (feed for feed in potential_feeds if feed in self.enabled_feeds),
            None,
        )
        if enabled_feed_name:
            return True

        feed_to_enable = potential_feeds[0] if potential_feeds else None
        if not feed_to_enable:
            self.log.error(f"No configured feeds for data type {data_type}")
            return False

        feed_data = self._get_misp_feed_by_name(feed_to_enable)
        feed_id = feed_data.get('id')
        if not feed_id:
            self.log.error(f"Feed '{feed_to_enable}' not found in MISP")
            return False

        self.enable_threat_feed(feed_id)
        self._feeds = self._get_feeds()
        self.enabled_feeds = self.get_enabled_feeds()
        return True

    def _resolve_feed_id(self, data_type='ip-dst', feed_id=None):
        if feed_id is not None:
            return str(feed_id)
        for feed_name, details in self.enabled_feeds.items():
            if details.get('data_types') == data_type:
                return str(details['feed_id'])
        potential = self.FEEDS_BY_DATA_TYPE.get(data_type, [])
        for feed_name in potential:
            feed_data = self._get_misp_feed_by_name(feed_name)
            if feed_data.get('enabled'):
                return str(feed_data['id'])
        if potential:
            self.ensure_feed_enabled(data_type)
            self.enabled_feeds = self.get_enabled_feeds()
            return self._resolve_feed_id(data_type)
        raise ValueError(f"No enabled feed available for data type {data_type}")

    def _cache_feed(self, feed_id):
        self.misp_api.cache_feed(feed_id)

    def _get_cached_feed(self, feed_id):
        return self.misp_api.get_feed(feed_id)

    def get_event_id(self, feed_id):
        feed = self._get_cached_feed(feed_id)
        return feed['Feed']['event_id']

    def _attribute_value(self, attr):
        if isinstance(attr, dict):
            return attr.get('value')
        return getattr(attr, 'value', None)

    def _attribute_type(self, attr):
        if isinstance(attr, dict):
            return attr.get('type')
        return getattr(attr, 'type', None)

    def get_event_data_by_type(self, data_type='ip-dst', feed_id=None):
        """Get indicator values from a cached MISP feed event."""
        if self._mock:
            values = MOCK_INDICATORS.get(data_type, [])
            self.log.info(f"Mock mode returning {len(values)} {data_type} indicator(s)")
            return values
        resolved_feed_id = self._resolve_feed_id(data_type, feed_id)
        event_id = self.get_event_id(resolved_feed_id)
        event_data = self.get_misp_event(event_id)

        attributes = []
        if hasattr(event_data, 'attributes'):
            attributes = event_data.attributes
        elif isinstance(event_data, dict):
            attributes = event_data.get('Attribute', [])

        values = [
            self._attribute_value(attr)
            for attr in attributes
            if self._attribute_type(attr) == data_type and self._attribute_value(attr)
        ]
        self.log.info(
            f"Retrieved {len(values)} {data_type} indicator(s) from feed {resolved_feed_id}"
        )
        return values

    def get_misp_event_by_type(self, data_type='ip-dst', feed_id=None):
        """Playbook alias for get_event_data_by_type."""
        return self.get_event_data_by_type(data_type=data_type, feed_id=feed_id)

    def _search_attributes(self, attribute_type, value=None):
        search_params = {
            'type_attribute': attribute_type,
            'value': value,
            'to_ids': True,
            'include_context': True,
        }
        return self.misp_api.search('attributes', **search_params)

    def _get_misp_feed_by_name(self, feed_name):
        return next(
            (feed['Feed'] for feed in self.feeds if feed['Feed']['name'] == feed_name),
            {},
        )

    def _get_misp_feed_by_id(self, feed_id):
        return next(
            (feed['Feed'] for feed in self.feeds if str(feed['Feed']['id']) == str(feed_id)),
            {},
        )

    def _get_feeds(self):
        try:
            self.misp_api.load_default_feeds()
            return self.misp_api.feeds()
        except Exception as e:
            self.log.error(f"Error loading MISP feeds: {e}")
            return []

    @property
    def feeds(self):
        return self._feeds or self._get_feeds()
