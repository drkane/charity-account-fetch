import io
import base64
import datetime

from flask import current_app
import pdfplumber


def convert_file(source):
    with pdfplumber.open(source) as pdf:
        content = "\n\n".join(
            [
                "<span id='page-{}'></span>\n{}".format(i, p.extract_text())
                for i, p in enumerate(pdf.pages)
                if p.extract_text()
            ]
        )
        return {
            "content": content,
            "content_length": len(content),
            "pages": len(pdf.pages),
            "content_type": "application/pdf",
            "language": "en",
            "date": datetime.datetime.now(),
        }


def upload_doc(charity, content, es):
    id_ = "{}-{:%Y%m%d}".format(charity["regno"], charity["fye"])
    filename = id_ + ".pdf"
    attachment = convert_file(io.BytesIO(content))

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
