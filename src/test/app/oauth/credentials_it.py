import os
import tempfile
import unittest

from content_publisher.app.oauth import CredentialsStore, Credentials


class CredentialsTest(unittest.TestCase):
    def test_loads_saved_credentials(self):
        dir_path = os.path.join(tempfile.gettempdir())
        credentials_store = CredentialsStore(dir_path)

        filename = "test_credentials.pickle"
        credentials = Credentials({
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 10000,
            "scopes": ["test-scope-1", "test-scope-2"]
        })

        saved = credentials_store.save(filename, credentials)

        self.assertTrue(saved)

        loaded_credentials = credentials_store.load(filename, credentials.scopes)

        self.assertEqual(loaded_credentials.access_token, "test-access-token")
        self.assertEqual(loaded_credentials.refresh_token, "test-refresh-token")
        self.assertEqual(loaded_credentials.expires_in, 10000)
        self.assertEqual(loaded_credentials.scopes, credentials.scopes)

    def test_loads_saved_credentials_nested_dir(self):
        dir_path = os.path.join(tempfile.gettempdir(), ".content-publisher", "credentials-store-it")
        credentials_store = CredentialsStore(dir_path)

        filename = "/test-dir/test_credentials.pickle"
        credentials = Credentials({
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 10000,
            "scopes": ["test-scope-1", "test-scope-2"]
        })

        saved = credentials_store.save(filename, credentials)

        self.assertTrue(saved)

        loaded_credentials = credentials_store.load(filename, credentials.scopes)

        self.assertEqual(loaded_credentials.access_token, "test-access-token")
        self.assertEqual(loaded_credentials.refresh_token, "test-refresh-token")
        self.assertEqual(loaded_credentials.expires_in, 10000)
        self.assertEqual(loaded_credentials.scopes, credentials.scopes)

if __name__ == '__main__':
    unittest.main()
