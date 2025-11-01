import time

import unittest

from content_publisher.app.oauth.credentials import Credentials


class CredentialsTest(unittest.TestCase):
    def test_data(self):
        data = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_in': time.time() + 10000,
            'scopes': ['test-scope-1', 'test-scope-2']
        }
        credentials = Credentials(data)
        self.assertEqual(credentials.access_token, 'test-access-token')
        self.assertEqual(credentials.scopes, ['test-scope-1', 'test-scope-2'])

    def test_no_data(self):
        data = { }
        credentials = Credentials(data)
        self.assertIsNone(credentials.access_token)
        self.assertEqual(credentials.scopes, [])

    def test_expired_given_zero(self):
        data = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_in': 0,
            'scopes': ['test-scope-1', 'test-scope-2']
        }
        credentials = Credentials(data)
        self.assertTrue(credentials.is_expired())

    def test_expired_given_negative(self):
        data = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_in': -100,
            'scopes': ['test-scope-1', 'test-scope-2']
        }
        credentials = Credentials(data)
        self.assertTrue(credentials.is_expired())

    def test_not_expired(self):
        data = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_in': 10000,
            'scopes': ['test-scope-1', 'test-scope-2']
        }
        credentials = Credentials(data)
        self.assertFalse(credentials.is_expired())

    def test_valid(self):
        data = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_in': 10000,
            'scopes': ['test-scope-1', 'test-scope-2']
        }
        credentials = Credentials(data)
        self.assertTrue(credentials.is_valid(['test-scope-1', 'test-scope-2']))

    def test_invalid(self):
        data = {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'expires_in': 10000,
            'scopes': ['test-scope-1', 'test-scope-2']
        }
        credentials = Credentials(data)
        self.assertFalse(credentials.is_valid(['test-scope-3']))
        self.assertFalse(credentials.is_valid([]))


if __name__ == '__main__':
    unittest.main()
