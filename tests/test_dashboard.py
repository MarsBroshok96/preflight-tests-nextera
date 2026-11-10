import io
import json
import unittest
from datetime import datetime
from wsgiref.validate import validator

from app import CHECKS, STATUSES, application


class DashboardTests(unittest.TestCase):
    def request(self, path, query=""):
        result = {}

        def start_response(status, headers, exc_info=None):
            result["status"] = status
            result["headers"] = dict(headers)

        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": path,
            "SCRIPT_NAME": "",
            "QUERY_STRING": query,
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "8000",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(),
            "wsgi.errors": io.StringIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "CONTENT_TYPE": "",
            "CONTENT_LENGTH": "",
        }
        chunks = validator(application)(environ, start_response)
        result["body"] = b"".join(chunks).decode("utf-8")
        if hasattr(chunks, "close"):
            chunks.close()
        return result

    def test_health(self):
        response = self.request("/health")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(json.loads(response["body"]), {"status": "ok"})

    def test_checks_have_observation_date_and_defects(self):
        response = self.request("/api/checks")
        self.assertEqual(response["status"], "200 OK")
        self.assertIn("application/json", response["headers"]["Content-Type"])
        checks = json.loads(response["body"])
        self.assertEqual(len(checks), len(CHECKS))
        self.assertTrue(any(check["defect"] for check in checks))
        for check in checks:
            self.assertIn(check["status"], STATUSES)
            self.assertTrue(check["description"])
            self.assertTrue(check["component"])
            observed = datetime.fromisoformat(check["observed_at"])
            self.assertIsNotNone(observed.tzinfo)

    def test_every_named_status_is_valid_and_filters(self):
        for status in STATUSES:
            with self.subTest(status=status):
                response = self.request("/api/checks", f"status={status}")
                self.assertEqual(response["status"], "200 OK")
                checks = json.loads(response["body"])
                self.assertEqual(checks, [c for c in CHECKS if c["status"] == status])

    def test_unknown_status_returns_400(self):
        for status in ("UNKNOWNN", "working", "", "WORKING%20"):
            with self.subTest(status=status):
                response = self.request("/api/checks", f"status={status}")
                self.assertEqual(response["status"], "400 Bad Request")
                self.assertIn("error", json.loads(response["body"]))

    def test_dashboard_has_table_date_description_defects_and_filter(self):
        response = self.request("/")
        self.assertEqual(response["status"], "200 OK")
        self.assertIn("text/html", response["headers"]["Content-Type"])
        for expected in ("Nextera Platform Health Dashboard", "<table", "Дата", "Описание", "Дефект", "status", "<form"):
            self.assertIn(expected, response["body"])
        for status in STATUSES:
            self.assertIn(f'value="{status}"', response["body"])
        for check in CHECKS:
            self.assertIn(check["description"], response["body"])

    def test_dashboard_filter_and_unknown_status(self):
        response = self.request("/", "status=BROKEN")
        self.assertEqual(response["status"], "200 OK")
        self.assertIn('value="BROKEN" selected', response["body"])
        for check in CHECKS:
            if check["status"] == "BROKEN":
                self.assertIn(check["description"], response["body"])
            else:
                self.assertNotIn(check["description"], response["body"])
        self.assertEqual(self.request("/", "status=INVALID")["status"], "400 Bad Request")

    def test_unknown_route_and_post_do_not_succeed(self):
        self.assertEqual(self.request("/missing")["status"], "404 Not Found")
        result = {}
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/health", "QUERY_STRING": ""}
        application(environ, lambda status, headers: result.update(status=status))
        self.assertEqual(result["status"], "405 Method Not Allowed")


if __name__ == "__main__":
    unittest.main()
