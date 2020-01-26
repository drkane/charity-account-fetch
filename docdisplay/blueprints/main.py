from flask import Blueprint, render_template, request
import requests
import requests_cache

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
    r = requests.get(CC_URL, params=cc_params)
    return render_template(
        'charitysearch.html',
        results=r.json().get('pageItems', []),
        q=request.args.get('q', '')
    )
