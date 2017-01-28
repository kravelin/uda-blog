import validate
import jinja2
import os

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)


### Database setup
def users_key(group = "default"):
    return db.Key.from_path("users", group)


class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty()


    @classmethod
    def by_id(cls, uid):
        return cls.get_by_id(uid, parent = users_key())


    @classmethod
    def by_name(cls, name):
        u = cls.all().filter("name =", name).get()
        return u


    @classmethod
    def register(cls, name, pw, email = None):
        pw_hash = validate.make_pw_hash(name, pw)
        return cls(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email)


    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and validate.valid_pw(name, pw, u.pw_hash):
            return u


class Comments(db.Model):
    post_id = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    author = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)


    def render(self, username):
        self._render_text = self.content
        return self.render_str("comment.html", c = self, username = username)


    @classmethod
    def by_post(cls, post_id):
        c = cls.all().filter("post_id =", str(post_id))
        c_count = cls.all(keys_only=True).filter("post_id =", str(post_id)).count(5000)
        return c, c_count


class Post(db.Model):
    title = db.StringProperty(required = True)
    author = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)


    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)


    def render(self, username):
        self._render_text = self.content
        return self.render_str("post.html", p = self, username = username)


def blog_key(name = "default"):
    return db.Key.from_path("blogs" , name)
