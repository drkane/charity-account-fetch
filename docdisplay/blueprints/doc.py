import base64
import csv
import datetime
import io
import os
import re
import sys
from pathlib import Path

import click
import requests
import requests_cache
from elasticsearch import NotFoundError
from elasticsearch.helpers import scan
from flask import (
    Blueprint,
    Markup,
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from slugify import slugify
from tqdm import tqdm
from werkzeug.utils import secure_filename

from docdisplay.db import get_db
from docdisplay.upload import convert_file, upload_doc
from docdisplay.utils import get_nav

requests_cache.install_cache("demo_cache")

CC_ACCOUNT_FILENAME = r"([0-9]+)_AC_([0-9]{4})([0-9]{2})([0-9]{2})_E_C.PDF"

bp = Blueprint("doc", __name__, url_prefix="/doc")


def get_doc(id, q=None):
    highlight_class = 'data-charity-account-highlight="true"'
    es = get_db()
    body = {
        "query": {
            "terms": {
                "_id": [id],
            }
        }
    }
    if q:
        body["highlight"] = {
            "fields": {
                "attachment.content": {
                    "number_of_fragments": 0,
                    "pre_tags": [
                        f'<em class="bg-yellow b highlight" {highlight_class}>'
                    ],
                    "post_tags": ["</em>"],
                    "highlight_query": {
                        "simple_query_string": {
                            "query": q,
                            "fields": ["attachment.content"],
                            "default_operator": "or",
                        }
                    },
                }
            },
            "encoder": "html",
        }
    search_doc = es.search(
        index=current_app.config.get("ES_INDEX"),
        doc_type="_doc",
        body=body,
        _source_excludes=["filedata"],
    )
    if search_doc.get("hits", {}).get("hits", []):
        doc = search_doc.get("hits", {}).get("hits", [])[0]
        if doc.get("highlight", {}).get("attachment.content"):
            content = doc["highlight"]["attachment.content"][0]
            content = Markup(content).unescape()
            doc["_highlight_count"] = content.count(highlight_class)
            doc["_source"]["attachment"]["content"] = content
        return doc


@bp.route("/<id>.pdf")
def doc_get_pdf(id):
    es = get_db()
    try:
        doc = es.get(
            index=current_app.config.get("ES_INDEX"),
            doc_type="_doc",
            id=id,
            _source_includes=["filedata"],
        )
    except NotFoundError:
        abort(404, description=f"Could not find document (id: [{id}])")
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
    highlight = request.values.get("q")
    doc = get_doc(id, highlight)
    if not doc:
        abort(404, description=f"Could not find document (id: [{id}])")
    return render_template(
        "doc_display.html.j2",
        result=doc.get("_source"),
        id=id,
        highlight=highlight,
        highlight_count=doc.get("_highlight_count", 0),
    )


@bp.route("/<id>/embed")
def doc_get_embed(id):
    highlight = request.values.get("q")
    doc = get_doc(id, highlight)
    if not doc:
        abort(404, description=f"Could not find document (id: [{id}])")
    content = doc.get("_source", {}).get("attachment", {}).get("content", "")
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
            _source_excludes=["filedata", "attachment.content"],
            body={
                "query": {
                    "simple_query_string": {
                        "query": request.values.get("q"),
                        "fields": ["attachment.content"],
                        "default_operator": "or",
                    }
                }
            },
        )
        if filetype == "csv":
            params["query"] = params.pop("body")
            doc = scan(
                es,
                **params,
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
                    **{k: v for k, v in result["_source"].items() if k in fields},
                }
                writer.writerow(row)
            output = make_response(buffer.getvalue())
            output.headers[
                "Content-Disposition"
            ] = f"attachment; filename=account_search_{slugify(q, separator='_')}.csv"
            output.headers["Content-type"] = "text/csv"
            return output
        params["body"]["highlight"] = {
            "fields": {
                "attachment.content": {
                    "fragment_size": 150,
                    "number_of_fragments": 3,
                    "pre_tags": ['<em class="bg-yellow b highlight">'],
                    "post_tags": ["</em>"],
                }
            },
            "encoder": "html",
        }
        doc = es.search(
            **params,
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
        for r in results:
            r["highlight"]["attachment.content"] = [
                Markup(s).unescape() for s in r["highlight"]["attachment.content"]
            ]
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
@bp.route("/all_docs.<filetype>")
def doc_all_docs(filetype="html"):
    es = get_db()

    try:
        p = int(request.values.get("p", 1))
    except ValueError:
        p = 1
    limit = 10
    skip = limit * (p - 1)

    results = None
    resultCount = 0
    nav = {}

    if filetype == "csv":
        doc = scan(
            es,
            index=current_app.config.get("ES_INDEX"),
            doc_type="_doc",
            _source_excludes=["filedata", "attachment"],
            request_timeout=1000,
        )
        fields = [
            "regno",
            "fye",
            "filename",
            "name",
            "income",
            "spending",
            "assets",
        ]

        def generate_csv():
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=fields)
            writer.writeheader()
            yield buffer.getvalue()

            for result in doc:
                buffer = io.StringIO()
                writer = csv.DictWriter(buffer, fieldnames=fields)
                writer.writerow(result["_source"])
                yield buffer.getvalue()

        return Response(
            generate_csv(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=all_accounts.csv",
                "Content-type": "text/csv",
            },
        )

    res = es.search(
        index=current_app.config.get("ES_INDEX"),
        doc_type="_doc",
        _source_excludes=["filedata", "attachment"],
        body={"size": limit, "from": skip, "query": {"match_all": {}}},
    )
    resultCount = res.get("hits", {}).get("total", 0)
    if isinstance(resultCount, dict):
        resultCount = resultCount.get("value")

    nav = get_nav(
        p,
        limit,
        resultCount,
        "doc.doc_all_docs",
        dict(),
    )
    results = res.get("hits", {}).get("hits", [])
    return render_template(
        "doc_all_docs.html.j2",
        results=results,
        resultCount=resultCount,
        nav=nav,
        downloadUrl=url_for("doc.doc_all_docs", filetype="csv"),
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


@bp.cli.command("upload")
@click.argument(
    "input_path", type=click.Path(exists=True, file_okay=True, dir_okay=True)
)
@click.option("--debug/--no-debug", default=False)
@click.option("--skip-if-exists/--no-skip-if-exists", default=False)
def cli_upload(input_path, debug, skip_if_exists=False):
    def file_generator(directory):
        pathlist = Path(directory).glob("**/*.pdf")
        for filename in pathlist:
            yield filename

    if os.path.isdir(input_path):
        files = file_generator(input_path)
    else:
        files = [input_path]

    for filepath in tqdm(files):
        filesize = os.path.getsize(filepath)
        if filesize > current_app.config["FILE_SIZE_LIMT"]:
            click.echo(
                click.style(
                    f"ERROR Filesize too big: {filepath} [{filesize}]",
                    fg="white",
                    bg="red",
                ),
                err=True,
            )
            continue

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
                charity, pdffile.read(), get_db(), skip_if_exists=skip_if_exists
            )
            if result["result"] in ("created", "updated", "already exists"):
                if debug:
                    click.echo(
                        click.style(
                            f"Document {result['result']}: {pdffile.name}", fg="green"
                        )
                    )
            else:
                click.echo(
                    click.style(
                        f"ERROR Could not upload document: {pdffile.name}",
                        fg="white",
                        bg="red",
                    ),
                    err=True,
                )
                print(result)


@bp.cli.command("check_pdf")
@click.argument(
    "input_path", type=click.Path(exists=True, file_okay=True, dir_okay=True)
)
@click.option("--debug/--no-debug", default=False)
def cli_check_pdf(input_path, debug):
    def file_generator(directory):
        pathlist = Path(directory).glob("**/*.pdf")
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
                    click.style(
                        f"ERROR Could not upload document: {pdffile.name}",
                        fg="white",
                        bg="red",
                    )
                    + f" {exc_type.__name__}: {str(err)}",
                    err=True,
                )
