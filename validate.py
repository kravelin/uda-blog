import string
import hashlib
import hmac
import re
import random

from string import letters

SECRET = "ajf9a0jf32kj532mrafsfjfI(#$#$)5kjdsjfa0wer59"


### salted passwords
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))


def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name+pw+salt).hexdigest()
    return "%s|%s" % (salt, h)


### validate username, password, email during signup proccess
def valid_username(username):
    user_re = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    return user_re.match(username)


def valid_password(password):
    pwd_re = re.compile(r"^.{3,20}$")
    return pwd_re.match(password)


def valid_email(email):
    email_re = re.compile("^[\S]+@[\S]+.[\S]+$")
    if email_re.match(email) or email == "":
        return True
    else:
        return False


def valid_pw(name, password, h):
    salt = h.split('|')[0]
    return h == make_pw_hash(name, password, salt)


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


### cookie hashing manipulators
def hash_str(s):
    return hmac.new(SECRET,s).hexdigest()


def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val


def make_secure_val(val):
    return "%s|%s" % (val, hmac.new(SECRET, val).hexdigest())
