import base64
import re
import datetime

from flask import (
    Blueprint, render_template, current_app, request,
    flash, redirect, url_for, make_response, jsonify
)
from werkzeug.utils import secure_filename
import requests
import requests_cache

from docdisplay.db import get_db
from docdisplay.utils import add_highlights
from docdisplay.upload import upload_doc

requests_cache.install_cache('demo_cache')

CC_ACCOUNT_FILENAME = r'([0-9]+)_AC_([0-9]{4})([0-9]{2})([0-9]{2})_E_C.PDF'

bp = Blueprint('doc', __name__, url_prefix='/doc')


@bp.route('/<id>.pdf')
def doc_get_pdf(id):
    es = get_db()
    doc = es.get(
        index=current_app.config.get('ES_INDEX'),
        doc_type='_doc',
        id=id,
        _source_includes=['filedata'],
    )
    return make_response(
        base64.b64decode(doc.get("_source", {}).get('filedata')),
        200,
        {
            "Content-type": "application/pdf",
            # "Content-Disposition": "attachment;filename={}.pdf".format(id)
        }
    )


@bp.route('/<id>')
def doc_get(id):
    es = get_db()
    doc = es.get(
        index=current_app.config.get('ES_INDEX'),
        doc_type='_doc',
        id=id,
        _source_excludes=['filedata'],
    )
    highlight = request.values.get('q')
    _, highlight_count = add_highlights(
        doc.get('_source', {}).get('attachment', {}).get('content', ''),
        q=highlight
    )
    return render_template(
        'doc_display.html',
        result=doc.get('_source'),
        id=id,
        highlight=highlight,
        highlight_count=highlight_count,
    )


@bp.route('/<id>/embed')
def doc_get_embed(id):
    es = get_db()
    doc = es.get(
        index=current_app.config.get('ES_INDEX'),
        doc_type='_doc',
        id=id,
        _source_excludes=['filedata'],
    )
    highlight = request.values.get('q')
    content, highlight_count = add_highlights(
        doc.get('_source', {}).get('attachment', {}).get('content', ''),
        q=highlight
    )
    return render_template(
        'doc_display_embed.html',
        content=content,
        id=id,
        highlight=highlight,
    )


@bp.route('/search')
def doc_search():
    es = get_db()
    q = request.values.get('q')
    results = None
    resultCount = 0
    if q:
        doc = es.search(
            index=current_app.config.get('ES_INDEX'),
            doc_type='_doc',
            q=request.values.get('q'),
            _source_excludes=['filedata'],
            body=dict(
                highlight={
                    "fields": {
                        "attachment.content": {
                            "fragment_size": 150,
                            "number_of_fragments": 3,
                            "pre_tags": ['<em class="bg-yellow b">'],
                            "post_tags": ['</em>'],
                        }
                    },
                    "encoder": 'html',
                }
            )
        )
        resultCount = doc.get('hits', {}).get('total', 0)
        if isinstance(resultCount, dict):
            resultCount = resultCount.get('value')
        results = doc.get('hits', {}).get('hits', [])
    return render_template(
        'doc_search.html',
        results=results,
        q=q,
        resultCount=resultCount,
    )


@bp.route('/bulkupload')
def doc_upload_bulk():
    return render_template('doc_upload_bulk.html')


@bp.route('/upload', methods=['GET', 'POST'])
@bp.route('/upload.<filetype>', methods=['GET', 'POST'])
def doc_upload(filetype='html'):
    if filetype not in ['json', 'html']:
        filetype = 'html'
    es = get_db()
    if request.method == 'POST':

        content = None

        # check file is provided
        doc = request.files.get('doc')
        url = request.values.get('url')
        if doc:

            # check the filename
            filename = secure_filename(doc.filename)
            content = doc.read()

        # download from an URL
        elif url:

            r = requests.get(url)
            if not r.status_code == requests.codes.ok:
                flash("Couldn't load from URL: {}".format(url), 'error')
                if filetype == 'json':
                    return jsonify({
                        'data': {},
                        'errors': ["Couldn't load from URL: {}".format(url)],
                    })
                return redirect(request.url)
            content = r.content
            filename = url
            if "Content-Disposition" in r.headers.keys():
                filename = re.findall(
                    "filename=(.+)",
                    r.headers["Content-Disposition"]
                )[0]
            else:
                filename = url.split("/")[-1]

        else:
            flash('No file found', 'error')
            if filetype == 'json':
                return jsonify({
                    'data': {},
                    'errors': ['No file found'],
                })
            return redirect(request.url)

        # check the filename
        if not filename.lower().endswith(".pdf"):
            flash('File must be a PDF', 'error')
            return redirect(request.url)

        charity = {
            "regno": request.values.get('regno'),
            "fye": request.values.get('fye'),
            "name": request.values.get('name'),
            "income": request.values.get('income'),
            "spending": request.values.get('spending'),
            "assets": request.values.get('assets'),
        }

        if not charity["regno"] or not charity["fye"]:
            nameparse = re.match(CC_ACCOUNT_FILENAME, filename, re.IGNORECASE)
            if nameparse:
                charity["regno"] = nameparse.group(1).lstrip('0')
                charity['fye'] = '{}-{}-{}'.format(
                    nameparse.group(2),
                    nameparse.group(3),
                    nameparse.group(4),
                )
            else:
                flash(
                    'Must provide charity number and financial year end',
                    'error'
                )
                if filetype == 'json':
                    return jsonify({
                        'data': {},
                        'errors': [
                            ('Must provide charity number ' +
                             ' and financial year end')
                        ],
                    })
                return redirect(request.url)

        charity["fye"] = datetime.datetime.strptime(charity['fye'], '%Y-%m-%d')

        result = upload_doc(
            charity,
            content,
            es
        )
        flash('Uploaded "{}"'.format(filename), 'message')
        if filetype == 'json':
            return jsonify({
                'data': {
                    'id': result.get('_id'),
                    'result': result.get('result'),
                },
                'errors': [],
            })
        return redirect(url_for('doc.doc_get', id=result.get('_id')))

    return render_template('doc_upload.html')
