import os
import webapp2
import jinja2
import hashlib
import hmac
import random
import string
import re

### My modules
import blogData
import validate

from string import letters
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True, trim_blocks = True)


### blog functions
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


def summary_details(post_id, author, username):
    c, c_count = blogData.Comments.by_post(post_id)

    if not c:
        c_count = 0

    t = jinja_env.get_template("postsummary.html")
    return t.render(post_id = post_id, c_count = c_count, comments = c,
                    author = author, username = username)

jinja_env.filters["summary_details"] = summary_details


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
        cookie_val = validate.make_secure_val(val)
        self.response.headers.add_header("Set-Cookie", "%s=%s; Path=/" %
                                         (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and validate.check_secure_val(cookie_val)


    def login(self, user):
        self.set_secure_cookie("user_id", str(user.key().id()))


    def logout(self):
        self.response.headers.add_header("Set-Cookie", "user_id=; Path=/")


    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie("user_id")
        self.user = uid and blogData.User.by_id(int(uid))


class Signup(Handler):

    def get(self):
        self.render("signup.html")


    def post(self):
        have_error = False
        self.username = self.request.get("username")
        self.password = self.request.get("password")
        self.verify = self.request.get("verify")
        self.email = self.request.get("email")

        params = dict(username = self.username, email = self.email)

        if not validate.valid_username(self.username):
            params["error_username"] = "That's not a valid username."
            have_error = True

        if not validate.valid_password(self.password):
            params["error_password"] = "That's not a valid password."
            have_error = True
        elif self.password != self.verify:
            params["error_verify"] = "Your passwords didn't match."
            have_error = True

        if not validate.valid_email(self.email):
            params["error_email"] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render("signup.html", **params)
        else:
            self.done()


    def done(self, *a, **kw):
        raise NotImplementedError


class SignUpPage(Signup):

    def done(self):
        # make sure the user doesn't already exist
        u = blogData.User.by_name(self.username)
        if u:
            msg = "That user already exists"
            params = dict(username = self.username, email = self.email)
            self.render("signup.html", error_username = msg, **params)
        else:
            u = blogData.User.register(self.username, self.password,
                self.email)
            u.put()

            self.login(u)
            self.redirect("/welcome")


class WelcomePage(Handler):

    def get(self):
        if self.user:
            self.render("welcome.html",username=self.user.name)
        else:
            self.redirect("/login")


class LoginPage(Handler):

    def get(self):
        self.render("login.html")


    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")

        u = blogData.User.login(username, password)
        if u:
            self.login(u)
            self.redirect("/welcome")
        else:
            msg = "Invalid login"
            self.render("login.html", error = msg)


class LogoutPage(Handler):

    def get(self):
        self.logout()
        self.redirect("/login")


class BlogFrontPage(Handler):
    def get(self):

        if not self.user:
            username = ""
        else:
            username = self.user.name

        posts = blogData.Post.all().order("-created")
        self.render("frontpage.html", posts = posts, username = username)


    def post(self):

        post_id = self.request.get("post_id")
        key = db.Key.from_path("Post", int(post_id),
              parent=blogData.blog_key())
        p = db.get(key)

        if self.request.get("Edit"):
            return self.redirect("/blog/editpost?post_id=%s" % post_id)

        if self.request.get("Delete"):
            return self.redirect("/blog/deletepost?post_id=%s" % post_id)

        if self.request.get("Comment"):
            return self.redirect("/blog/addcomment?post_id=%s" % post_id)


class PostPage(Handler):

    def get(self, post_id):
        if not self.user:
            return self.redirect("/login")

        key = db.Key.from_path("Post", int(post_id),
              parent=blogData.blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return

        username = self.user.name
        self.render("permalink.html", post = post, username = username)


class NewPostPage(Handler):

    def get(self):
        if self.user:
            username = self.user.name
            return self.render("newpost.html", username=username)
        else:
            self.redirect("/login")


    def post(self):
        if not self.user:
            return self.redirect("/login")

        if self.request.get("Cancel"):
            return self.redirect("/blog")

        author = self.user.name

        title = self.request.get("title")
        content = self.request.get("content")

        if title and content:
            p = blogData.Post(parent = blogData.blog_key(), title = title,
                     content = content, author = author)
            p.put()
            self.redirect("/blog/%s" % str(p.key().id()))
        else:
            error = "title and content, please!"
            self.render("newpost.html", title=title, content=content,
                        error=error, username=author)


class EditPostPage(Handler):

    def get(self):

        if not self.user:
            return self.redirect("/login")

        post_id = self.request.get("post_id")
        key = db.Key.from_path("Post", int(post_id),
              parent=blogData.blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return

        self.render("editpost.html", title = post.title, content = post.content,
                    post_id = post_id)


    def post(self):
        if not self.user:
            return self.redirect("/login")

        if self.request.get("Cancel"):
            return self.redirect("/blog")

        author = self.user.name

        title = self.request.get("title")
        content = self.request.get("content")
        post_id = self.request.get("post_id")

        if title and content:
            key = db.Key.from_path("Post", int(post_id),
                                   parent=blogData.blog_key())
            p = db.get(key)
            p.title = title
            p.content = content
            p.put()
            self.redirect("/blog/%s" % str(p.key().id()))
        else:
            error = "title and content, please!"
            self.render("editpost.html", title = title, content = content,
                        error = error, username = author, post_id = post_id)


class DeletePostPage(Handler):

    def get(self):

        if not self.user:
            return self.redirect("/login")

        post_id = self.request.get("post_id")
        key = db.Key.from_path("Post", int(post_id),
              parent=blogData.blog_key())
        p = db.get(key)

        if not p:
            self.error(404)
            return

        if p.author != self.user.name:
            return self.redirect("/blog")

        self.render("deletepost.html", p = p, post_id = post_id, username=self.user.name)


    def post(self):
        if not self.user:
            return self.redirect("/login")

        if self.request.get("Cancel"):
            return self.redirect("/blog")

        post_id = self.request.get("post_id")
        key = db.Key.from_path("Post", int(post_id),
              parent=blogData.blog_key())
        p = db.get(key)

        if not p:
            self.error(404)
            return

        if p.author != self.user.name:
            return self.redirect("/blog")

        p.delete()
        self.redirect("/blog")


class AddCommentPage(Handler):

    def get(self):
        if self.user:
            post_id = self.request.get("post_id")
            author = self.user.name
            return self.render("addcomment.html", post_id = post_id,
                                author = author)
        else:
            self.redirect("/login")


    def post(self):
        if not self.user:
            return self.redirect("/login")

        if self.request.get("Cancel"):
            return self.redirect("/blog")

        author = self.user.name
        content = self.request.get("content")
        post_id = self.request.get("post_id")

        if content:
            c = blogData.Comments(parent = blogData.blog_key(), post_id = post_id,
                     content = content, author = author)
            c.put()
            self.redirect("/blog/%s" % str(post_id))
        else:
            error = "comment cannot be blank!"
            self.render("addcomment.html", post_id = post_id, content = content,
                        error = error, author = author)


class EditCommentPage(Handler):

    def get(self):

        if not self.user:
            return self.redirect("/login")

        c_id = self.request.get("c_id")
        key = db.Key.from_path("Comments", int(c_id),
              parent=blogData.blog_key())
        comment = db.get(key)

        if not comment:
            self.error(404)
            return

        self.render("editcomment.html", content = comment.content,
                    c_id = c_id)


    def post(self):
        if not self.user:
            return self.redirect("/login")

        if self.request.get("Cancel"):
            return self.redirect("/blog")

        author = self.user.name

        content = self.request.get("content")
        c_id = self.request.get("c_id")

        if content:
            key = db.Key.from_path("Comments", int(c_id),
                                   parent=blogData.blog_key())
            c = db.get(key)
            c.content = content
            c.put()
            post_id = c.post_id
            self.redirect("/blog/%s" % str(post_id))
        else:
            error = "comment cannot be blank!"
            self.render("editcomment.html", content = content,
                        error = error, username = author, c_id = c_id)


class DeleteCommentPage(Handler):

    def get(self):

        if not self.user:
            return self.redirect("/login")

        c_id = self.request.get("c_id")
        key = db.Key.from_path("Comments", int(c_id),
              parent=blogData.blog_key())
        c = db.get(key)

        if not c:
            self.error(404)
            return

        if c.author != self.user.name:
            return self.redirect("/blog")

        self.render("deletecomment.html", c = c, c_id = c_id, username=self.user.name)


    def post(self):
        if not self.user:
            return self.redirect("/login")

        if self.request.get("Cancel"):
            return self.redirect("/blog")

        c_id = self.request.get("c_id")
        key = db.Key.from_path("Comments", int(c_id),
              parent=blogData.blog_key())
        c = db.get(key)

        if not c:
            self.error(404)
            return

        if c.author != self.user.name:
            return self.redirect("/blog")

        c.delete()
        self.redirect("/blog")


class MainPage(Handler):

    def get(self):
        self.write("Hello, Udacity!")


app = webapp2.WSGIApplication([("/",MainPage),
                               ("/signup",SignUpPage),
                               ("/welcome",WelcomePage),
                               ("/login",LoginPage),
                               ("/logout",LogoutPage),
                               ("/blog",BlogFrontPage),
                               ("/blog/([0-9]+)",PostPage),
                               ("/blog/newpost",NewPostPage),
                               ("/blog/editpost",EditPostPage),
                               ("/blog/deletepost",DeletePostPage),
                               ("/blog/addcomment",AddCommentPage),
                               ("/blog/editcomment",EditCommentPage),
                               ("/blog/deletecomment",DeleteCommentPage)
                               ], debug=True)
