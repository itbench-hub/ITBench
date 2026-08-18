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


class TestMain(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, "records"), exist_ok=True)

    def _run_main(self, endpoint, responses_by_item, annotation=""):
        env = {"KUBERNETES_TOPOLOGY_MONITOR_ENDPOINT": endpoint}
        if annotation:
            env["FILENAME_ANNOTATION"] = annotation

        session_mock = MagicMock()
        session_mock.get.side_effect = lambda url, **kw: responses_by_item[url.split("/")[-1]]

        with patch.dict(os.environ, env), \
             patch("requests.Session", return_value=session_mock), \
             patch("os.path.expanduser", return_value=self.tmpdir):
            gather.main()

        return session_mock

    def test_writes_file_for_each_successful_item(self):
        responses = {item: make_response(200, {"data": item}) for item in ["nodes", "edges", "graph", "events"]}
        self._run_main("http://topology", responses)

        files = os.listdir(os.path.join(self.tmpdir, "records"))
        self.assertEqual(len(files), 4)
        items = {f.split("__")[0] for f in files}
        self.assertEqual(items, {"nodes", "edges", "graph", "events"})

    def test_skips_item_on_non_200(self):
        responses = {item: make_response(200, {"data": item}) for item in ["nodes", "edges", "graph", "events"]}
        responses["nodes"] = make_response(500, {})
        self._run_main("http://topology", responses)

        files = os.listdir(os.path.join(self.tmpdir, "records"))
        self.assertEqual(len(files), 3)
        self.assertFalse(any(f.startswith("nodes") for f in files))

    def test_filename_annotation_prefixed(self):
        responses = {item: make_response(200, {}) for item in ["nodes", "edges", "graph", "events"]}
        self._run_main("http://topology", responses, annotation="init")

        files = os.listdir(os.path.join(self.tmpdir, "records"))
        self.assertTrue(all(f.startswith("init__") for f in files))

    def test_exits_when_endpoint_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("KUBERNETES_TOPOLOGY_MONITOR_ENDPOINT", None)
            with self.assertRaises(SystemExit):
                gather.main()


if __name__ == "__main__":
    unittest.main()
