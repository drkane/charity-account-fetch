from . import doc
from . import main


def init_app(app):
    app.register_blueprint(main.bp)
    app.register_blueprint(doc.bp)
