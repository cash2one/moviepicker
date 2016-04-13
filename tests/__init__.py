'''
To run tests:

$ ~/mp_app_env/bin/python runtests.py
$ ~/mp_app_env/bin/python runtests.py --coverage
'''

import os
import unittest

os.environ['DBURI'] = "sqlite://" #empty URL means using an in-memory DB

from mock import patch, mock_open

from app import app, db
from app import User
from movies import fetch_wikipedia_titles

class AppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        with app.app_context():
            db.create_all()
        self.client = app.test_client()

## non-app tests ##############################################################

class MoviePickerTests(unittest.TestCase):
    urlopen = mock_open(read_data='{"query": {"categorymembers": [{"title": "Up"}]}}')

    @patch("urllib.urlopen", urlopen)
    def test_fetch_wikipedia_titles(self):
        titles = fetch_wikipedia_titles("Pixar_animated_films")
        assert len(self.urlopen.mock_calls) == 2
        assert "https://en.wikipedia.org/" in str(self.urlopen.mock_calls[0])
        assert "Pixar_animated_films" in str(self.urlopen.mock_calls[0])
        assert "read()" in str(self.urlopen.mock_calls[1])
        assert len(titles) == 1
        assert titles[0] == 'Up'

## app tests ##################################################################

class ViewTests(AppTestCase):
    def test_index_logged_out(self):
        res = self.client.get('/')
        assert res.status == '200 OK'
        assert "<strong>Register</strong> or <strong>Log in</strong>" in res.data

    def test_add_cat_logged_out_redirect(self):
        res = self.client.get('/categories')
        assert res.status == '302 FOUND'
        assert '/login' in res.headers['Location']

class ModelTests(AppTestCase):
    def test_user_create(self):
        with app.app_context():
            u = User.create("test", "test@wow.com", "asdfasdf", "asdfasdf")
            assert u.username == "test"
            assert u.email == "test@wow.com"
            assert u.password_hash != "asdfasdf"