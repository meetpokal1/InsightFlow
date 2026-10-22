from dataclasses import replace

from sqlalchemy.engine import make_url

from src.config import get_settings


def test_special_characters_in_the_password_are_escaped_in_the_url():
    settings = replace(get_settings(), database_url_override=None, db_password="p@ss/word#1")
    rendered = settings.database_url.render_as_string(hide_password=False)
    assert "p@ss/word#1" not in rendered
    assert make_url(rendered).password == "p@ss/word#1"


def test_a_full_database_url_overrides_the_separate_settings():
    url = "postgresql+psycopg2://someone:secret@db.example:5433/other"
    settings = replace(get_settings(), database_url_override=url)
    assert settings.database_url == url
