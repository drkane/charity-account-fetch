import datetime
import os
import re

from flask import Flask, render_template
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from . import blueprints as bp
from . import db
from .auth import basic_auth
from .fetch import fetch_cli
from .utils import parse_datetime

if os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        integrations=[FlaskIntegration()],
        environment=os.environ.get("FLASK_ENV", "production"),

        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0
    )


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        ES_URL=os.environ.get("ELASTICSEARCH_URL"),
        ES_INDEX="charityaccounts",
        CHARITYBASE_API_URL=os.environ.get(
            "CHARITYBASE_API_URL", "https://charitybase.uk/api/graphql"
        ),
        CHARITYBASE_API_KEY=os.environ.get("CHARITYBASE_API_KEY"),
        CCEW_API_KEY=os.environ.get("CCEW_API_KEY"),
        FILE_SIZE_LIMT=(1024 ** 2) * 10,  # limit file size to upload - 10MB
        BASIC_AUTH_USERNAME=os.environ.get("BASIC_AUTH_USERNAME", "user"),
        BASIC_AUTH_PASSWORD=os.environ.get("BASIC_AUTH_PASSWORD"),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    basic_auth.init_app(app)
    db.init_app(app)
    bp.init_app(app)
    app.cli.add_command(fetch_cli)

    @app.context_processor
    def inject_now():
        return dict(
            now=datetime.datetime.now(),
        )

    @app.template_filter("strip_whitespace")
    def strip_whitespace(text):
        return re.sub(r"(\s)\s+", r"\1", text)

    @app.template_filter("dateformat")
    def dateformat_filter(d, f="%Y-%m-%d", o=None):
        return parse_datetime(d, f, o)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html.j2", error=e), 404

    return app
