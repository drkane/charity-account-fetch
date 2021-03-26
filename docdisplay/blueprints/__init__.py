from . import doc
from . import main
from . import charity


def init_app(app):
    app.register_blueprint(main.bp)
    app.register_blueprint(doc.bp)
    app.register_blueprint(charity.bp)
