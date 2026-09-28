import copy
import json
from pathlib import Path

from django.test import SimpleTestCase
from requests import Response

from integrations.jolpica.client import JolpicaClient
from integrations.jolpica.errors import (
    JolpicaInvalidPayload,
    JolpicaRateLimited,
    JolpicaUnavailable,
)


FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def response(payload: dict | str, status: int = 200, **headers: str) -> Response:
    result = Response()
    result.status_code = status
    result.headers.update(headers)
    result.url = "https://api.jolpi.ca/ergast/f1/test.json"
    if isinstance(payload, str):
        result._content = payload.encode("utf-8")
    else:
        result._content = json.dumps(payload).encode("utf-8")
        result.headers["Content-Type"] = "application/json"
    return result


class RecordingSession:
    def __init__(self, responses: list[Response]):
        self.responses = list(responses)
        self.headers: dict[str, str] = {}
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs) -> Response:
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class JolpicaClientTests(SimpleTestCase):
    def test_schedule_uses_user_agent_timeout_and_all_pages(self):
        first = fixture("schedule.json")
        first["MRData"].update({"limit": "1", "offset": "0", "total": "2"})
        second = copy.deepcopy(first)
        second["MRData"].update({"offset": "1"})
        race = second["MRData"]["RaceTable"]["Races"][0]
        race.update({"round": "2", "raceName": "Japanese Grand Prix"})
        race["Circuit"].update(
            {"circuitId": "suzuka", "circuitName": "Suzuka Circuit"}
        )
        recording_session = RecordingSession([response(first), response(second)])
        client = JolpicaClient(
            "https://api.jolpi.ca/ergast/f1",
            "ApexGrid/1.0",
            (3.05, 10.0),
            session=recording_session,
        )

        events = client.get_schedule(2026)

        self.assertEqual([event.round_number for event in events], [1, 2])
        self.assertEqual(recording_session.headers["User-Agent"], "ApexGrid/1.0")
        self.assertEqual(
            [call[1]["params"]["offset"] for call in recording_session.calls],
            [0, 1],
        )
        self.assertTrue(
            all(call[1]["timeout"] == (3.05, 10.0) for call in recording_session.calls)
        )

    def test_transient_server_error_is_retried_twice_then_succeeds(self):
        recording_session = RecordingSession(
            [response({}, 503), response({}, 502), response(fixture("schedule.json"))]
        )
        sleeps: list[float] = []
        client = JolpicaClient(
            "https://api.jolpi.ca/ergast/f1",
            "ApexGrid/1.0",
            (3.05, 10.0),
            session=recording_session,
            sleep=sleeps.append,
        )

        events = client.get_schedule(2026)

        self.assertEqual(len(events), 1)
        self.assertEqual(len(recording_session.calls), 3)
        self.assertEqual(sleeps, [0.25, 0.5])

    def test_retry_after_is_honored_but_capped(self):
        recording_session = RecordingSession(
            [
                response({}, 429, **{"Retry-After": "999"}),
                response(fixture("schedule.json")),
            ]
        )
        sleeps: list[float] = []
        client = JolpicaClient(
            "https://api.jolpi.ca/ergast/f1",
            "ApexGrid/1.0",
            (3.05, 10.0),
            session=recording_session,
            sleep=sleeps.append,
        )

        client.get_schedule(2026)

        self.assertEqual(sleeps, [2.0])

    def test_exhausted_failures_expose_only_adapter_errors(self):
        unavailable = JolpicaClient(
            "https://api.jolpi.ca/ergast/f1",
            "ApexGrid/1.0",
            (3.05, 10.0),
            session=RecordingSession([response({}, 503)] * 3),
            sleep=lambda _: None,
        )
        limited = JolpicaClient(
            "https://api.jolpi.ca/ergast/f1",
            "ApexGrid/1.0",
            (3.05, 10.0),
            session=RecordingSession([response({}, 429)] * 3),
            sleep=lambda _: None,
        )

        with self.assertRaises(JolpicaUnavailable):
            unavailable.get_schedule(2026)
        with self.assertRaises(JolpicaRateLimited):
            limited.get_schedule(2026)

    def test_invalid_json_becomes_invalid_payload(self):
        client = JolpicaClient(
            "https://api.jolpi.ca/ergast/f1",
            "ApexGrid/1.0",
            (3.05, 10.0),
            session=RecordingSession([response("not-json")]),
        )

        with self.assertRaises(JolpicaInvalidPayload):
            client.get_schedule(2026)
