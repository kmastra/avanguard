import os
import sys
import hmac
import hashlib
import unittest
import time
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../src')))
from server import try_notify_channels, is_heartbeat_valid


class TestServer(unittest.TestCase):
    
    @patch('client.should_send_notification', return_value=True)
    @patch('client.send_pushbullet_not')
    @patch('client.send_telegram_not', new_callable=AsyncMock)
    @patch('client.pushbullet_use', True)  # Simulate Pushbullet enabled
    @patch('logging.warning')
    async def test_try_notify_channels_with_pushbullet(self, mock_log_warning, mock_telegram, mock_pushbullet, mock_should_send):
        # Act
        await try_notify_channels("Test Title", "Test Body")

        # Assert
        mock_should_send.assert_called_once()
        mock_pushbullet.assert_called_once_with("Test Title", "Test Body")  # Ensure Pushbullet notification sent
        mock_telegram.assert_awaited_once_with("Test Title Test Body")  # Ensure Telegram notification sent
        mock_log_warning.assert_called_once_with('Sent notification: "Test Title Test Body"')

    @patch('client.should_send_notification', return_value=True)
    @patch('client.send_pushbullet_not')
    @patch('client.send_telegram_not', new_callable=AsyncMock)
    @patch('client.pushbullet_use', False)  # Simulate Pushbullet disabled
    @patch('logging.warning')
    async def test_send_notification_without_pushbullet(self, mock_log_warning, mock_telegram, mock_pushbullet, mock_should_send):
        # Act
        await try_notify_channels("Test Title", "Test Body")

        # Assert
        mock_should_send.assert_called_once()
        mock_pushbullet.assert_not_called()  # Ensure Pushbullet notification is not sent
        mock_telegram.assert_awaited_once_with("Test Title Test Body")  # Ensure Telegram notification sent
        mock_log_warning.assert_called_once_with('Sent notification: "Test Title Test Body"')

    @patch('client.should_send_notification', return_value=False)
    @patch('client.send_pushbullet_not')
    @patch('client.send_telegram_not', new_callable=AsyncMock)
    @patch('logging.info')
    async def test_notification_snoozed(self, mock_log_info, mock_telegram, mock_pushbullet, mock_should_send):
        # Act
        await try_notify_channels("Test Title", "Test Body")

        # Assert
        mock_should_send.assert_called_once()
        mock_pushbullet.assert_not_called()  # Ensure no notification sent
        mock_telegram.assert_not_awaited()  # Ensure no Telegram notification sent
        mock_log_info.assert_called_once_with('Notification "Test Title Test Body" snoozed, not sent.')


class TestValidateHeartbeat(unittest.TestCase):
    
    def setUp(self):
        self.test_secret_key = b'supersecretkey'
        self.valid_timestamp = str(int(time.time()))
        self.valid_message = f'heartbeat:{self.valid_timestamp}'.encode()
        self.valid_hmac = hmac.new(self.test_secret_key, self.valid_message, hashlib.sha256).hexdigest()
        self.valid_data = f"heartbeat:{self.valid_timestamp}:{self.valid_hmac}".encode()

    def test_validate_heartbeat(self):
        self.assertTrue(is_heartbeat_valid(self.valid_data))

