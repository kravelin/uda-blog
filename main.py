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
    """
    render_str: render a template
    Args:
        self (self pointer): pointer to class object, does not need to be passed in
        template (str): the template file to be rendered
        **params (varies): any extra parameteres to be passed to the rendered template
    Returns:
        rendered template and the parameters in **params
    """
    t = jinja_env.get_template(template)
    return t.render(params)


def summary_details(post_id, author, username):
    """
    summary_details: generates the comments and likes section of a post
    Args:
        post_id (int): ID of the post being used
        author (str): the author of the post
        username (str): the user viewing the post
    Returns:
        rendered template of the post details section
    """
    c, c_count = blogData.Comments.by_post(post_id)

    if not c:
        c_count = 0

    l, l_count = blogData.Likes.by_post(post_id)

    if not l:
        l_count = 0

    t = jinja_env.get_template("postsummary.html")
    return t.render(post_id = post_id, c_count = c_count, comments = c,
                    author = author, username = username, l_count = l_count,
                    likes = l)

jinja_env.filters["summary_details"] = summary_details


### page handlers
class Handler(webapp2.RequestHandler):

    def write(self, *a, **kw):
        """
        write: wrapper for write functionality
        """
        self.response.out.write(*a, **kw)


    def render_str(self, template, **params):
        """
        render_str: render a template
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            template (str): the template file to be rendered
            **params (varies): any extra parameteres to be passed to the rendered template
        Returns:
            rendered template and the parameters in **params
        """
        t = jinja_env.get_template(template)
        return t.render(params)


    def render(self, template, **kw):
        """
        render: wrapper for rendering a template
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            username (str): username of person viewing the page
        Returns:
            rendered template file passed through render_str
        """
        self.write(self.render_str(template, **kw))


    def set_secure_cookie(self, name, val):
        """
        set_secure_cookie: sets the cookie header
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            name (str): name of the cookie_val
            val (str): value of the cookie
        Returns:
            no return value
        """
        cookie_val = validate.make_secure_val(val)
        self.response.headers.add_header("Set-Cookie", "%s=%s; Path=/" %
                                         (name, cookie_val))

    def read_secure_cookie(self, name):
        """
        read_secure_cookie: reads a cookie
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            name (str): name of the cookie to read
        Returns:
            True or False if the cookie is valid
        """
        cookie_val = self.request.cookies.get(name)
        return cookie_val and validate.check_secure_val(cookie_val)


    def login(self, user):
        """
        login: calls cookie creation when user logs in
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            user (str): user object of person viewing the page
        Returns:
            no return value
        """
        self.set_secure_cookie("user_id", str(user.key().id()))


    def logout(self):
        """
        logout: clears the session cookie when user logs out
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
        self.response.headers.add_header("Set-Cookie", "user_id=; Path=/")


    def initialize(self, *a, **kw):
        """
        initialize: initializes the page
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            *a (varies): arguments to be passed in to webapp2 initialize function
            **kw (varies): arguments to be passed in to webapp2 initialize function
        Returns:
            no return value
        """
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie("user_id")
        self.user = uid and blogData.User.by_id(int(uid))


class Signup(Handler):

    def get(self):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
        self.render("signup.html")


    def post(self):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
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
        """
        done: unimplemented stub function
        """
        raise NotImplementedError


class SignUpPage(Signup):

    def done(self):
        """
        done: checks user to make sure not duplicate, and if passes sends to welcome page
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
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
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
        if self.user:
            self.render("welcome.html",username=self.user.name)
        else:
            self.redirect("/login")


class LoginPage(Handler):

    def get(self):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
        self.render("login.html")


    def post(self):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
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
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
        self.logout()
        self.redirect("/login")


class BlogFrontPage(Handler):
    def get(self):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """

        if not self.user:
            username = ""
        else:
            username = self.user.name

        posts = blogData.Post.all().order("-created")
        self.render("frontpage.html", posts = posts, username = username)


    def post(self):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """

        username = self.request.get("username")
        post_id = self.request.get("post_id")

        key = db.Key.from_path("Post", int(post_id),
              parent=blogData.blog_key())
        p = db.get(key)
        posts = blogData.Post.all().order("-created")

        if self.request.get("Edit"):
            return self.redirect("/blog/editpost?post_id=%s" % post_id)

        if self.request.get("Delete"):
            return self.redirect("/blog/deletepost?post_id=%s" % post_id)

        if self.request.get("Comment"):
            return self.redirect("/blog/addcomment?post_id=%s" % post_id)

        if self.request.get("Like"):
            l = blogData.Likes.by_user_and_post(post_id, username)

            if not self.user:
                return self.redirect("/login")
            if p.author == username:
                self.redirect("/blog")
            elif l:
                l.delete()
                self.redirect("/blog")
            else:
                l = blogData.Likes(post_id = post_id, username = username)
                l.put()
                self.redirect("/blog")


class PostPage(Handler):

    def get(self, post_id):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            post_id (int): ID of the post to be displayed
        Returns:
            no return value
        """
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
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
        if self.user:
            username = self.user.name
            self.render("newpost.html", username=username)
        else:
            self.redirect("/login")


    def post(self):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
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
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """

        if not self.user:
            return self.redirect("/login")

        post_id = self.request.get("post_id")
        key = db.Key.from_path("Post", int(post_id),
              parent=blogData.blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return self.redirect("/404")

        if self.user.name != post.author:
            return self.redirect("/blog")


        self.render("editpost.html", title = post.title, content = post.content,
                    post_id = post_id)


    def post(self):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
        if not self.user:
            return self.redirect("/login")

        if self.request.get("Cancel"):
            return self.redirect("/blog")

        username = self.user.name

        title = self.request.get("title")
        content = self.request.get("content")
        post_id = self.request.get("post_id")
        key = db.Key.from_path("Post", int(post_id),
                               parent=blogData.blog_key())
        p = db.get(key)

        author = p.author
        if username != author:
            return self.redirect("/blog")

        if title and content:
            p.title = title
            p.content = content
            p.put()
            self.redirect("/blog/%s" % str(p.key().id()))
        else:
            error = "title and content, please!"
            self.render("editpost.html", title = title, content = content,
                        error = error, username = username, post_id = post_id)


class DeletePostPage(Handler):

    def get(self):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """

        if not self.user:
            return self.redirect("/login")

        post_id = self.request.get("post_id")
        key = db.Key.from_path("Post", int(post_id),
              parent=blogData.blog_key())
        p = db.get(key)

        if not p:
            self.error(404)
            return self.redirect("/404")

        if p.author != self.user.name:
            return self.redirect("/blog")

        self.render("deletepost.html", p = p, post_id = post_id, username=self.user.name)


    def post(self):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
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
            return self.redirect("/404")

        if p.author != self.user.name:
            return self.redirect("/blog")

        p.delete()
        self.redirect("/blog")


class AddCommentPage(Handler):

    def get(self):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
        if self.user:
            post_id = self.request.get("post_id")
            author = self.user.name
            return self.render("addcomment.html", post_id = post_id,
                                author = author)
        else:
            self.redirect("/login")


    def post(self):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
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
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """

        if not self.user:
            return self.redirect("/login")

        c_id = self.request.get("c_id")
        key = db.Key.from_path("Comments", int(c_id),
              parent=blogData.blog_key())
        comment = db.get(key)

        author = c.author
        if self.user.neme != author:
            return self.redirect("/blog")

        if not comment:
            self.error(404)
            return self.redirect("/404")

        self.render("editcomment.html", content = comment.content,
                    c_id = c_id)


    def post(self):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
        if not self.user:
            return self.redirect("/login")

        if self.request.get("Cancel"):
            return self.redirect("/blog")

        username = self.user.name

        content = self.request.get("content")
        c_id = self.request.get("c_id")
        key = db.Key.from_path("Comments", int(c_id),
                               parent=blogData.blog_key())
        c = db.get(key)

        author = c.author
        if username != author:
            return self.redirect("/blog")

        if content:
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
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """

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
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
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


class NotFoundErrorPage(Handler):

    def get(self):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
        self.render("404.html")


class MainPage(Handler):

    def get(self):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
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
                               ("/blog/deletecomment",DeleteCommentPage),
                               ("/404",NotFoundErrorPage)
                               ], debug=True)
