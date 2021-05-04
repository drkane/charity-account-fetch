import math
from datetime import date, datetime

from flask import url_for


def filesize_text_to_int(filesize: str) -> int:
    """
    Convert file size text to an int

    Sizes are generally in the format "(12,345KB)"
    """
    filesize = filesize.replace("(", "").replace(")", "").replace(",", "").upper()
    if "KB" in filesize:
        return int(filesize.replace("KB", "")) * 1024
    elif "KIB" in filesize:
        return int(filesize.replace("KIB", "")) * 1000
    return int(filesize)


def parse_datetime(d: str, f: str = "%Y-%m-%d", output_format=None) -> date:
    """
    Parse a date from a string
    """
    d = datetime.strptime(d, f).date()
    if output_format:
        return d.strftime(output_format)
    return d


def get_nav(p, limit, result_count, url_base, url_args):
    nav = {
        "first_result": ((p - 1) * limit) + 1,
        "last_result": min([p * limit, result_count]),
        "current_page": p,
        "first_page": 1,
        "last_page": math.ceil(result_count / limit),
    }

    if result_count > nav["last_result"]:
        nav["last"] = url_for(url_base, **url_args, p=nav["last_page"])
        nav["next"] = url_for(url_base, **url_args, p=p + 1)
    if p >= 2:
        nav["prev"] = url_for(url_base, **url_args, p=p - 1)
        nav["first"] = url_for(url_base, **url_args, p=nav["first_page"])

    return nav
