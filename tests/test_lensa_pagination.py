from __future__ import annotations

import json

import applypilot.discovery.smartextract as smartextract


def _job(idx: int) -> dict:
    return {
        "title": {"cleaned_title": f"Job {idx}"},
        "location": {"display_name": "Remote"},
        "description": f"Description {idx}",
        "predicted_salary": {"display_value": f"${idx}"},
        "apply_url": f"/jobs/{idx}",
    }


def test_paginate_lensa_more_jobs_merges_multiple_pages(monkeypatch) -> None:
    api_response = {
        "url": "https://lensa.com/jlp/api/more-jobs",
        "_request_post_data": json.dumps(
            {
                "searchParams": {
                    "location": None,
                    "position": ["VP of Information Technology"],
                    "remote_jobs": "only",
                },
                "limit": 20,
            }
        ),
        "_raw_data": {
            "total": 45,
            "searchParamsForPaging": {
                "location": None,
                "position": ["VP of Information Technology"],
                "remote_jobs": "only",
                "apiStates": {"rnd": {"limit": 20, "items": 20, "offset": 20, "total": 45}},
            },
            "standardRecommendedJobs": [_job(i) for i in range(20)],
        },
    }
    requested_bodies: list[dict] = []

    class _Resp:
        def __init__(self, payload: dict):
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self.payload

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url: str, json: dict):
            requested_bodies.append(json)
            offset = json["searchParams"]["apiStates"]["rnd"]["offset"]
            if offset == 20:
                return _Resp(
                    {
                        "total": 45,
                        "searchParamsForPaging": {
                            "location": None,
                            "position": ["VP of Information Technology"],
                            "remote_jobs": "only",
                            "apiStates": {"rnd": {"limit": 20, "items": 20, "offset": 40, "total": 45}},
                        },
                        "standardRecommendedJobs": [_job(i) for i in range(20, 40)],
                    }
                )
            if offset == 40:
                return _Resp(
                    {
                        "total": 45,
                        "searchParamsForPaging": {
                            "location": None,
                            "position": ["VP of Information Technology"],
                            "remote_jobs": "only",
                            "apiStates": {"rnd": {"limit": 20, "items": 5, "offset": 45, "total": 45}},
                        },
                        "standardRecommendedJobs": [_job(i) for i in range(40, 45)],
                    }
                )
            raise AssertionError(f"unexpected offset {offset}")

    monkeypatch.setattr(smartextract.httpx, "Client", lambda **kwargs: _Client())

    merged = smartextract._paginate_lensa_more_jobs_response(api_response, "https://lensa.com/talent/job-opportunities")

    assert len(merged["standardRecommendedJobs"]) == 45
    assert requested_bodies[0]["searchParams"]["apiStates"]["rnd"]["offset"] == 20
    assert requested_bodies[1]["searchParams"]["apiStates"]["rnd"]["offset"] == 40


def test_execute_api_response_uses_paginated_lensa_payload(monkeypatch) -> None:
    intel = {
        "url": "https://lensa.com/talent/job-opportunities?job-title=VP+of+Information+Technology&remote_jobs=only",
        "api_responses": [
            {
                "url": "https://lensa.com/jlp/api/more-jobs",
                "_raw_data": {"standardRecommendedJobs": [_job(0)]},
                "_request_post_data": '{"searchParams":{"position":["VP of Information Technology"]},"limit":20}',
            }
        ],
    }
    plan = {
        "extraction": {
            "url_pattern": "/jlp/api/more-jobs",
            "items_path": "standardRecommendedJobs",
            "title": "title.cleaned_title",
            "salary": "predicted_salary.display_value",
            "description": "description",
            "location": "location.display_name",
            "url": "apply_url",
        }
    }

    monkeypatch.setattr(
        smartextract,
        "_paginate_lensa_more_jobs_response",
        lambda resp, page_url, max_pages=10: {"standardRecommendedJobs": [_job(i) for i in range(25)]},
    )

    jobs = smartextract.execute_api_response(intel, plan)

    assert len(jobs) == 25
    assert jobs[0]["title"] == "Job 0"
