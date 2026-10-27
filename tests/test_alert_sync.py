import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import sync_alert_data as sync


class AlertSyncTests(unittest.TestCase):
    def test_payload_preserves_exact_data_and_cannot_touch_notification_state(self):
        # Synthetic metadata only; actual financial data is validated by verify_artifact.
        with tempfile.TemporaryDirectory() as folder, patch('verify_publication.verify_artifact'):
            out = Path(folder)
            daily = '{"date":"2026-10-26"}'
            qdii = '{"fetched_at":"2026-10-27T00:02:47+00:00"}'
            (out/'data.json').write_text(daily)
            (out/'qdii.json').write_text(qdii)
            entries = {x['key']:x['value'] for x in sync.payload(out, 'test-revision')}
            self.assertEqual(set(entries), sync.ALLOWED_KEYS)
            self.assertEqual(entries['daily_data'], daily)
            self.assertEqual(entries['qdii_data'], qdii)
            self.assertEqual(json.loads(entries['data_meta'])['datasets']['daily_data']['date'], '2026-10-26')
            self.assertTrue({'daily_state','qdii_state'}.isdisjoint(entries))

    def test_invalid_artifact_cannot_be_synchronized(self):
        with patch('verify_publication.verify_artifact', side_effect=ValueError('stale artifact')):
            with self.assertRaises(ValueError):
                sync.payload(ROOT/'dist', 'test')

    def test_write_uses_only_allowed_keys_and_permission_failure_is_explicit(self):
        with self.assertRaises(ValueError):
            sync.publish([{'key':'daily_state','value':'{}'}], 'test-token')
        entries = [{'key':k,'value':'{}'} for k in sync.ALLOWED_KEYS]
        with patch.object(sync.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"success":true}')) as request:
            sync.publish(entries, 'test-token')
            sent = request.call_args.args[0]
            self.assertEqual(sent.method, 'PUT')
            self.assertEqual({x['key'] for x in json.loads(sent.data)}, sync.ALLOWED_KEYS)
        error = urllib.error.HTTPError('https://api.cloudflare.com', 403, 'forbidden', {}, None)
        with patch.object(sync.urllib.request, 'urlopen', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, 'Workers KV Storage Edit'):
                sync.publish(entries, 'test-token')
