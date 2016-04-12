## Movie picker Flask application

This code is used to demonstrate how to build a Flask application.

Here are the commits / branches that represent different periods of development:

| Commit ID<br>or branch | Compare to<br>previous version | Description |
| --- | --- | --- |
| [5e984ac](https://github.com/lost-theory/moviepicker/blob/5e984ac/movies.py) | n/a | The original movie picker command line code. |
| [solved5](https://github.com/lost-theory/moviepicker/tree/solved5) | [Compare](https://github.com/lost-theory/moviepicker/compare/5e984ac...solved5?diff=split) | Basic Flask application that builds on top of the existing command line program. No database or persistence, just read-only data pulled on the fly from Wikipedia (movie categories), OMDbAPI.com (movie data), and IMDb (poster images). Uses a Bootstrap theme. |
| [solved6](https://github.com/lost-theory/moviepicker/tree/solved6) | [Compare](https://github.com/lost-theory/moviepicker/compare/solved5...solved6?diff=split) | Adds a sqlite database, models (categories, users, and lists of movies per user), login & registration, secure handling of passwords with [passlib](https://pythonhosted.org/passlib/), and AJAX calls. |
| [flask_sqlalchemy](https://github.com/lost-theory/moviepicker/tree/flask_sqlalchemy) | [Compare](https://github.com/lost-theory/moviepicker/compare/solved6...flask_sqlalchemy?diff=split) | Adds the Flask-SQLAlchemy extension, replacing the hand-rolled sqlite code. Application code was pretty much unchanged (just renaming methods). Templates only required one line of changes |
| [comments](https://github.com/lost-theory/moviepicker/tree/comments) | [Compare](https://github.com/lost-theory/moviepicker/compare/flask_sqlalchemy...comments?diff=split) | Adds a username to the User model. Replaces the one-to-many User -> Movies relation with a many-to-many relation, removing the need for duplicate Movie rows. Now that each Movie has a unique movie_id, add a Comment model that lets users leave comments on each movie via the movie details page. |
| [class_view_and_blueprint](https://github.com/lost-theory/moviepicker/tree/class_view_and_blueprint) | [Compare](https://github.com/lost-theory/moviepicker/compare/comments...class_view_and_blueprint?diff=split) | Adds Flask-Admin, a `login_required` view decorator, `before_request` and `context_processor` functions, a class based view for implement some API endpoints for converting models to JSON, and a blueprint for containing that API functionality. |
