import md5
from flask import abort, redirect, request, session, url_for
from functools import wraps

import settings


def authenticated(f):
    """Check if user is logged in"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('snapshots_email'):
            return redirect(url_for('main'))
        return f(*args, **kwargs)
    return decorated


def csrf_protect(f):
    """Check CSRF."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "POST":
            token = session.pop('_csrf_token', None)
            if not token or token != request.form.get('_csrf_token'):
                abort(403)
        return f(*args, **kwargs)
    return decorated


def gravatar(email, size=50):
    """Get gravatar image."""
    email = str(md5.new(email).hexdigest())
    gravatar = 'http://www.gravatar.com/avatar/%s?s=%s' % (email, size)
    return gravatar