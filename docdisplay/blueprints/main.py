from flask import Blueprint, render_template, request, current_app
import requests
import requests_cache

from docdisplay.db import get_db

requests_cache.install_cache('demo_cache')

CC_ACCOUNT_FILENAME = r'([0-9]+)_AC_([0-9]{4})([0-9]{2})([0-9]{2})_E_C.PDF'

bp = Blueprint('main', __name__, url_prefix='/')


@bp.route('/search')
def charity_search():
    CC_URL = 'https://beta.charitycommission.gov.uk/' + \
             'umbraco/api/charityApi/getSearchResults'
    cc_params = {
        'searchText': request.args.get('q'),
        'pageNumber': 1,
        'contextId': 1126,
    }
    results = []
    if cc_params["searchText"]:
        r = requests.get(CC_URL, params=cc_params)
        results = r.json().get('pageItems', [])
    return render_template(
        'charitysearch.html',
        results=results,
        q=request.args.get('q', '')
    )


@bp.route('/')
def index():
    es = get_db()
    count = es.count(
        index=current_app.config.get('ES_INDEX'),
        doc_type='_doc',
        body={
            "query": {
                "match_all": {}
            }
        }
    )
    return render_template('index.html', docs=count.get('count', 0))
