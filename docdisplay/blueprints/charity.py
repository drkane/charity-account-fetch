import json
import math

from flask import Blueprint, render_template, current_app, request, url_for
from graphqlclient import GraphQLClient

from docdisplay.fetch import ccew_list_accounts

CC_ACCOUNT_FILENAME = r'([0-9]+)_AC_([0-9]{4})([0-9]{2})([0-9]{2})_E_C.PDF'

bp = Blueprint('charity', __name__, url_prefix='/charity')


def get_charity(regno):
    client = GraphQLClient(current_app.config.get('CHARITYBASE_API_URL'))
    client.inject_token(
        'Apikey ' + current_app.config.get('CHARITYBASE_API_KEY')
    )
    query = '''
    query fetchCharities($regno:ID){
        CHC {
            getCharities(filters: {id: [$regno]}) {
                list {
                    names(all:false) {
                        value
                        primary
                    }
                    finances(all:true) {
                        financialYear {
                            end
                        }
                        income
                        spending
                    }
                }
            }
        }
    }
    '''
    result = client.execute(query, {'regno': regno})
    result = json.loads(result)
    result = result.get('data', {}).get('CHC', {})\
                   .get('getCharities', {}).get('list', [])
    if result:
        return result[0]


def search_charities(q, limit=20, skip=0):
    if not q:
        return []
    client = GraphQLClient(current_app.config.get('CHARITYBASE_API_URL'))
    client.inject_token(
        'Apikey ' + current_app.config.get('CHARITYBASE_API_KEY')
    )
    query = '''
    query fetchCharities($q:String, $limit:PageLimit, $skip:Int){
        CHC {
            getCharities(filters: {search:$q}) {
                count
                list(limit:$limit, skip:$skip) {
                    id
                    names(all:false) {
                        value
                        primary
                    }
                    finances(all:true) {
                        financialYear {
                            begin
                        }
                    }
                }
            }
        }
    }
    '''
    result = client.execute(query, {
        'q': q,
        'limit': limit,
        'skip': skip,
    })
    result = json.loads(result)
    return {
        "count": result.get('data', {}).get('CHC', {})
                       .get('getCharities', {}).get('count', 0),
        "results": result.get('data', {}).get('CHC', {})
                         .get('getCharities', {}).get('list', [])
    }


@bp.route('/search')
def charity_search():
    q = request.values.get('q')
    try:
        p = int(request.values.get('p', 1))
    except ValueError:
        p = 1
    limit = 10
    skip = limit * (p - 1)

    results = search_charities(q, limit, skip)
    nav = {
        "first_result": ((p-1) * limit) + 1,
        "last_result": min([p * limit, results['count']]),
        "current_page": p,
        'first_page': 1,
        'last_page': math.ceil(results["count"] / limit),
    }

    if results['count'] > nav['last_result']:
        nav['last'] = url_for(
            'charity.charity_search',
            q=q,
            p=nav['last_page']
        )
        nav['next'] = url_for('charity.charity_search', q=q, p=p+1)
    if p > 2:
        nav['prev'] = url_for('charity.charity_search', q=q, p=p-1)
        nav['first'] = url_for(
            'charity.charity_search',
            q=q,
            p=nav['first_page']
        )

    return render_template(
        'charity_search.html',
        results=results,
        q=request.values.get('q', ''),
        nav=nav,
    )


@bp.route('/<regno>')
def charity_get(regno):
    accounts = ccew_list_accounts(regno)
    accounts = {
        "{:%Y-%m-%d}".format(a['fyend']): a
        for a in accounts
    }
    charity = get_charity(regno)
    charity['finances'] = [
        {
            **f,
            **accounts.get(f['financialYear']['end'][0:10], {})
        }
        for f in charity['finances']
    ]
    return render_template(
        'charity.html',
        results=accounts,
        charity=charity,
        regno=regno
    )
