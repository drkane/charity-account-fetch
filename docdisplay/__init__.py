import datetime
import os

from flask import Flask

from . import blueprints as bp
from . import db
from .fetch import fetch_cli
from .utils import add_highlights, parse_datetime


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

    db.init_app(app)
    bp.init_app(app)
    app.cli.add_command(fetch_cli)

    @app.context_processor
    def inject_now():
        return dict(
            now=datetime.datetime.now(),
        )

    @app.template_filter("highlight")
    def highlight_filter(s, q):
        return add_highlights(s, q)[0]

    @app.template_filter("dateformat")
    def dateformat_filter(d, f="%Y-%m-%d", o=None):
        return parse_datetime(d, f, o)

    return app
