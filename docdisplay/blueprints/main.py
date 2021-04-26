from flask import Blueprint, render_template, current_app

from docdisplay.db import get_db

CC_ACCOUNT_FILENAME = r"([0-9]+)_AC_([0-9]{4})([0-9]{2})([0-9]{2})_E_C.PDF"

bp = Blueprint("main", __name__, url_prefix="/")


@bp.route("/")
def index():
    es = get_db()
    count = es.count(
        index=current_app.config.get("ES_INDEX"),
        doc_type="_doc",
        body={"query": {"match_all": {}}},
    )
    return render_template("index.html.j2", docs=count.get("count", 0))
