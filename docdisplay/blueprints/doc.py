import base64
import re
import datetime

from flask import (
    Blueprint, render_template, current_app, request,
    flash, redirect, url_for, make_response
)
from werkzeug.utils import secure_filename

from docdisplay.db import get_db
from docdisplay.utils import add_highlights

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
    highlight = request.args.get('q')
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
    highlight = request.args.get('q')
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
    q = request.args.get('q')
    results = None
    resultCount = 0
    if q:
        doc = es.search(
            index=current_app.config.get('ES_INDEX'),
            doc_type='_doc',
            q=request.args.get('q'),
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


@bp.route('/upload', methods=['GET', 'POST'])
def doc_upload():
    es = get_db()
    if request.method == 'POST':

        # check file is provided
        doc = request.files.get('doc')
        if 'doc' not in request.files:
            flash('No file part')
            return redirect(request.url)

        # check the filename
        filename = secure_filename(doc.filename)
        if not filename.lower().endswith(".pdf"):
            flash('File must be a PDF')
            return redirect(request.url)

        charity = {
            "regno": request.args.get('regno'),
            "name": request.args.get('name'),
            "fye": request.args.get('fye'),
            "income": request.args.get('income'),
            "spending": request.args.get('spending'),
            "assets": request.args.get('assets'),
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
                flash('Must provide charity number and financial year end')
        charity["fye"] = datetime.datetime.strptime(charity['fye'], '%Y-%m-%d')

        id = "{}-{:%Y%m%d}".format(charity['regno'], charity['fye'])
        _ = es.index(
            index=current_app.config.get('ES_INDEX'),
            doc_type='_doc',
            id=id,
            body={
                "filename": filename,
                "filedata": base64.b64encode(doc.read()).decode('utf8'),
                **charity
            },
            pipeline=current_app.config.get('ES_PIPELINE'),
        )
        flash('Uploaded "{}"'.format(filename))
        return redirect(url_for('main.doc_get', id=id))
    return render_template('doc_upload.html')
