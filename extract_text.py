import argparse
import logging
import os

import pdfplumber


def convert_file(source, dest=None, **kwargs):
    if not dest:
        dest = source.replace(".pdf", ".txt")

    logging.info("Converting {} to {}".format(source, dest))
    with pdfplumber.open(source) as pdf, open(dest, "w", encoding="utf8") as destfile:
        text = "\n----\n".join(
            [p.extract_text() for p in pdf.pages if p.extract_text()]
        )
        destfile.write(text)


def convert_folder(source, **kwargs):
    for f in os.listdir():
        if f.endswith(".pdf"):
            convert_file(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""Extract text from a PDF to a text file"""
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="More descriptive output"
    )

    subparsers = parser.add_subparsers(help="Operation to perform")

    folder_parser = subparsers.add_parser(
        "folder", help="Convert all PDF files in a folder to txt"
    )
    folder_parser.add_argument(
        "--source", default=".", help="Folder in which to look for PDFs"
    )
    folder_parser.set_defaults(func=convert_folder)

    file_parser = subparsers.add_parser("file", help="Convert a PDF file to TXT")
    file_parser.add_argument("source", help="PDF file to convert")
    file_parser.add_argument("--dest", default=None, help="destination file")
    file_parser.set_defaults(func=convert_file)

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    args.func(**args.__dict__)
