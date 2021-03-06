import traceback
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import MarkdownLexer
from flask import url_for, render_template, request
from flask_mail import Message
from app.util import mail, text_or_redirect


unknown_error_text = """# Uh Oh!

**Shit really hit the fan.  Some sort of unknown error just happened.**"""


not_found_text = """# Not Found

**There doesn't seem to be anything here.**"""


def setup_handlers(app):
    @app.errorhandler(400)
    @text_or_redirect
    def bad_request(ex):
        return dict(
            status=400,
            message='400 missing text',
            url=url_for('edit.edit', _external=True)
        )

    @app.errorhandler(404)
    def not_found(ex):
        return render_template(
            'view/view.html',
            text=highlight(not_found_text, MarkdownLexer(), HtmlFormatter()),
            lines=not_found_text.count('\n') + 1,
            status=404
        )

    @app.errorhandler(413)
    def too_large(ex):
        text = f"""
# Too many characters

Limit: {app.config['MAX_PASTE_LENGTH']}"""
        return render_template(
            'view/view.html',
            text=highlight(text, MarkdownLexer(), HtmlFormatter()),
            lines=text.count('\n') + 1,
        ), 413

    @app.errorhandler(429)
    def rate_limit(ex):
        text = f"""
# Too Many Requests

**Limit: {app.config.get('RATELIMIT_DEFAULT')}**"""
        return render_template(
            'view/view.html',
            text=highlight(text, MarkdownLexer(), HtmlFormatter()),
            lines=text.count('\n') + 1
        ), 429

    if not app.debug:
        @app.errorhandler(500)
        @app.errorhandler(Exception)
        def unknown_error(ex):
            tb = traceback.format_exc()
            try:
                mail.send(Message(
                    subject=f'Error From {request.host_url}',
                    recipients=[app.config['MAIL_RECIPIENT']],
                    body=render_template('email/error.txt.jinja', tb=tb),
                    html=render_template('email/error.html.jinja', tb=tb)
                ))
            except Exception:
                pass  # Ignore, we're going to log it anyway

            app.logger.exception(f'Unknown error at endpoint: {request.full_path}')
            return render_template(
                'view/view.html',
                text=highlight(unknown_error_text, MarkdownLexer(), HtmlFormatter()),
                lines=unknown_error_text.count('\n') + 1
            ), 500
