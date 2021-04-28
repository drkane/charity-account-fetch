import base64
import datetime
import io
import sys

from elasticsearch.exceptions import NotFoundError
import pdfplumber
from flask import current_app


class DocumentUploadError(Exception):
    pass


def convert_file(source):
    with pdfplumber.open(source) as pdf:
        content = "\n\n".join(
            [
                "<span id='page-{}'></span>\n{}".format(i, p.extract_text())
                for i, p in enumerate(pdf.pages)
                if p.extract_text()
            ]
        )
        if not content:
            raise DocumentUploadError("No content found in PDF")
        return {
            "content": content,
            "content_length": len(content),
            "pages": len(pdf.pages),
            "content_type": "application/pdf",
            "language": "en",
            "date": datetime.datetime.now(),
        }


def upload_doc(charity, content, es, skip_if_exists=False):
    id_ = "{}-{:%Y%m%d}".format(charity["regno"], charity["fye"])
    filename = id_ + ".pdf"

    if skip_if_exists:
        try:
            doc = es.get(
                index=current_app.config.get("ES_INDEX"),
                doc_type="_doc",
                id=id_,
                _source=False,
            )
            return {
                "_index": doc["_index"],
                "_type": doc["_type"],
                "_id": doc["_id"],
                "result": "already exists",
            }
        except NotFoundError:
            pass

    try:
        attachment = convert_file(io.BytesIO(content))
    except Exception as err:
        exc_type, value, traceback = sys.exc_info()
        return {
            "_index": current_app.config.get("ES_INDEX"),
            "_type": "_doc",
            "_id": id_,
            "result": "error",
            "error": f"{exc_type.__name__}: {str(err)}",
        }

    return es.index(
        index=current_app.config.get("ES_INDEX"),
        doc_type="_doc",
        id=id_,
        body={
            "filename": filename,
            "filedata": base64.b64encode(content).decode("utf8"),
            "attachment": attachment,
            **charity,
        },
    )
