from unittest import mock

import unittest

from content_publisher import Content, App, SocialPlatformType, SocialContentPublisher, \
    ConfigFactory
from content_publisher.app.config import PublisherConfig
from content_publisher.app.content_publisher import SocialContentPublisherFactory, PostResult


class AppTest(unittest.TestCase):
    def test_publish_content(self):
        with mock.patch.object(SocialContentPublisherFactory, 'get_publisher') as mock_get_publisher:
            with mock.patch.object(ConfigFactory, "get_publisher_config") as mock_get_publisher_config:

                success_message = "success"
                mock_publisher = mock.Mock(spec=SocialContentPublisher)
                mock_publisher._authenticate.return_value = True
                mock_publisher.validate_content.return_value = PostResult(success=True, message="valid")
                mock_publisher.post_content.return_value = PostResult(success=True, message=success_message)
                mock_get_publisher.return_value = mock_publisher

                mock_publisher_config = mock.Mock(spec=PublisherConfig)
                # mock_publisher_config.endpoint.return_value = "https://mocked-endpoint"
                # mock_publisher_config.credentials.return_value = { "client_secret": "mocked-client-secret" }
                mock_get_publisher_config.return_value = mock_publisher_config

                platforms = SocialPlatformType.values()

                result = App().publish_content(platforms, Content("test-content"))

                for platform in platforms:
                    self.assertIn(platform, result)
                    self.assertIsInstance(result[platform], PostResult)
                    self.assertTrue(result[platform].success)
                    self.assertEqual(result[platform].message, success_message)

                self.assertEqual(mock_get_publisher.call_count, len(platforms))
                self.assertEqual(mock_publisher.validate_content.call_count, len(platforms))
                self.assertEqual(mock_publisher.post_content.call_count, len(platforms))

                self.assertEqual(mock_get_publisher_config.call_count, len(platforms))
                # self.assertEqual(mock_publisher_config.endpoint.call_count, len(platforms))
                # self.assertEqual(mock_publisher_config.credentials.call_count, len(platforms))


if __name__ == '__main__':
    unittest.main()
