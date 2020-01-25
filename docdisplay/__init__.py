import os
import datetime
import re

from flask import Flask

from . import db
from . import main
from . import doc

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
    app.register_blueprint(main.bp)
    app.register_blueprint(doc.bp)

    @app.context_processor
    def inject_now():
        return dict(
            now=datetime.datetime.now(),
        )

    @app.template_filter('highlight')
    def highlight_filter(s, q):
        qs = q.split()
        s = re.sub(
            r'({})'.format("|".join(qs)),
            r'<span class="bg-yellow">\g<1></span>',
            s,
            flags=re.IGNORECASE
        )
        return s


    @app.route('/')
    def index():
        return None

    return app