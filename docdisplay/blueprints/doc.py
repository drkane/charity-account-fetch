import base64
import re
import datetime
import math
import os
import io
import csv
from pathlib import Path
import sys

import click
from flask import (
    Blueprint,
    render_template,
    current_app,
    request,
    flash,
    redirect,
    url_for,
    make_response,
    jsonify,
)
from werkzeug.utils import secure_filename
import requests
import requests_cache
from tqdm import tqdm
from elasticsearch.helpers import scan
from slugify import slugify

from docdisplay.db import get_db
from docdisplay.utils import add_highlights, get_nav
from docdisplay.upload import upload_doc, convert_file

requests_cache.install_cache("demo_cache")

CC_ACCOUNT_FILENAME = r"([0-9]+)_AC_([0-9]{4})([0-9]{2})([0-9]{2})_E_C.PDF"

bp = Blueprint("doc", __name__, url_prefix="/doc")


@bp.route("/<id>.pdf")
def doc_get_pdf(id):
    es = get_db()
    doc = es.get(
        index=current_app.config.get("ES_INDEX"),
        doc_type="_doc",
        id=id,
        _source_includes=["filedata"],
    )
    return make_response(
        base64.b64decode(doc.get("_source", {}).get("filedata")),
        200,
        {
            "Content-type": "application/pdf",
            # "Content-Disposition": "attachment;filename={}.pdf".format(id)
        },
    )


@bp.route("/<id>")
def doc_get(id):
    es = get_db()
    doc = es.get(
        index=current_app.config.get("ES_INDEX"),
        doc_type="_doc",
        id=id,
        _source_excludes=["filedata"],
    )
    highlight = request.values.get("q")
    _, highlight_count = add_highlights(
        doc.get("_source", {}).get("attachment", {}).get("content", ""), q=highlight
    )
    return render_template(
        "doc_display.html.j2",
        result=doc.get("_source"),
        id=id,
        highlight=highlight,
        highlight_count=highlight_count,
    )


@bp.route("/<id>/embed")
def doc_get_embed(id):
    es = get_db()
    doc = es.get(
        index=current_app.config.get("ES_INDEX"),
        doc_type="_doc",
        id=id,
        _source_excludes=["filedata"],
    )
    highlight = request.values.get("q")
    content, highlight_count = add_highlights(
        doc.get("_source", {}).get("attachment", {}).get("content", ""), q=highlight
    )
    return render_template(
        "doc_display_embed.html.j2",
        content=content,
        id=id,
        highlight=highlight,
    )


@bp.route("/search")
@bp.route("/search.<filetype>")
def doc_search(filetype="html"):
    es = get_db()
    q = request.values.get("q")

    try:
        p = int(request.values.get("p", 1))
    except ValueError:
        p = 1
    limit = 10
    skip = limit * (p - 1)

    results = None
    resultCount = 0
    nav = {}
    if q:
        params = dict(
            index=current_app.config.get("ES_INDEX"),
            doc_type="_doc",
            q=request.values.get("q"),
        )
        if filetype == "csv":
            doc = scan(
                es,
                **params,
                _source_excludes=["filedata", "attachment"],
            )
            buffer = io.StringIO()
            fields = [
                "regno",
                "fye",
                "filename",
                "name",
                "income",
                "spending",
                "assets",
                "search term",
            ]
            writer = csv.DictWriter(buffer, fieldnames=fields)
            writer.writeheader()
            for k, result in enumerate(doc):
                row = {
                    "search term": q,
                    **result["_source"],
                }
                writer.writerow(row)
            output = make_response(buffer.getvalue())
            output.headers["Content-Disposition"] = f"attachment; filename=account_search_{slugify(q, separator='_')}.csv"
            output.headers["Content-type"] = "text/csv"
            return output
        doc = es.search(
            **params,
            _source_excludes=["filedata"],
            body=dict(
                highlight={
                    "fields": {
                        "attachment.content": {
                            "fragment_size": 150,
                            "number_of_fragments": 3,
                            "pre_tags": ['<em class="bg-yellow b">'],
                            "post_tags": ["</em>"],
                        }
                    },
                    "encoder": "html",
                }
            ),
            from_=skip,
            size=limit,
        )
        resultCount = doc.get("hits", {}).get("total", 0)
        if isinstance(resultCount, dict):
            resultCount = resultCount.get("value")

        nav = get_nav(
            p,
            limit,
            resultCount,
            "doc.doc_search",
            dict(q=q),
        )
        results = doc.get("hits", {}).get("hits", [])
    return render_template(
        "doc_search.html.j2",
        results=results,
        q=q,
        resultCount=resultCount,
        nav=nav,
        downloadUrl=url_for("doc.doc_search", q=q, filetype="csv"),
    )


@bp.route("/bulkupload")
def doc_upload_bulk():
    return render_template("doc_upload_bulk.html.j2")


@bp.route("/all_docs")
def doc_all_docs():
    es = get_db()
    page = int(request.values.get("p", 0))
    page_size = 10
    res = es.search(
        index=current_app.config.get("ES_INDEX"),
        doc_type="_doc",
        _source_excludes=["filedata", "attachment"],
        body={"size": page_size, "from": page_size * page, "query": {"match_all": {}}},
    )
    resultCount = res.get("hits", {}).get("total", 0)
    if isinstance(resultCount, dict):
        resultCount = resultCount.get("value")
    maxPage = math.ceil(resultCount / page_size)
    results = res.get("hits", {}).get("hits", [])
    return render_template(
        "doc_all_docs.html.j2",
        results=results,
        resultCount=resultCount,
        page=page,
        maxPage=maxPage,
        page_size=page_size,
    )


@bp.route("/upload", methods=["GET", "POST"])
@bp.route("/upload.<filetype>", methods=["GET", "POST"])
def doc_upload(filetype="html"):
    if filetype not in ["json", "html"]:
        filetype = "html"
    es = get_db()
    if request.method == "POST":

        content = None

        # check file is provided
        doc = request.files.get("doc")
        url = request.values.get("url")
        if doc:

            # check the filename
            filename = secure_filename(doc.filename)
            content = doc.read()

        # download from an URL
        elif url:

            r = requests.get(url)
            if not r.status_code == requests.codes.ok:
                flash("Couldn't load from URL: {}".format(url), "error")
                if filetype == "json":
                    return jsonify(
                        {
                            "data": {},
                            "errors": ["Couldn't load from URL: {}".format(url)],
                        }
                    )
                return redirect(request.url)
            content = r.content
            if "Content-Disposition" in r.headers.keys():
                filename = re.findall(
                    "filename=(.+)", r.headers["Content-Disposition"]
                )[0].strip('"')
            elif request.values.get("regno") and request.values.get("fye"):
                filename = "{}_{:%Y%m%d}.pdf".format(
                    request.values.get("regno"), request.values.get("fye")
                )
            else:
                filename = "annual_accounts.pdf"

        else:
            flash("No file found", "error")
            if filetype == "json":
                return jsonify(
                    {
                        "data": {},
                        "errors": ["No file found"],
                    }
                )
            return redirect(request.url)

        # check the filename
        if not filename.lower().endswith(".pdf"):
            flash("File must be a PDF", "error")
            return redirect(request.url)

        charity = {
            "regno": request.values.get("regno"),
            "fye": request.values.get("fye"),
            "name": request.values.get("name"),
            "income": request.values.get("income"),
            "spending": request.values.get("spending"),
            "assets": request.values.get("assets"),
        }

        if not charity["regno"] or not charity["fye"]:
            nameparse = re.match(CC_ACCOUNT_FILENAME, filename, re.IGNORECASE)
            if nameparse:
                charity["regno"] = nameparse.group(1).lstrip("0")
                charity["fye"] = "{}-{}-{}".format(
                    nameparse.group(2),
                    nameparse.group(3),
                    nameparse.group(4),
                )
            else:
                flash("Must provide charity number and financial year end", "error")
                if filetype == "json":
                    return jsonify(
                        {
                            "data": {},
                            "errors": [
                                (
                                    "Must provide charity number "
                                    " and financial year end"
                                )
                            ],
                        }
                    )
                return redirect(request.url)

        charity["fye"] = datetime.datetime.strptime(charity["fye"], "%Y-%m-%d")

        result = upload_doc(charity, content, es)
        flash('Uploaded "{}"'.format(filename), "message")
        if filetype == "json":
            return jsonify(
                {
                    "data": {
                        "id": result.get("_id"),
                        "result": result.get("result"),
                    },
                    "errors": [],
                }
            )
        return redirect(url_for("doc.doc_get", id=result.get("_id")))

    return render_template("doc_upload.html.j2")


@bp.cli.command('upload')
@click.argument('input_path', type=click.Path(exists=True, file_okay=True, dir_okay=True))
@click.option('--debug/--no-debug', default=False)
def cli_upload(input_path, debug):

    def file_generator(directory):
        pathlist = Path(directory).glob('**/*.pdf')
        for filename in pathlist:
            yield filename

    if os.path.isdir(input_path):
        files = file_generator(input_path)
    else:
        files = [input_path]

    for filepath in tqdm(files):
        with open(filepath, "rb") as pdffile:
            filename = os.path.basename(filepath)
            regno, fyend = filename.rstrip(".pdf").split("_")
            fyend = datetime.date(
                int(fyend[0:4]),
                int(fyend[4:6]),
                int(fyend[6:8]),
            )
            charity = {
                "regno": regno,
                "fye": fyend,
                # "name": request.values.get("name"),
                # "income": request.values.get("income"),
                # "spending": request.values.get("spending"),
                # "assets": request.values.get("assets"),
            }
            if debug:
                click.echo(f"Uploading document: {pdffile.name}")
            result = upload_doc(
                charity,
                pdffile.read(),
                get_db()
            )
            if result["result"] in ("created", "updated"):
                if debug:
                    click.echo(click.style(f"Document {result['result']}: {pdffile.name}", fg='green'))
            else:
                click.echo(click.style(f"ERROR Could not upload document: {pdffile.name}", fg='white', bg='red'), err=True)
                print(result)


@bp.cli.command('check_pdf')
@click.argument('input_path', type=click.Path(exists=True, file_okay=True, dir_okay=True))
@click.option('--debug/--no-debug', default=False)
def cli_check_pdf(input_path, debug):

    def file_generator(directory):
        pathlist = Path(directory).glob('**/*.pdf')
        for filename in pathlist:
            yield filename

    if os.path.isdir(input_path):
        files = file_generator(input_path)
    else:
        files = [input_path]

    for filepath in files:
        with open(filepath, "rb") as pdffile:
            try:
                convert_file(pdffile)
            except Exception as err:
                exc_type, value, traceback = sys.exc_info()
                click.echo(
                    click.style(f"ERROR Could not upload document: {pdffile.name}", fg='white', bg='red') + f" {exc_type.__name__}: {str(err)}",
                    err=True
                )
