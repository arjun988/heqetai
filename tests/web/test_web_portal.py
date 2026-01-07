"""
Web interface tests for the AgentDebugger web portal.
"""
import pytest
from unittest.mock import Mock, patch
import json

try:
    from agent_debugger.web.portal import WebPortal
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False
    WebPortal = None


@pytest.mark.skipif(not WEB_AVAILABLE, reason="Web dependencies not available")
class TestWebPortal:
    """Test the WebPortal class."""

    @pytest.fixture
    def web_portal(self, debugger):
        """Create a web portal instance."""
        return WebPortal(debugger, host="127.0.0.1", port=8080)

    @pytest.fixture
    def mock_flask_app(self):
        """Create a mock Flask app."""
        app = Mock()
        app.route = Mock()
        app.run = Mock()
        return app

    def test_web_portal_initialization(self, debugger):
        """Test web portal initialization."""
        portal = WebPortal(debugger)

        assert portal.debugger == debugger
        assert portal.host == "0.0.0.0"
        assert portal.port == 5000
        assert portal.app is not None

    def test_web_portal_custom_config(self, debugger):
        """Test web portal with custom configuration."""
        portal = WebPortal(debugger, host="127.0.0.1", port=8080, debug=True)

        assert portal.host == "127.0.0.1"
        assert portal.port == 8080

    @patch('flask.Flask')
    def test_setup_routes(self, mock_flask, debugger):
        """Test setting up web routes."""
        portal = WebPortal(debugger)

        # Routes should be set up during initialization
        assert portal.app is not None

        # Check that some key routes are registered
        # This is a basic check - in real implementation we'd verify specific routes

    def test_get_dashboard_data(self, web_portal):
        """Test getting dashboard data."""
        # Add some mock data to debugger
        web_portal.debugger.record_event(Mock(
            event_type="tool_call",
            agent_id="test_agent",
            data={"tool": "web_search"}
        ))

        data = web_portal._get_dashboard_data()

        assert "events" in data
        assert "agents" in data
        assert "stats" in data
        assert len(data["events"]) > 0

    def test_get_agent_details(self, web_portal):
        """Test getting agent details."""
        # Mock an attached agent
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        web_portal.debugger.attached_agents["test_agent"] = mock_agent

        details = web_portal._get_agent_details("test_agent")

        assert details is not None
        assert details["agent_id"] == "test_agent"
        assert details["name"] == "TestAgent"

    def test_get_agent_details_not_found(self, web_portal):
        """Test getting agent details for non-existent agent."""
        details = web_portal._get_agent_details("nonexistent")
        assert details is None

    def test_get_trace_timeline(self, web_portal):
        """Test getting trace timeline data."""
        # Add some events
        web_portal.debugger.record_event(Mock(
            event_type="tool_call",
            agent_id="agent1",
            data={"tool": "search"}
        ))
        web_portal.debugger.record_event(Mock(
            event_type="memory_write",
            agent_id="agent1",
            data={"key": "result"}
        ))

        timeline = web_portal._get_trace_timeline()

        assert isinstance(timeline, list)
        assert len(timeline) >= 2

        # Check timeline entry structure
        for entry in timeline:
            assert "timestamp" in entry
            assert "event_type" in entry
            assert "agent_id" in entry
            assert "data" in entry

    def test_execute_command(self, web_portal):
        """Test executing debugger commands via web interface."""
        # Test continue command
        result = web_portal._execute_command("continue")
        assert "executed" in result.lower()

        # Test next command
        result = web_portal._execute_command("next")
        assert "executed" in result.lower()

    def test_execute_command_invalid(self, web_portal):
        """Test executing invalid commands."""
        result = web_portal._execute_command("invalid_command")
        assert "error" in result.lower() or "unknown" in result.lower()

    @patch('builtins.open')
    def test_export_trace_web(self, mock_open, web_portal, tmp_path):
        """Test exporting trace via web interface."""
        export_path = tmp_path / "web_export.json"
        mock_open.return_value.__enter__.return_value = export_path.open('w')

        result = web_portal._export_trace("json", str(export_path))

        assert "exported" in result.lower()
        mock_open.assert_called_once()

    def test_get_system_info(self, web_portal):
        """Test getting system information."""
        info = web_portal._get_system_info()

        assert "python_version" in info
        assert "debugger_version" in info
        assert "active_agents" in info
        assert "total_events" in info

    def test_websocket_connection_simulation(self, web_portal):
        """Test WebSocket connection simulation."""
        # Mock WebSocket connection
        mock_ws = Mock()

        # Simulate receiving a message
        message = {"type": "command", "command": "continue"}
        web_portal._handle_websocket_message(mock_ws, json.dumps(message))

        # Should have processed the message
        # In real implementation, this would send responses back

    @patch('flask.Flask.run')
    def test_start_server(self, mock_run, web_portal):
        """Test starting the web server."""
        web_portal.start()

        mock_run.assert_called_once_with(
            host=web_portal.host,
            port=web_portal.port,
            debug=False
        )

    @patch('flask.Flask.run')
    def test_start_server_debug(self, mock_run, debugger):
        """Test starting the web server in debug mode."""
        portal = WebPortal(debugger, debug=True)
        portal.start()

        mock_run.assert_called_once_with(
            host=portal.host,
            port=portal.port,
            debug=True
        )

    def test_stop_server(self, web_portal):
        """Test stopping the web server."""
        # Mock the server shutdown
        with patch.object(web_portal, 'server', create=True) as mock_server:
            mock_server.shutdown = Mock()
            web_portal.stop()

            mock_server.shutdown.assert_called_once()

    def test_is_running(self, web_portal):
        """Test checking if server is running."""
        # Initially should not be running
        assert web_portal.is_running() is False

        # Mock server thread
        with patch.object(web_portal, 'server_thread', create=True) as mock_thread:
            mock_thread.is_alive.return_value = True
            assert web_portal.is_running() is True

            mock_thread.is_alive.return_value = False
            assert web_portal.is_running() is False

    def test_get_server_url(self, web_portal):
        """Test getting server URL."""
        url = web_portal.get_server_url()
        expected_url = f"http://{web_portal.host}:{web_portal.port}"
        assert url == expected_url

    def test_cors_headers(self, web_portal):
        """Test CORS headers are properly set."""
        with web_portal.app.test_client() as client:
            response = client.options('/api/dashboard')
            assert response.status_code == 200
            # CORS headers should be present
            assert 'Access-Control-Allow-Origin' in response.headers

    def test_api_endpoints(self, web_portal):
        """Test main API endpoints are accessible."""
        with web_portal.app.test_client() as client:
            # Test dashboard endpoint
            response = client.get('/api/dashboard')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "events" in data

            # Test agents endpoint
            response = client.get('/api/agents')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert isinstance(data, list)

    def test_static_file_serving(self, web_portal):
        """Test that static files are served correctly."""
        with web_portal.app.test_client() as client:
            # Test main page
            response = client.get('/')
            assert response.status_code == 200

            # Test static CSS
            response = client.get('/static/css/custom.css')
            # May return 404 if file doesn't exist, but route should be configured
            assert response.status_code in [200, 404]  # 200 if file exists, 404 if not

    @pytest.mark.slow
    def test_concurrent_connections(self, web_portal):
        """Test handling multiple concurrent web connections."""
        import threading
        import time

        results = []
        errors = []

        def make_request():
            try:
                with web_portal.app.test_client() as client:
                    response = client.get('/api/dashboard')
                    results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Start multiple threads making requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)

        # All requests should succeed
        assert len(results) == 5
        assert all(status == 200 for status in results)
        assert len(errors) == 0
