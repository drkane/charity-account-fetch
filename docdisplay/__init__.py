import os
import datetime
import re

from flask import Flask

from . import db
from . import blueprints as bp

class HighlightNumbers(object):
    def __init__(self, start=1):
        self.count = start - 1

    def __call__(self, match):
        self.count += 1
        return '<span class="bg-yellow" id="match-{}">{}</span>'.format(
            self.count,
            match.group(1)
        )


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
        qs = q.split()
        h = HighlightNumbers()
        s = re.sub(r'({})'.format("|".join(qs)), h, s, flags=re.IGNORECASE)
        return s


    @app.route('/')
    def index():
        return None

    return app