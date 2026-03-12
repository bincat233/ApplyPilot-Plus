from __future__ import annotations

from applypilot.scoring import tailor


def _profile() -> dict:
    return {
        "personal": {"full_name": "Test User"},
        "resume_facts": {
            "preserved_companies": ["Example Co"],
            "preserved_projects": [],
            "preserved_school": "State University",
            "real_metrics": [],
        },
        "skills_boundary": {"languages": ["Python"]},
        "experience": {"education_level": "BS"},
    }


def test_tailor_resume_returns_parsed_json_but_omits_it_from_report(monkeypatch) -> None:
    parsed = {
        "title": "Software Engineer",
        "summary": "Practical engineer.",
        "skills": {"Languages": "Python"},
        "experience": [{"title": "Engineer", "company_dates": "Example Co | 2022-Present", "bullets": ["Built APIs"]}],
        "education": "State University | BS",
    }

    class FakeClient:
        @staticmethod
        def chat(messages, max_output_tokens=16000):
            _ = messages, max_output_tokens
            return '{"title":"Software Engineer","summary":"Practical engineer.","skills":{"Languages":"Python"},"experience":[{"title":"Engineer","company_dates":"Example Co | 2022-Present","bullets":["Built APIs"]}],"education":"State University | BS"}'

    monkeypatch.setattr(tailor, "get_client", lambda: FakeClient())
    monkeypatch.setattr(tailor, "extract_json", lambda raw: parsed)
    monkeypatch.setattr(
        tailor,
        "validate_json_fields",
        lambda data, profile, mode="normal": {
            "passed": False,
            "errors": ["Company 'Example Co' missing from experience"],
            "warnings": [],
        },
    )

    tailored_text, report, parsed_json = tailor.tailor_resume(
        resume_text="Base resume",
        job={"title": "Software Engineer", "site": "Example", "full_description": "Build APIs"},
        profile=_profile(),
        max_retries=0,
        validation_mode="normal",
    )

    assert parsed_json == parsed
    assert "parsed_data" not in report
    assert report["status"] == "failed_validation"
    assert "Example Co" in tailored_text
