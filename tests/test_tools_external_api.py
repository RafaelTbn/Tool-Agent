"""Unit tests for external API tool behavior."""

import unittest

from src.tools.external_api_tool import ExternalAPITool


class ExternalAPIToolTests(unittest.TestCase):
    class _FakeResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

        def json(self):
            return self._payload

    class _FakeRequester:
        def __init__(self, responses):
            self._responses = responses

        def get(self, url, params=None, timeout=None):
            if "geocoding-api" in url:
                payload = self._responses["geocode"]
            else:
                payload = self._responses["forecast"]
            if isinstance(payload, Exception):
                raise payload
            return ExternalAPIToolTests._FakeResponse(payload)

    def test_tools_external_api_success(self) -> None:
        tool = ExternalAPITool(
            requester=self._FakeRequester(
                {
                    "geocode": {
                        "results": [
                            {
                                "name": "Jakarta",
                                "country": "Indonesia",
                                "latitude": -6.175,
                                "longitude": 106.827,
                            }
                        ]
                    },
                    "forecast": {
                        "current": {
                            "temperature_2m": 31.2,
                            "apparent_temperature": 35.0,
                            "relative_humidity_2m": 74,
                            "weather_code": 2,
                            "wind_speed_10m": 12.4,
                        }
                    },
                }
            )
        )
        result = tool.run({"query": "cuaca hari ini di jakarta"})
        self.assertEqual(result["status"], "ok")
        self.assertIn("Jakarta", result["message"])
        self.assertEqual(result["data"]["condition"], "Partly cloudy")

    def test_tools_external_api_prefers_exact_city_match_over_related_area(self) -> None:
        tool = ExternalAPITool(
            requester=self._FakeRequester(
                {
                    "geocode": {
                        "results": [
                            {
                                "name": "Sunda Kelapa",
                                "country": "Indonesia",
                                "admin1": "Jakarta",
                                "feature_code": "PPL",
                                "latitude": -6.12,
                                "longitude": 106.81,
                                "population": 5000,
                            },
                            {
                                "name": "Jakarta",
                                "country": "Indonesia",
                                "admin1": "Jakarta",
                                "feature_code": "PPLA",
                                "latitude": -6.175,
                                "longitude": 106.827,
                                "population": 10562088,
                            },
                        ]
                    },
                    "forecast": {
                        "current": {
                            "temperature_2m": 31.2,
                            "apparent_temperature": 35.0,
                            "relative_humidity_2m": 74,
                            "weather_code": 2,
                            "wind_speed_10m": 12.4,
                        }
                    },
                }
            )
        )
        result = tool.run({"query": "cuaca di jakarta"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["city"], "Jakarta")

    def test_tools_external_api_city_only_query_still_handles_ambiguous_location_names(self) -> None:
        tool = ExternalAPITool(
            requester=self._FakeRequester(
                {
                    "geocode": {
                        "results": [
                            {
                                "name": "Doloksanggul",
                                "country": "Indonesia",
                                "admin1": "North Sumatra",
                                "admin2": "Kabupaten Serdang Bedagai",
                                "feature_code": "PPL",
                                "latitude": 3.3219,
                                "longitude": 99.0904,
                                "population": 1200,
                            },
                            {
                                "name": "Doloksanggul",
                                "country": "Indonesia",
                                "admin1": "North Sumatra",
                                "admin2": "Kabupaten Humbang Hasundutan",
                                "feature_code": "PPLA4",
                                "latitude": 2.2654,
                                "longitude": 98.7528,
                                "population": 15000,
                            },
                        ]
                    },
                    "forecast": {
                        "current": {
                            "temperature_2m": 22.4,
                            "apparent_temperature": 23.1,
                            "relative_humidity_2m": 88,
                            "weather_code": 61,
                            "wind_speed_10m": 5.6,
                        }
                    },
                }
            )
        )
        result = tool.run({"query": "cuaca di Doloksanggul"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["city"], "Doloksanggul")
        self.assertEqual(result["data"]["latitude"], 2.2654)

    def test_tools_external_api_rejects_non_weather_queries_safely(self) -> None:
        tool = ExternalAPITool(requester=self._FakeRequester({"geocode": {}, "forecast": {}}))
        result = tool.run({"query": "system latency external service"})
        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["error"], "unsupported_external_query")
        self.assertIn("weather queries only", result["message"].lower())

    def test_tools_external_api_failure_with_retry_fallback(self) -> None:
        events = []
        tool = ExternalAPITool(
            logger=lambda e, p: events.append((e, p)),
            requester=self._FakeRequester({"geocode": ConnectionError("boom"), "forecast": {}}),
        )
        result = tool.run(
            {
                "query": "cuaca di jakarta",
                "max_retries": 2,
            }
        )
        self.assertEqual(result["status"], "fallback")
        retry_events = [entry for entry in events if entry[0] == "retry_attempt"]
        self.assertEqual(len(retry_events), 2)

    def test_tools_external_api_timeout_fallback(self) -> None:
        class SlowRequester:
            def get(self, url, params=None, timeout=None):
                import time

                if "geocoding-api" in url:
                    return ExternalAPIToolTests._FakeResponse(
                        {
                            "results": [
                                {
                                    "name": "Jakarta",
                                    "country": "Indonesia",
                                    "latitude": -6.175,
                                    "longitude": 106.827,
                                }
                            ]
                        }
                    )

                time.sleep(0.01)
                return ExternalAPIToolTests._FakeResponse(
                    {
                        "current": {
                            "temperature_2m": 30,
                            "apparent_temperature": 33,
                            "relative_humidity_2m": 70,
                            "weather_code": 1,
                            "wind_speed_10m": 10,
                        }
                    }
                )

        tool = ExternalAPITool(requester=SlowRequester())
        result = tool.run(
            {
                "query": "cuaca di jakarta",
                "timeout_seconds": 0.001,
                "max_retries": 0,
            }
        )
        self.assertEqual(result["status"], "fallback")
        self.assertIn("timed out", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
