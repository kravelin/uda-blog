import os
import webapp2
import jinja2
import hashlib
import hmac
import random
import string
import re

from string import letters
from google.appengine.ext import db

SECRET = "ajf9a0jf32kj532mrafsfjfI(#$#$)5kjdsjfa0wer59"

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

### Database setup
def users_key(group = 'default'):
    return db.Key.from_path('users', group)

class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        return cls.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = cls.all().filter('name =', name).get()
        return u

    @classmethod
    def register(cls, name, pw, email = None):
        pw_hash = make_pw_hash(name, pw)
        return cls(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u

### validate username, password, email during signup proccess
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return USER_RE.match(username)

PWD_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return PWD_RE.match(password)

EMAIL_RE = re.compile("^[\S]+@[\S]+.[\S]+$")
def valid_email(email):
    if EMAIL_RE.match(email) or email == "":
        return True
    else:
        return False

### salted passwords
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name+pw+salt).hexdigest()
    return "%s|%s" % (salt, h)

def valid_pw(name, password, h):
    salt = h.split('|')[0]
    return h == make_pw_hash(name, password, salt)

### cookie hashing manipulators
def hash_str(s):
    return hmac.new(SECRET,s).hexdigest()

def check_cookie(uncookie):
    username, hashedpw = uncookie.split('|')
    check = db.GqlQuery("SELECT * FROM Users WHERE name='%s'" % username)

    username = str(username)
    hashedpw = str(hashedpw)

    if check:
        for row in check:
            hashpw = row.password_hash.split('|')[1]

            if str(row.name) == username and str(hashpw) == hashedpw:
                return True

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

def make_secure_val(val):
    return "%s|%s" % (val, hmac.new(SECRET, val).hexdigest())

### blog functions
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

def render_post(response, post):
    response.out.write('<b>' + post.title + '</b><br>')
    response.out.write(post.content)

def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)

class Post(db.Model):
    title = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

### page handlers
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header('Set-Cookie', '%s=%s; Path=/' %
                                         (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

class Signup(Handler):
    def get(self):
        self.render('signup.html')

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username = self.username, email = self.email)

        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "That's not a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class SignUpPage(Signup):
    def done(self):
        # make sure the user doesn't already exist
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists'
            params = dict(username = self.username, email = self.email)
            self.render('signup.html', error_username = msg, **params)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()

            self.login(u)
            self.redirect('/welcome')

class WelcomePage(Handler):
    def get(self):
        if self.user:
            self.render('welcome.html',username=self.user.name)
        else:
            self.redirect('/signup')

class LoginPage(Handler):
    def get(self):
        self.render('login.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/welcome')
        else:
            msg = 'Invalid login'
            self.render('login.html', error = msg)

class LogoutPage(Handler):
    def get(self):
        self.logout()
        self.redirect('/signup')

class BlogFrontPage(Handler):
    def get(self):
        posts = greetings = Post.all().order('-created')
        self.render('frontpage.html', posts = posts)

class PostPage(Handler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return

        self.render("permalink.html", post = post)

class NewPostPage(Handler):
    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login")

    def post(self):
        if not self.user:
            self.redirect('/blog')

        title = self.request.get('title')
        content = self.request.get('content')

        if title and content:
            p = Post(parent = blog_key(), title = title, content = content)
            p.put()
            self.redirect('/blog/%s' % str(p.key().id()))
        else:
            error = "title and content, please!"
            self.render("newpost.html", title=title, content=content,
                        error=error)

class MainPage(Handler):
    def get(self):
        self.write("Hello, Udacity!")

app = webapp2.WSGIApplication([('/',MainPage),
                               ('/signup',SignUpPage),
                               ('/welcome',WelcomePage),
                               ('/login',LoginPage),
                               ('/logout',LogoutPage),
                               ('/blog',BlogFrontPage),
                               ('/blog/([0-9]+)',PostPage),
                               ('/blog/newpost',NewPostPage)
                               ], debug=True)
