import string
import hashlib
import hmac
import re
import random

from string import letters

SECRET = "ajf9a0jf32kj532mrafsfjfI(#$#$)5kjdsjfa0wer59"


### salted passwords
def make_salt(length = 5):
    """
    make_salt: generates the salt for a password hash
    Args:
        length (int): length of the salt key
    Returns:
        returns the randomly generated salt
    """
    return ''.join(random.choice(letters) for x in xrange(length))


def make_pw_hash(name, pw, salt = None):
    """
    make_pw_hash: creates a hashed password
    Args:
        name (str): the username
        pw (str): the password
        salt (str): optional, the salt to use
    Returns:
        a string of the salt | hashed password
    """
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name+pw+salt).hexdigest()
    return "%s|%s" % (salt, h)


### validate username, password, email during signup proccess
def valid_username(username):
    """
    valid_username: checks to make sure it's a valid username
    Args:
        username (str): username to check
    Returns:
        True / False on if username is valid
    """
    user_re = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    return user_re.match(username)


def valid_password(password):
    """
    valid_password: checks a password to make sure it's valid
    Args:
        password (str): password to be checked
    Returns:
        True / False if password is valid
    """
    pwd_re = re.compile(r"^.{3,20}$")
    return pwd_re.match(password)


def valid_email(email):
    """
    valid_email: checks to see if email is a properly formed email address
    Args:
        email (sstr): email address to check
    Returns:
        True / False if email is valid format
    """
    email_re = re.compile("^[\S]+@[\S]+.[\S]+$")
    if email_re.match(email) or email == "":
        return True
    else:
        return False


def valid_pw(name, password, h):
    """
    valid_pw: checks entered password to see if it matches user's stored password
    Args:
        name (str): username trying to log in
        password (str): password provided by user
        h (str): salt | hashed password from datastore
    Returns:
        True / False if passwords match
    """
    salt = h.split('|')[0]
    return h == make_pw_hash(name, password, salt)


def check_cookie(uncookie):
    """
    check_cookie: verifies that a cookie is valid
    Args:
        uncookie (str): the cookie passed by the browser
    Returns:
        True / False if the cookie is valid
    """
    username, hashedpw = uncookie.split('|')
    check = db.GqlQuery("SELECT * FROM Users WHERE name='%s'" % username)

    username = str(username)
    hashedpw = str(hashedpw)

    if check:
        for row in check:
            hashpw = row.password_hash.split('|')[1]

            if str(row.name) == username and str(hashpw) == hashedpw:
                return True


### cookie hashing manipulators
def hash_str(s):
    """
    hash_str: takes a string and hashes it
    Args:
        s (str): the string to be hashed
    Returns:
        the hashed version of the string
    """
    return hmac.new(SECRET,s).hexdigest()


def check_secure_val(secure_val):
    """
    check_secure_val: checks secure_val to make sure it's valid
    Args:
        secure_val (str): a salt | hash string to be checked
    Returns:
        returns the salt if valid
    """
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val


def make_secure_val(val):
    """
    make_secure_val: creates a salt | hash string from a salt
    Args:
        val (str): the value to hash
    Returns:
        salt | hash string from val
    """
    return "%s|%s" % (val, hmac.new(SECRET, val).hexdigest())
