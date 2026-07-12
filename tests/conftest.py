"""Shared test configuration."""

import os
import tempfile

# Route the state store to a throwaway file so test runs never touch a
# developer's real pysoar_state.db in the repo root.
_state_db = os.path.join(tempfile.mkdtemp(prefix='pysoar-test-'), 'state.db')
os.environ.setdefault('PYSOAR_STATE_DB', _state_db)
