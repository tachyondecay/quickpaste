import functools
import pymongo
from flask import render_template, request, redirect
from flask_mail import Mail
from flask_limiter.util import get_remote_address
from flask_limiter import Limiter
from app.repositories import get_db

mail = Mail()
limiter = Limiter(key_func=get_remote_address)

about_text = """# Quickpaste

A dead simple code sharing tool.


## Features

**Syntax highlighting**

There is automatic language detection, but sometimes it gets it wrong.  To
override the language, just add or edit a file extension to the url.

**Line highlighting**

Click on a line number to highlight and target the line with the # part of the
URL. Control+Click (Command+Click on mac) a line to highlight it without
targeting it (This can be done to as many lines as you like).  Click on a
highlighted line to un-highlight it.

**Does not totally break without JavaScript**

No JavaScript is required to use the basic features of pasting code, saving it,
copying the link to share or targetting lines. But Shift-Clicking to highlight
lines without targetting, and un-highlighting lines (for example if someone
shared a link with you pre-highlighted) will not work.


## FAQ

**Are the snippets stored forever?**

NO! They are deleted after one week(ish).

**Is the code available?**

[github project](https://github.com/carc1n0gen/quickpaste)"""


def templated(template=None):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            template_name = template
            if template_name is None:
                template_name = request.endpoint.replace('.', '/') + '.html'

            ctx = f(*args, **kwargs)
            if ctx is None:
                ctx = {}
            elif not isinstance(ctx, dict):
                # Either something other than a dict was returned by the view
                # function, another decorator has modified the return type, or
                # maybe the view function returned a reidrect or something.
                # In any of these cases, just return what we got.
                return ctx

            status = ctx.get('status', 200)
            return render_template(template_name, **ctx), status
        return decorated_function
    return decorator


def text_or_redirect(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            ctx = f(*args, **kwargs)
            if not isinstance(ctx, dict):
                return ctx

            accept = request.headers.get('Accept')
            status = ctx.get('status', 200)
            message = ctx.get('message')
            url = ctx.get('url')
            if accept == 'text/plain':
                if message:
                    text = message
                else:
                    text = url
                return text + '\n', status, {'Content-type': 'text/plain; charset=utf-8'}
            return redirect(url)

        return f(*args, **kwargs)
    return decorated_function


def configure_mongo(app):
    db = get_db()
    pastes = db['pastes']

    try:
        pastes.drop_index('paste_ttl')
    except pymongo.errors.OperationFailure:
        pass

    pastes.create_index('delete_at', expireAfterSeconds=0, name='paste_ttl')
