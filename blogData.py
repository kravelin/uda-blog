import validate
import jinja2
import os

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)


### Database setup
def users_key(group = "default"):
    """
    users_key: get the key for the parent object in datastore
    Args:
        group (str): the group to get the key for
    Returns:
        database Key object of the group
    """
    return db.Key.from_path("users", group)


class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty()


    @classmethod
    def by_id(cls, uid):
        """
        by_id: get User by ID
        Args:
            cls (self pointer): pointer to class object, does not need to be passed in
            uid (int): UID of the user to look up
        Returns:
            database object of the User based on UID
        """
        return cls.get_by_id(uid, parent = users_key())


    @classmethod
    def by_name(cls, name):
        """
        by_name: get User by name
        Args:
            cls (self pointer): pointer to class object, does not need to be passed in
            name (str): name of the user to look up
        Returns:
            database object of the User based on name
        """
        u = cls.all().filter("name =", name).get()
        return u


    @classmethod
    def register(cls, name, pw, email = None):
        """
        register: register a new user
        Args:
            cls (self pointer): pointer to class object, does not need to be passed in
            name (str): name of the user to add
            pw (str): password of the user to add, unencrypted
            email (str): optional email address of user
        Returns:
            database object of the new user
        """
        pw_hash = validate.make_pw_hash(name, pw)
        return cls(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email)


    @classmethod
    def login(cls, name, pw):
        """
        login: log in a user
        Args:
            cls (self pointer): pointer to class object, does not need to be passed in
            name (str): name of the user logging in
            pw (str): unencrypted password of the user logging in
        Returns:
            database object of the User logging in
        """
        u = cls.by_name(name)
        if u and validate.valid_pw(name, pw, u.pw_hash):
            return u


class Likes(db.Model):
    post_id = db.StringProperty(required = True)
    username = db.StringProperty(required = True)


    @classmethod
    def by_post(cls, post_id):
        """
        by_post: get Likes by post_id
        Args:
            cls (self pointer): pointer to class object, does not need to be passed in
            post_id (int): ID of the post to look up
        Returns:
            database object of the Likes for a post based on ID, and count of the Likes
        """
        l = cls.all().filter("post_id =", str(post_id))
        l_count = cls.all(keys_only=True).filter("post_id", str(post_id)).count(5000)
        return l, l_count


    @classmethod
    def by_user_and_post(cls, post_id, username):
        """
        by_user_and_post: check to see if the user has liked a post
        Args:
            cls (self pointer): pointer to class object, does not need to be passed in
            post_id (int): ID of the post to look up
            username (str): username being checked
        Returns:
            database object of the Like based on username and post ID, if it exists
        """
        l = cls.all().filter("post_id =", str(post_id)).filter("username =", str(username)).get()
        return l


class Comments(db.Model):
    post_id = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    author = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)


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


    def render(self, username):
        """
        render: wrapper for rendering a template
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            username (str): username of person viewing the page
        Returns:
            rendered template file passed through render_str
        """
        self._render_text = self.content
        return self.render_str("comment.html", c = self, username = username)


    @classmethod
    def by_post(cls, post_id):
        """
        by_post: get comments based on post ID
        Args:
            cls (self pointer): pointer to class object, does not need to be passed in
            post_id (int): ID of the post to look up
        Returns:
            database object of the Comments for the post, and the count of comments
        """
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


    def render(self, username):
        """
        render: wrapper for rendering a template
        Args:
            self (self pointer): pointer to class object, does not need to be passed in
            username (str): username of person viewing the page
        Returns:
            rendered template file passed through render_str
        """
        self._render_text = self.content
        return self.render_str("post.html", p = self, username = username)


def blog_key(name = "default"):
    """
    blog_key: key for the blog
    Args:
        name (str): nae of datastore group
    Returns:
        key of blogs datastore in the group
    """
    return db.Key.from_path("blogs" , name)
