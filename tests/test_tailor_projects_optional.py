from __future__ import annotations

from applypilot.scoring.tailor import assemble_resume_text
from applypilot.scoring.validator import validate_json_fields, validate_tailored_resume


def _profile() -> dict:
    return {
        "personal": {
            "full_name": "Test User",
            "email": "test@example.com",
            "phone": "555-0100",
        },
        "resume_facts": {
            "preserved_companies": ["Example Co"],
            "preserved_projects": [],
            "preserved_school": "State University",
        },
        "skills_boundary": {
            "languages": ["Python", "JavaScript"],
        },
    }


def test_validate_json_fields_allows_missing_projects_key() -> None:
    data = {
        "title": "Software Engineer",
        "summary": "Backend-focused engineer.",
        "skills": {"Languages": "Python, JavaScript"},
        "experience": [
            {"header": "Engineer at Example Co", "bullets": ["Built APIs"]},
        ],
        "education": "State University | BS",
    }

    result = validate_json_fields(data, _profile(), mode="lenient")

    assert result["passed"] is True
    assert result["errors"] == []


def test_assemble_resume_text_omits_projects_section_when_absent() -> None:
    data = {
        "title": "Software Engineer",
        "summary": "Backend-focused engineer.",
        "skills": {"Languages": "Python, JavaScript"},
        "experience": [
            {"header": "Engineer at Example Co", "bullets": ["Built APIs"]},
        ],
        "education": "State University | BS",
    }

    text = assemble_resume_text(data, _profile())

    assert "\nPROJECTS\n" not in text
    assert "\nEDUCATION\n" in text


def test_validate_tailored_resume_allows_missing_projects_section() -> None:
    text = """Test User
Software Engineer
test@example.com | 555-0100

SUMMARY
Backend-focused engineer.

TECHNICAL SKILLS
Languages: Python, JavaScript

EXPERIENCE
Engineer at Example Co
- Built APIs

EDUCATION
State University | BS
"""

    result = validate_tailored_resume(text, _profile())

    assert result["passed"] is True
    assert not any("PROJECTS" in error for error in result["errors"])
