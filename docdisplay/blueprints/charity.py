from flask import Blueprint, render_template

from docdisplay.fetch import ccew_list_accounts

CC_ACCOUNT_FILENAME = r'([0-9]+)_AC_([0-9]{4})([0-9]{2})([0-9]{2})_E_C.PDF'

bp = Blueprint('charity', __name__, url_prefix='/charity')


@bp.route('/<regno>')
def charity_get(regno):
    accounts = ccew_list_accounts(regno)
    return render_template('charity.html', results=accounts, regno=regno)
