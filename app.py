import time
import traceback
import hashlib
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from flask import Flask, request, render_template, redirect, url_for, \
    make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_htmlmin import HTMLMIN
from flask_alembic import Alembic
from flask_assets import Environment, Bundle
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from pygments import highlight
from pygments.util import ClassNotFound
from pygments.lexers import guess_lexer, get_lexer_for_filename
from pygments.formatters import HtmlFormatter
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.exceptions import NotFound, BadRequest, \
    RequestEntityTooLarge


app = Flask('quickpaste')
app.config.from_json('config.json')

if app.config.get('BEHIND_PROXY'):
    # DO NOT DO THIS IN PROD UNLESS YOU SERVE THE APP BEHIND A 
    # REVERSE PROXY!
    app.wsgi_app = ProxyFix(app.wsgi_app)

handler = RotatingFileHandler(app.config['LOG_FILE'], maxBytes=1024 * 1024)
app.logger.setLevel(app.config['LOG_LEVEL'])
app.logger.addHandler(handler)

HTMLMIN(app)
db = SQLAlchemy(app)
alembic = Alembic(app)
mail = Mail(app)
assets = Environment(app)
limiter = Limiter(app, key_func=get_remote_address)
assets.register('js_all', Bundle(
    'js/main.js', filters='jsmin', output='bundle.js'))
assets.register('css_all', Bundle(
    'css/normalize.css', 'css/highlight.css', 'css/fontello.css',
    'css/styles.css', filters='cssmin', output='bundle.css'))


def insert_text(text):
    hash = hashlib.md5(text.encode('utf-8'))
    result = db.engine.execute(
        "SELECT * FROM pastes WHERE hash = ?", [hash.digest()])
    if result.first() is None:
        db.engine.execute("INSERT INTO pastes VALUES (?, ?, ?)",
                          [hash.digest(), text, time.time()])
    result.close()
    return hash.hexdigest()


def get_text(hexhash):
    try:
        binhash = bytes.fromhex(hexhash)
    except (ValueError, TypeError):
        return None
    result = db.engine.execute(
        'SELECT * FROM pastes WHERE hash=?', [binhash])
    item = result.first()
    if item is None:
        return None
    result.close()
    return item[1]


def respond_with_redirect_or_text(redirect, text, status=200):
    respond_with = request.headers.get('X-Respondwith')
    if (respond_with == 'link'):
        return (text, status, {'Content-type': 'text/plain; charset=utf-8'})
    return redirect


@app.errorhandler(400)
def bad_request(e):
    return respond_with_redirect_or_text(
        redirect('/'), '400 missing text\n', 400)


@app.errorhandler(404)
def not_found(e):
    return render_template(
        '4xx.html', title='Not found',
        message='There doesn\'t seem to be a paste here',
        disabled=['clone', 'save'], body_class='about'), 404


@app.errorhandler(413)
def too_large(e):
    return render_template(
        '4xx.html', title='Too many characters',
        message='Limit: {}'.format(app.config['MAX_PASTE_LENGTH']),
        disabled=['clone', 'save'], body_class='about'), 413


@app.errorhandler(429)
def rate_limit(e):
    return render_template(
        '4xx.html', title='Too many requests',
        message='Limit: {}'.format(app.config.get('RATELIMIT_DEFAULT')),
        disabled=['clone', 'save'], body_class='about'), 429


if not app.debug:
    @app.errorhandler(500)
    @app.errorhandler(Exception)
    def internal_error(e):
        tb = traceback.format_exc()
        try:
            mail.send(Message(
                subject='Error From {}'.format(request.host_url),
                recipients=[app.config['MAIL_RECIPIENT']],
                body=render_template('email/error.txt.jinja', tb=tb),
                html=render_template('email/error.html.jinja', tb=tb)
            ))
        except Exception:
            app.logger.error(f'Failed to send error email {tb}')

        return render_template(
            '5xx.html', title='Uh oh', message='Shit really hit the fan',
            disabled=['clone', 'save'], body_class='about'), 500


about_text = """
# Quickpaste

A dead simple code sharing tool.


## Features

**Syntax highlighting**

There is automatic language detection, but sometimes it gets it wrong.  To
override the language, just add or edit a file extension to the url.

**Line highlighting**

Click on a line number to highlight that line, and click the line number again
to un-highlight it.  The highlighted lines are saved in the url, so they will
stay highlighted if you share the link with someone.

**Does not totally break without JavaScript**

No JavaScript is required to use the basic features of pasting code, saving it,
and copying the link to share. But line highlighting will not work without
JavaScript.


## FAQ

**Are the snippets stored forever?**

NO! They are deleted after one week(ish).

**Is the code available?**

[github project](https://github.com/carc1n0gen/quickpaste)

**Can I use quickpaste from my terminal?**

`cat file-name | curl -H "X-Respondwith: link" -X POST -d "text=$(</dev/stdin)" https://quickpaste.net/`

*Notice: The "X-Respondwith: link" is important. Otherwise you will get a
redirect response.*

You could even alias the curl part of that command:

`alias quickpaste="curl -H \"X-Respondwith: link\" -X POST -d \"text=\$(</dev/stdin)\" https://quickpaste.net/"`

To make it as simple as:

`cat file-name | quickpaste`
"""


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        maxlength = app.config.get('MAX_PASTE_LENGTH')
        text = request.form.get('text')
        if text is None or text.strip() == '':
            raise BadRequest()
        elif maxlength is not None and len(text) > maxlength:
            raise RequestEntityTooLarge()
        hexhash = insert_text(text)
        return respond_with_redirect_or_text(
            redirect(url_for('view', hexhash=hexhash)), '{}{}\n'.format(
                request.host_url, hexhash), 200)

    clone = request.args.get('clone')
    if clone == 'about':
        text = about_text
    else:
        text = get_text(clone)

    return render_template(
        'index.html', text=text, disabled=['clone', 'new', 'raw', 'download'])


@app.route('/<string:hexhash>', methods=['GET'])
@app.route('/<string:hexhash>.<string:extension>', methods=['GET'])
def view(hexhash, extension=None):
    highlighted = request.args.get('h')
    if highlighted:
        highlighted = highlighted.split(',')

    if hexhash == 'about' and extension == 'md':
        text = about_text
    else:
        text = get_text(hexhash)

    if text is None:
        raise NotFound()

    try:
        lexer = get_lexer_for_filename('foo.{}'.format(extension))
    except ClassNotFound:
        lexer = guess_lexer(text)
    lines = text.count('\n')
    return render_template(
        'view.html',
        hexhash=hexhash,
        extension=extension,
        text=highlight(text, lexer, HtmlFormatter()),
        lines=lines,
        disabled=['save'], highlighted=highlighted
    )


@app.route('/raw/<string:hexhash>', methods=['GET'])
@app.route('/raw/<string:hexhash>.<string:extension>', methods=['GET'])
def raw(hexhash, extension=None):
    if hexhash == 'about' and extension == 'md':
        text = about_text
    else:
        text = get_text(hexhash)

    if text is None:
        raise NotFound()

    return (text, 200, {'Content-type': 'text/plain; charset=utf-8'})


@app.route('/download/<string:hexhash>', methods=['GET'])
@app.route('/download/<string:hexhash>.<string:extension>', methods=['GET'])
def download(hexhash, extension='txt'):
    if hexhash == 'about' and extension == 'md':
        text = about_text
    else:
        text = get_text(hexhash)

    if text is None:
        raise NotFound()

    res = make_response(text)
    res.headers['Content-Disposition'] = \
        f'attachment; filename={hexhash}.{extension}'
    res.headers['Content-type'] = 'text/plain; charset=utf-8'
    return res


@app.cli.command()
def cleanup():
    # Reminder: the timestamp < ? looks backwards because we are storing 
    # unix timestamps which are the number of seconds since the epoch. 
    # This means that a lower number of seconds is longer ago than a 
    # greater number.
    week_ago = datetime.now() - timedelta(weeks=1)
    db.engine.execute('DELETE FROM pastes WHERE timestamp < ?',
                      [week_ago.timestamp()])
    print('Deleted pastes older than one week.')
