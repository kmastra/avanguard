import os
import socket
import sys
import hmac
import hashlib
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../src')))
from client import create_heartbeat, send_heartbeat


class TestClient(unittest.TestCase):

    @patch('client.secret_key', b'supersecretkey')  # Mock secret key
    @patch('time.time', return_value=1234567890)  # Fixed timestamp for predictability
    def test_create_heartbeat(self, mock_time):
        # Act
        heartbeat = create_heartbeat()

        # Assert
        self.assertIsInstance(
            heartbeat, bytes, "The heartbeat should be in bytes format.")
        heartbeat_str = heartbeat.decode()
        self.assertTrue(heartbeat_str.startswith(
            "heartbeat:1234567890:"), "Incorrect message format.")

        # Manually calculate expected HMAC to verify correctness
        message = f"heartbeat:1234567890".encode()
        expected_hmac = hmac.new(
            b'supersecretkey', message, hashlib.sha256).hexdigest()
        self.assertIn(expected_hmac, heartbeat_str,
                      "The HMAC signature does not match.")


    @patch('client.create_heartbeat', return_value=b'heartbeat:message')
    @patch('socket.socket')
    def test_send_heartbeat_success(self, mock_socket, mock_create_heartbeat):
        # Arrange
        mock_socket_instance = MagicMock()
        mock_socket_instance = mock_socket.return_value.__enter__.return_value
        mock_socket_instance.connect.return_value = None  # Successful connect
        mock_socket_instance.sendall.return_value = None  # Successful send
        
        # Act
        send_heartbeat(1, iterations=1)  # Run send_heartbeat with a 1-second interval

        # Assert
        mock_socket_instance.connect.assert_called_once()  # Ensure connection attempted once
        mock_socket_instance.sendall.assert_called_once_with(b'heartbeat:message')  # Ensure heartbeat sent
        mock_create_heartbeat.assert_called_once()  # Ensure heartbeat created once
        
        
    @patch('socket.socket')
    def test_send_heartbeat_connection_refused(self, mock_socket):
        # Arrange
        mock_socket_instance = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        mock_socket_instance.connect.side_effect = ConnectionRefusedError  # Simulate refused connection

        # Act
        with self.assertLogs(level='INFO') as log:  # Capture logs for verification
            send_heartbeat(1, iterations=1)

        # Assert
        self.assertIn("Connection refused by the server. Retrying...", log.output[0], "Should log connection refused error")


    @patch('socket.socket')
    def test_send_heartbeat_timeout(self, mock_socket):
        # Arrange
        mock_socket_instance = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        mock_socket_instance.connect.side_effect = socket.timeout  # Simulate a timeout error

        # Act
        with self.assertLogs(level='INFO') as log:
            send_heartbeat(1, iterations=1)

        # Assert
        self.assertIn("Connection timed out. Retrying...", log.output[0], "Should log timeout error")
        
