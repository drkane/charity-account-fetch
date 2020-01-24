from flask import Blueprint, render_template, jsonify, current_app, request
from docdisplay.db import get_db

bp = Blueprint('main', __name__, url_prefix='/')

@bp.route('/doc/<id>')
def doc_get(id):
    es = get_db()
    doc = es.get(
        index=current_app.config.get('ES_INDEX'),
        doc_type='_doc',
        id=id,
        _source_excludes=['filedata'],
    )
    return jsonify(doc)
    # return render_template('blog/index.html', posts=posts)

@bp.route('/search')
def doc_search():
    es = get_db()
    doc = es.search(
        index=current_app.config.get('ES_INDEX'),
        doc_type='_doc',
        q=request.args.get('q'),
        _source_excludes=['filedata'],
    )
    return jsonify(doc)
    # return render_template('blog/index.html', posts=posts)