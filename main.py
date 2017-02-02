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
from functools import wraps
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True, trim_blocks = True)


### Decorators
def post_exists(function):
    """
    post_exists: decorator to check if a post ID is valid
    Args:
        function (function): the wrapped function
    Returns:
        either the function with post id and post object, or redirects to 404 page
    """
    @wraps(function)
    def wrapper(self, post_id):
        key = db.Key.from_path("Post", int(post_id),
                               parent = blogData.blog_key())
        post = db.get(key)
        if post:
            return function(self, post_id, post)
        else:
            self.error(404)
            return self.redirect("/404/%s" % post_id)
    return wrapper


def comment_exists(function):
    """
    comment_exists: decorator to check if a comment ID is valid
    Args:
        function (function): the wrapped function
    Returns:
        either the function with comment id and comment object, or redirects to 404 page
    """
    @wraps(function)
    def wrapper(self, c_id):
        key = db.Key.from_path("Comments", int(c_id),
                                parent = blogData.blog_key())
        comment = db.get(key)
        if comment:
            return function(self, c_id, comment)
        else:
            self.error(404)
            return self.redirect("/404/%s" % c_id)
    return wrapper


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
    comment, c_count = blogData.Comments.by_post(post_id)

    if not comment:
        c_count = 0

    like, l_count = blogData.Likes.by_post(post_id)

    if not like:
        l_count = 0

    t = jinja_env.get_template("postsummary.html")
    return t.render(post_id = post_id, c_count = c_count, comments = comment,
                    author = author, username = username, l_count = l_count,
                    likes = like)

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


    def user_logged_in(self):
        """
        user_logged_in: check if a user is logged in
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            either the username of logged in user, or redirects to login page
        """
        if self.user:
            username = self.user.name
            return username
        else:
            return self.redirect("/login")


    def user_owns_post(self, post):
        """
        user_owns_post: check if a logged in user owns the post
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            post (object): post object for the post being checked
        Returns:
            True if the user and post authoer match
        """
        author = post.author
        username = self.user.name
        return author == username


    def user_owns_comment(self, comment):
        """
        user_owns_comment: check if a logged in user owns the comment
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            comment (object): comment object for the comment being checked
        Returns:
            True if the user and comment author match
        """
        author = comment.author
        username = self.user.name
        return author == username


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
        username = self.user_logged_in()
        self.render("welcome.html", username = username)


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

        posts = blogData.Post.all().order("-created")

        if not self.user:
            usernmae = ""
        else:
            username = self.request.get("username")

        post_id = self.request.get("post_id")

        key = db.Key.from_path("Post", int(post_id),
              parent=blogData.blog_key())
        post = db.get(key)

        if post:
            if self.request.get("Like"):
                like = blogData.Likes.by_user_and_post(post_id, username)

            if user_owns_post(post):
                self.redirect("/blog")
            elif like:
                like.delete()
                self.redirect("/blog")
            else:
                like = blogData.Likes(post_id = post_id, username = username)
                like.put()
                self.redirect("/blog")


class PostPage(Handler):

    @post_exists
    def get(self, post_id, post):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            post_id (int): ID of the post to be displayed
            post (object): post object of post to be displayed
        Returns:
            no return value
        """
        if not self.user:
            username = ""
        else:
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
        username = self.user_logged_in()
        self.render("newpost.html", username = username)


    def post(self):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
        Returns:
            no return value
        """
        author = self.user_logged_in()

        title = self.request.get("title")
        content = self.request.get("content")

        if title and content:
            post = blogData.Post(parent = blogData.blog_key(), title = title,
                     content = content, author = author)
            post.put()
            self.redirect("/blog/%s" % str(post.key().id()))
        else:
            error = "title and content, please!"
            self.render("newpost.html", title=title, content=content,
                        error=error, username=author)


class EditPostPage(Handler):

    @post_exists
    def get(self, post_id, post):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            post_id (int): ID of the post to be edited
            post (object): post object of the post to be edited
        Returns:
            no return value
        """

        username = self.user_logged_in()

        if not self.user_owns_post(post):
            return self.redirect("/blog")

        self.render("editpost.html", title = post.title, content = post.content,
                    post_id = post_id)


    @post_exists
    def post(self, post_id, post):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            post_id (int): ID of the post to edit
            post (object): post object of the post to be edited
        Returns:
            no return value
        """

        username = self.user_logged_in()

        title = self.request.get("title")
        content = self.request.get("content")

        if not self.user_owns_post(post):
            return self.redirect("/blog")

        if title and content:
            post.title = title
            post.content = content
            post.put()
            self.redirect("/blog/%s" % str(post.key().id()))
        else:
            error = "title and content, please!"
            self.render("editpost.html", title = title, content = content,
                        error = error, username = username, post_id = post_id)


class DeletePostPage(Handler):

    @post_exists
    def get(self, post_id, post):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            post_id (int): ID of post to delete
        Returns:
            no return value
        """

        username = self.user_logged_in()

        if not self.user_owns_post(post):
            return self.redirect("/blog")

        self.render("deletepost.html", post = post, username = username,
                    post_id = post_id)


    @post_exists
    def post(self, post_id, post):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            post_id (int): ID of the post to delete
            post (object): post object of the post to be deleted
        Returns:
            no return value
        """

        username = self.user_logged_in()

        if not self.user_owns_post(post):
            return self.redirect("/blog")

        post.delete()

        comments, c_count = blogData.Comments.by_post(post_id)

        if comments:
            for comment in comments:
                comment.delete()

        likes, l_count = blogData.Likes.by_post(post_id)

        if likes:
            for like in likes:
                like.delete()

        self.redirect("/blog")


class AddCommentPage(Handler):

    @post_exists
    def get(self, post_id, post):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            post_id (int): ID of post the comment is for
            post (object): post object of the post being commented on
        Returns:
            no return value
        """

        author = self.user_logged_in()
        self.render("addcomment.html", post_id = post_id, author = author)


    @post_exists
    def post(self, post_id, post):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            post_id (int): ID of the post the comment is for
            post (object): post object of the post being commented on
        Returns:
            no return value
        """

        author = self.user_logged_in()
        content = self.request.get("content")

        if content:
            comment = blogData.Comments(parent = blogData.blog_key(), post_id = post_id,
                     content = content, author = author)
            comment.put()
            self.redirect("/blog/%s" % str(post_id))
        else:
            error = "comment cannot be blank!"
            self.render("addcomment.html", post_id = post_id, content = content,
                        error = error, author = author)


class EditCommentPage(Handler):

    @comment_exists
    def get(self, c_id, comment):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            c_id (int): ID of the comment to be edited
            comment (object): comment object of the comment to be edited
        Returns:
            no return value
        """

        username = self.user_logged_in()

        if not self.user_owns_comment(comment):
            return self.redirect("/blog")

        self.render("editcomment.html", content = comment.content,
                    c_id = c_id)


    @comment_exists
    def post(self, c_id, comment):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            c_id (int): ID of the comment to be edited
            comment (object): comment object of the comment to be edited
        Returns:
            no return value
        """

        username = self.user_logged_in()

        content = self.request.get("content")

        if not self.user_owns_comment(comment):
            return self.redirect("/blog")

        if content:
            comment.content = content
            comment.put()
            post_id = comment.post_id
            self.redirect("/blog/%s" % str(post_id))
        else:
            error = "comment cannot be blank!"
            self.render("editcomment.html", content = content,
                        error = error, username = username, c_id = c_id)


class DeleteCommentPage(Handler):

    @comment_exists
    def get(self, c_id, comment):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            c_id (int): ID of the comment to be deleted
            comment (object): comment object of the comment to be deleted
        Returns:
            no return value
        """

        username = self.user_logged_in()

        if not self.user_owns_comment(comment):
            return self.redirect("/blog")

        self.render("deletecomment.html", comment = comment, c_id = c_id,
                    username = username)


    @comment_exists
    def post(self, c_id, comment):
        """
        post: renders page when post method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            c_id (int): ID of the comment to be deleted
            comment (object): comment object of the comment to be deleted
        Returns:
            no return value
        """

        username = self.user_logged_in()

        if not self.user_owns_comment(comment):
            return self.redirect("/blog")

        comment.delete()
        self.redirect("/blog")


class NotFoundErrorPage(Handler):

    def get(self, error_id):
        """
        get: renders page when get method used
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            error_id (int): the ID of the post or comment not found
        Returns:
            no return value
        """
        self.render("404.html", error_id = error_id)


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
                               ("/blog/editpost/([0-9]+)",EditPostPage),
                               ("/blog/deletepost/([0-9]+)",DeletePostPage),
                               ("/blog/addcomment/([0-9]+)",AddCommentPage),
                               ("/blog/editcomment/([0-9]+)",EditCommentPage),
                               ("/blog/deletecomment/([0-9]+)",DeleteCommentPage),
                               ("/404/([0-9]+)",NotFoundErrorPage)
                               ], debug=True)
