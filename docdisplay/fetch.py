import os
from datetime import date, datetime
import csv
import logging

import click
from flask import current_app
from flask.cli import AppGroup
import requests
import dateutil.parser
from requests_html import HTMLSession

from docdisplay.utils import parse_datetime
from docdisplay.cc_api import CharityCommissionAPI

fetch_cli = AppGroup("fetch")
CCEW_URL = "https://register-of-charities.charitycommission.gov.uk/charity-search/-/charity-details/{}/accounts-and-annual-returns"


def get_charity_url(regno):
    api = CharityCommissionAPI(current_app.config.get('CCEW_API_KEY'))
    org_details = api.GetCharityDetails(RegisteredNumber=regno)
    return CCEW_URL.format(org_details["organisation_number"])


class StripLinkText(str):
    def __eq__(self, other):
        return self.strip() == other.strip()


def print_header(s: str, underline: str = "="):
    print(s)
    print(underline * len(s))


def ccew_list_accounts(regno: str, session=HTMLSession()) -> list:
    """
    List accounts for a charity
    """
    url = get_charity_url(regno)
    logging.debug("Fetching account list: {}".format(url))

    r = session.get(url)
    accounts = []
    for tr in r.html.find("tr.govuk-table__row"):
        cells = list(tr.find("td"))
        cell_text = [c.text.strip() if c.text else "" for c in cells]
        if not cell_text or "accounts" not in cell_text[0].lower():
            continue
        if not cells[-1].find("a"):
            continue
        accounts.append(
            {
                "url": cells[-1].find("a", first=True).attrs["href"],
                "fyend": dateutil.parser.parse(cell_text[1]).date(),
                "size": None,
            }
        )
    return sorted(accounts, key=lambda x: x["fyend"], reverse=True)


def download_account(
    url: str,
    regno: str,
    fyend: date,
    destination: str = ".",
    session=None,
) -> dict:
    """
    Download a charity account from an URL
    """

    if not session:
        session = requests.Session()

    filename = "{}_{:%Y%m%d}.pdf".format(regno, fyend)
    r = session.get(url)
    logging.debug("Fetching account PDF: {}".format(url))
    if getattr(r, "from_cache", False):
        logging.debug("Used cache")
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        logging.error("Account not found: {}".format(url))
        return {"error": "Account not found"}

    if not os.path.exists(destination):
        logging.debug("Creating directory: {}".format(destination))
        os.makedirs(destination)

    dest = os.path.join(destination, filename)
    logging.debug("Saving to: {}".format(dest))
    with open(dest, "wb") as f:
        f.write(r.content)

    return {
        "file_location": dest,
        "file_name": filename,
        "file_size": len(r.content),
        "download_timetaken": r.elapsed.total_seconds(),
    }


@fetch_cli.command("list")
@click.argument("regno")
@click.option("--destination", default=".", help="Folder in which to save accounts")
def list_accounts_for_download(regno: str, destination: str = ".", **kwargs: dict):
    """List all accounts for charity number REGNO.

    \b
    REGNO is the charity number
    """
    accounts = ccew_list_accounts(regno)
    if not accounts:
        print("No accounts found for charity number {}".format(regno))
        exit()
    print()
    print_header("Accounts for charity number {}".format(regno))
    for k, a in enumerate(accounts):
        print("{}: {:%Y-%m-%d}".format(k + 1, a["fyend"]))

    print("Enter account number to download:")
    to_download = input()
    to_download = int(to_download) - 1
    download_account(
        accounts[to_download]["url"],
        regno=regno,
        fyend=accounts[to_download]["fyend"],
        destination=destination,
    )


@fetch_cli.command("latest")
@click.argument("regno")
@click.option("--destination", default=".", help="Folder in which to save accounts")
def download_latest_account(regno: str, destination: str = ".", **kwargs: dict):
    """Download the latest account for charity number REGNO.

    \b
    REGNO is the charity number
    """
    accounts = ccew_list_accounts(regno)
    download_account(
        accounts[0]["url"],
        regno=regno,
        fyend=accounts[0]["fyend"],
        destination=destination,
    )


@fetch_cli.command("all")
@click.argument("regno")
@click.option("--destination", default=".", help="Folder in which to save accounts")
def download_all_accounts(regno: str, destination: str = ".", **kwargs: dict):
    """Download all available accounts for charity number REGNO.

    \b
    REGNO is the charity number
    """
    session = HTMLSession()
    accounts = ccew_list_accounts(regno, session=session)
    for a in accounts:
        download_account(
            a["url"],
            regno=regno,
            fyend=a["fyend"],
            destination=destination,
            session=session,
        )


@fetch_cli.command("account")
@click.argument("regno")
@click.argument("fyend", type=parse_datetime)
@click.option("--destination", default=".", help="Folder in which to save accounts")
def download_account_parser(regno: str, fyend: date, destination: str = ".", **kwargs):
    """Download account for FYEND for REGNO.

    \b
    REGNO is the charity number
    FYEND is the financial year end of the accounts (format YYYY-MM-DD)
    """
    session = HTMLSession()
    accounts = ccew_list_accounts(regno, session=session)
    for account in accounts:
        if account["fyend"] == fyend:
            download_account(
                account["url"],
                regno=regno,
                fyend=fyend,
                destination=destination,
                session=session,
            )
            return
    print("Account not found")


@fetch_cli.command("csv")
@click.argument("csvfile", type=click.File("r"))
@click.option(
    "--regno-column",
    default="regno",
    help="Name of the column with a charity number in",
)
@click.option(
    "--fyend-column",
    default="fyend",
    help="""Name of the column with the financial year end in
    (if not found then the latest accounts will be used)""",
)
@click.option(
    "--destination", type=click.Path(), default=".", help="Folder in which to save accounts"
)
@click.option("--logfile", type=click.Path(), help="File to output results")
@click.option(
    "--skip-rows",
    type=int,
    default=0,
    help="Number of rows to skip when parsing file",
)
def download_from_csv(
    csvfile,
    regno_column: str = "regno",
    fyend_column: str = "fyend",
    destination: str = ".",
    logfile=None,
    skip_rows: int = 0,
    **kwargs
):
    """Download accounts for a selection of charities from CSVFILE"""
    reader = csv.DictReader(csvfile)
    session = HTMLSession()

    logging_fields = [
        "success",
        "error",
        "fetch_datetime",
        "file_location",
        "file_name",
        "file_size",
        "download_timetaken",
    ]

    for k, row in enumerate(reader):

        if logfile and k == 0:
            with open(logfile, "w", newline="") as logf:
                writer = csv.writer(logf)
                writer.writerow(
                    [h for h in row.keys() if h not in logging_fields] + logging_fields
                )

        if skip_rows and skip_rows > k:
            result = {"error": "Row skipped"}

        else:
            regno = row[regno_column]
            fyend = row.get(fyend_column)
            result = {}
            accounts = ccew_list_accounts(regno, session=session)
            urls = {account["fyend"]: account["url"] for account in accounts}
            if fyend and urls.get(fyend):
                fyend = parse_datetime(fyend)
                result = download_account(
                    urls[fyend],
                    regno=regno,
                    fyend=fyend,
                    destination=destination,
                    session=session,
                )
            elif accounts:
                result = download_account(
                    accounts[0]["url"],
                    regno=regno,
                    fyend=accounts[0]["fyend"],
                    destination=destination,
                    session=session,
                )
            else:
                result = {
                    "error": "no accounts found"
                }

        if logfile:
            with open(logfile, "a", newline="") as logf:
                writer = csv.writer(logf)
                writer.writerow(
                    [v for h, v in row.items() if h not in logging_fields]
                    + [
                        result.get("file_location") is not None,
                        result.get("error"),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        result.get("file_location"),
                        result.get("file_name"),
                        result.get("file_size"),
                        result.get("download_timetaken"),
                    ]
                )
