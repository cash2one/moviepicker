'''
Movie picker flask application.
'''

import logging
import os
import random
import urllib
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, g, request, url_for, session,
    render_template, redirect,
)
from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView

from movies import (
    MovieData,
    fetch_wikipedia_titles, fetch_omdb_info, is_valid_category,
)
from models import db, User, Category, Movie, Comment
from api import api

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DBURI', 'sqlite:///movies.db')
app.config['SQLALCHEMY_ECHO'] = bool(os.environ.get('ECHO'))
db.init_app(app)

# http://flask.pocoo.org/docs/0.10/errorhandling/
logging.basicConfig(level=logging.INFO)

if os.environ.get('SECRET_KEY_PATH'):
    with open(os.environ['SECRET_KEY_PATH']) as f:
        app.secret_key = f.read().strip()
if os.environ.get('SECRET_KEY'):
    app.secret_key = os.environ['SECRET_KEY']

## flask-admin code ###########################################################

class ProtectedAdminIndexView(AdminIndexView):
    '''Login protected index page for the admin area.'''
    @expose('/')
    def index(self):
        if not is_admin_visible():
            return redirect(url_for('login'))
        return super(ProtectedAdminIndexView, self).index()

class ProtectedAdminModelView(ModelView):
    '''Login protected views for models in the admin area.'''
    def is_accessible(self):
        return is_admin()

    def inaccessible_callback(self, *a, **kw):
        return redirect(url_for('login'))

class CommentModeration(BaseView):
    '''Easier moderation of comments.'''
    def is_accessible(self):
        return is_admin_visible()

    def inaccessible_callback(self, *a, **kw):
        return redirect(url_for('login'))

    @expose('/')
    def index(self):
        one_day_ago = datetime.utcnow() - timedelta(hours=24)
        comments = Comment.query.filter(
            db.and_(Comment.created >= one_day_ago, Comment.is_visible == False, Comment.is_deleted != True)
        ).all()
        return self.render('admin/moderation.html', comments=comments)

    @expose('/approve', methods=['POST'])
    def approve(self):
        comment_id = int(request.values['comment_id'])
        c = Comment.query.get(comment_id)
        c.is_visible = True
        db.session.add(c)
        db.session.commit()
        return redirect(url_for('moderation.index'))

    @expose('/reject', methods=['POST'])
    def reject(self):
        comment_id = int(request.values['comment_id'])
        c = Comment.query.get(comment_id)
        c.is_deleted = True
        db.session.add(c)
        db.session.commit()
        return redirect(url_for('moderation.index'))

admin = Admin(app, name='MoviePicker Admin', index_view=ProtectedAdminIndexView())
admin.add_view(CommentModeration(name='Moderation', endpoint='moderation'))

for model in [User, Category, Movie, Comment]:
    admin.add_view(ProtectedAdminModelView(model, db.session))

## utilities ##################################################################

@app.before_request
def before_request():
    '''
    If there is a user currently in the session, look up their User object in
    the database and set `g.user`.
    '''
    g.user = None
    if 'user' in session:
        g.user = User.query.get(session['user'])

def is_admin():
    return g.user and g.user.role == 'admin'

def is_admin_visible():
    return g.user and g.user.role in ['admin', 'moderator']

def is_logged_in():
    return bool(g.user)

@app.context_processor
def add_utils_to_template_context():
    return dict(
        is_admin_visible=is_admin_visible,
        is_logged_in=is_logged_in,
    )

def login_required(f):
    '''
    View decorator that ensures a logged in user is in the session, redirecting
    to the login page otherwise.
    '''
    @wraps(f)
    def inner(*a, **kw):
        if not is_logged_in():
            return redirect(url_for('login'))
        return f(*a, **kw)
    return inner

## application code ###########################################################

app.register_blueprint(api, url_prefix='/api')

@app.route('/')
def index():
    categories = Category.query.all()
    return render_template("index.html", categories=categories)

@app.route('/categories/<category>')
def show_category(category, message=''):
    titles = fetch_wikipedia_titles(category)
    return render_template("category.html", category=category, titles=titles, message=message)

@app.route('/categories', methods=['GET', 'POST'])
@login_required
def add_category():
    if request.method == 'GET':
        return render_template("add_category.html")
    name = request.form.get('category').replace(' ', '_')
    try:
        is_valid_category(name)
        category = Category.create(name)
    except RuntimeError, e:
        return render_template("add_category.html", category=name, error=e.message)

    return show_category(category.name, message='Category created!')

@app.route('/random')
def random_movie():
    cat = random.choice(Category.query.all())
    title = random.choice(fetch_wikipedia_titles(cat.name))
    return redirect(url_for("show_movie", title=title))

@app.route('/movie/<title>')
def show_movie(title):
    movie = Movie.query.filter_by(title=title).one_or_none()
    comments = movie.comments.filter_by(is_visible=True, is_deleted=False) if movie else []
    moviedata = MovieData(fetch_omdb_info(title))
    return render_template("movie.html", moviedata=moviedata, comments=comments)

def register_or_login(form):
    submit = form['submit']
    if submit == 'reg':
        user = User.create(form['r_username'], form['r_email'], form['r_password'], form['r_confirm'])
    elif submit == 'login':
        user = User.validate(form['l_username_or_email'], form['l_password'])
    else:
        raise ValueError("Got unexpected submit value {!r}".format(submit))
    return user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('index'))
    if request.method == 'GET':
        return render_template('login.html')
    try:
        user = register_or_login(request.form)
    except RuntimeError, exc:
        error_type = '{}_error'.format(request.form['submit'])
        return render_template('login.html', **{error_type: exc.message})
    session['user'] = user.id
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    if 'user' in session:
        del session['user']
    return redirect(url_for('index'))

@app.route('/user', methods=['GET', 'POST'])
@login_required
def show_user():
    if request.method == 'POST' and request.form['action'] == 'add':
        User.query.get(g.user.id).add_to_list(request.form['title'])
        return "Added."
    elif request.method == 'POST' and request.form['action'] == 'remove':
        User.query.get(g.user.id).remove_from_list(request.form['title'])
        return "Removed."

    movies = g.user.movies
    movies = [MovieData(fetch_omdb_info(movie.title)) for movie in movies]
    return render_template("user.html", movies=movies)

@app.route('/comments', methods=['POST'])
@login_required
def post_comment():
    title = request.form['title']
    contents = request.form['contents']
    if contents:
        m = Movie.get_or_create(title)
        m.add_comment(Comment(user_id=g.user.id, contents=contents))
    return redirect(url_for("show_movie", title=title))

@app.route('/rehost_image')
def rehost_image():
    image = urllib.urlopen(request.args['url'])
    return (image.read(), '200 OK', {'Content-type': 'image/jpeg'})

@app.route('/db_create_all')
def db_create_all():
    '''Run this to create the database on Heroku etc.'''
    db.create_all()
    return "OK"


#####

if __name__ == '__main__':
    #setting the secret here for development purposes only
    #in production you would load this from a config file, environment variable, etc. outside of version control
    #uuid.getnode() returns a (hopefully) unique integer tied to your computer's hardware
    import uuid
    app.secret_key = app.secret_key or str(uuid.getnode())
    app.run(host='0.0.0.0', debug=True)
