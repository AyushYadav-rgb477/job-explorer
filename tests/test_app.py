import io

import pytest
from docx import Document

from app import create_app


def make_docx(text: str) -> io.BytesIO:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


@pytest.mark.parametrize("path", ["/", "/jobs", "/insights", "/login", "/signup", "/healthz",
                                  "/jobs?q=python&city=Delhi&page=2", "/jobs?skill=Python&min_salary=300000"])
def test_pages_load(client, path):
    assert client.get(path).status_code == 200


def test_insights_api(client):
    data = client.get("/api/insights").get_json()
    assert data["totals"]["jobs"] > 5000
    assert len(data["top_skills"]["labels"]) == 15
    assert data["salary_by_experience"]["values"]
    assert "Informal dress code" not in data["top_skills"]["labels"]  # perks aren't skills


def test_match_ranks_relevant_jobs(client):
    cv = make_docx("Python developer. Skills: Python, Django, SQL, Machine Learning, Data Analytics.")
    res = client.post("/api/match", data={"cv": (cv, "cv.docx")}, content_type="multipart/form-data")
    assert res.status_code == 200
    data = res.get_json()
    assert "Python" in data["cv_skills"]
    assert len(data["matches"]) == 10
    assert any("python" in m["title"].lower() or "data" in m["title"].lower() for m in data["matches"][:3])
    assert data["matches"][0]["score"] >= data["matches"][-1]["score"]
    assert data["saved"] is False  # not logged in


def test_match_rejects_bad_files(client):
    res = client.post("/api/match", data={"cv": (io.BytesIO(b"hi"), "cv.txt")},
                      content_type="multipart/form-data")
    assert res.status_code == 400
    res = client.post("/api/match", data={"cv": (io.BytesIO(b"not a pdf"), "cv.pdf")},
                      content_type="multipart/form-data")
    assert res.status_code == 400
    assert client.post("/api/match").status_code == 400


def test_history_requires_login(client):
    res = client.get("/history")
    assert res.status_code == 302 and "/login" in res.headers["Location"]


def test_csrf_blocks_post_without_token():
    app = create_app({"TESTING": True, "SECRET_KEY": "test"})
    res = app.test_client().post("/logout")
    assert res.status_code == 400


def test_unknown_page_is_404(client):
    assert client.get("/nope").status_code == 404
