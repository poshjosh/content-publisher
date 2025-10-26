import time

import unittest

from content_publisher.app.tiktok.tiktok_content_publisher import TikTokCredentials


class CredentialsTest(unittest.TestCase):
    def test_data(self):
        data = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_at': time.time() + 10000,
            'scopes': ['test-scope-1', 'test-scope-2']
        }
        credentials = TikTokCredentials(data)
        self.assertEqual(credentials.access_token, 'test-access-token')
        self.assertEqual(credentials.scopes, ['test-scope-1', 'test-scope-2'])

    def test_expired(self):
        data = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_at': time.time() - 10000,
            'scopes': ['test-scope-1', 'test-scope-2']
        }
        credentials = TikTokCredentials(data)
        self.assertTrue(credentials.is_expired())

    def test_not_expired(self):
        data = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_at': time.time() + 10000,
            'scopes': ['test-scope-1', 'test-scope-2']
        }
        credentials = TikTokCredentials(data)
        self.assertFalse(credentials.is_expired())

    def test_valid(self):
        data = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_at': time.time() + 10000,
            'scopes': ['test-scope-1', 'test-scope-2']
        }
        credentials = TikTokCredentials(data)
        self.assertTrue(credentials.is_valid(['test-scope-1', 'test-scope-2']))

    def test_invalid(self):
        data = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_at': time.time() + 10000,
            'scopes': ['test-scope-1', 'test-scope-2']
        }
        credentials = TikTokCredentials(data)
        self.assertFalse(credentials.is_valid(['test-scope-3']))
        self.assertFalse(credentials.is_valid([]))


if __name__ == '__main__':
    unittest.main()
