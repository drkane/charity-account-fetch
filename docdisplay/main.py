from flask import Blueprint, render_template, jsonify, current_app, request
import requests
import requests_cache

from docdisplay.db import get_db
from docdisplay.fetch import ccew_list_accounts

requests_cache.install_cache('demo_cache')

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

@bp.route('/doc/search')
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

@bp.route('/search')
def charity_search():
    CC_URL = 'https://beta.charitycommission.gov.uk/umbraco/api/charityApi/getSearchResults'
    cc_params = {
        'searchText': request.args.get('q'),
        'pageNumber': 1,
        'contextId': 1126,
    }
    r = requests.get(CC_URL, params=cc_params)
    return render_template('charitysearch.html', results=r.json().get('pageItems', []), q=request.args.get('q', ''))

@bp.route('/charity/<regno>')
def charity_get(regno):
    accounts = ccew_list_accounts(regno)
    return render_template('charity.html', results=accounts, regno=regno)
