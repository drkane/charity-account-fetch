import os
import datetime

from flask import Flask

from . import db
from . import blueprints as bp
from .utils import add_highlights, parse_datetime


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        ES_URL=os.environ.get('ES_URL'),
        ES_INDEX='charityaccounts',
        ES_PIPELINE='accounts',
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
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

    @app.context_processor
    def inject_now():
        return dict(
            now=datetime.datetime.now(),
        )

    @app.template_filter('highlight')
    def highlight_filter(s, q):
        return add_highlights(s, q)[0]

    @app.template_filter('dateformat')
    def dateformat_filter(d, f="%Y-%m-%d", o=None):
        return parse_datetime(d, f, o)

    return app
