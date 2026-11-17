from app.cleaning import parse_cities, parse_experience, parse_salary, split_skills


def test_parse_salary_range():
    assert parse_salary("₹ 2,00,000 - 3,50,000") == (200000, 350000)


def test_parse_salary_missing():
    assert parse_salary("Not Mentioned") == (None, None)


def test_parse_experience():
    assert parse_experience("1 year(s)") == 1
    assert parse_experience("0 year(s)") == 0
    assert parse_experience("Not Found") is None


def test_split_skills_separates_perks():
    skills, perks = split_skills("Python, SQL, Informal dress code, Health Insurance, Python")
    assert skills == ["Python", "SQL"]
    assert perks == ["Informal dress code", "Health Insurance"]


def test_parse_cities_hybrid_and_aliases():
    assert parse_cities("Delhi, Bangalore (Hybrid)") == (["Delhi", "Bengaluru"], True)
    assert parse_cities("Not Found") == ([], False)
