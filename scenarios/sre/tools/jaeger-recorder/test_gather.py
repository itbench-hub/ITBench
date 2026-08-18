import json
import os
import sys
import tempfile
import unittest

from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))
import gather


def make_response(status_code, body):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = body
    return mock


class TestGetServices(unittest.TestCase):

    def test_returns_services_on_200(self):
        session = MagicMock()
        session.get.return_value = make_response(200, {"services": ["svc-a", "svc-b"]})
        result = gather.get_services(session, "http://jaeger", {})
        self.assertEqual(result, ["svc-a", "svc-b"])

    def test_returns_empty_on_non_200(self):
        session = MagicMock()
        session.get.return_value = make_response(500, {})
        result = gather.get_services(session, "http://jaeger", {})
        self.assertEqual(result, [])


class TestGetOperations(unittest.TestCase):

    def test_returns_operations_on_200(self):
        session = MagicMock()
        session.get.return_value = make_response(200, {"operations": [{"name": "GET /foo"}]})
        result = gather.get_operations(session, "http://jaeger", {}, "svc-a")
        self.assertEqual(result, [{"name": "GET /foo"}])

    def test_returns_empty_on_non_200(self):
        session = MagicMock()
        session.get.return_value = make_response(404, {})
        result = gather.get_operations(session, "http://jaeger", {}, "svc-a")
        self.assertEqual(result, [])


class TestGetTraces(unittest.TestCase):

    def test_returns_spans_on_200(self):
        session = MagicMock()
        spans = [{"spanId": "abc"}]
        session.get.return_value = make_response(200, {"result": {"resourceSpans": spans}})
        result = gather.get_traces(session, "http://jaeger", {}, "svc-a", {"name": "GET /foo"}, ("t0", "t1"))
        self.assertEqual(result, spans)

    def test_returns_empty_when_operation_has_no_name(self):
        session = MagicMock()
        result = gather.get_traces(session, "http://jaeger", {}, "svc-a", {}, ("t0", "t1"))
        self.assertEqual(result, [])
        session.get.assert_not_called()

    def test_returns_empty_on_non_200(self):
        session = MagicMock()
        session.get.return_value = make_response(500, {})
        result = gather.get_traces(session, "http://jaeger", {}, "svc-a", {"name": "GET /foo"}, ("t0", "t1"))
        self.assertEqual(result, [])


class TestMain(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _run_main(self, endpoint, side_effects):
        with patch.dict(os.environ, {"JAEGER_ENDPOINT": endpoint}), \
             patch("gather.get_services", side_effect=side_effects[0]), \
             patch("gather.get_operations", side_effect=side_effects[1]), \
             patch("gather.get_traces", side_effect=side_effects[2]), \
             patch("os.path.expanduser", return_value=self.tmpdir):
            os.makedirs(os.path.join(self.tmpdir, "records"), exist_ok=True)
            gather.main()

    def test_writes_file_when_traces_found(self):
        spans = [{"spanId": "abc"}]
        self._run_main(
            "http://jaeger",
            [lambda *a, **kw: ["svc-a"],
             lambda *a, **kw: [{"name": "GET /foo"}],
             lambda *a, **kw: spans]
        )
        files = os.listdir(os.path.join(self.tmpdir, "records"))
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith("traces_at_"))

    def test_no_file_written_when_no_traces(self):
        self._run_main(
            "http://jaeger",
            [lambda *a, **kw: ["svc-a"],
             lambda *a, **kw: [{"name": "GET /foo"}],
             lambda *a, **kw: []]
        )
        files = os.listdir(os.path.join(self.tmpdir, "records"))
        self.assertEqual(len(files), 0)

    def test_exits_when_endpoint_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("JAEGER_ENDPOINT", None)
            with self.assertRaises(SystemExit):
                gather.main()


if __name__ == "__main__":
    unittest.main()
