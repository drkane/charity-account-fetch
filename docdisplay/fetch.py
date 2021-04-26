import csv
import logging
import os
import re
import sys
from collections import namedtuple
from datetime import date, datetime

import click
import dateutil.parser
import requests
from flask import current_app
from flask.cli import AppGroup
from requests_html import HTMLSession
from tqdm import tqdm

from docdisplay.cc_api import CharityCommissionAPI
from docdisplay.utils import parse_datetime

fetch_cli = AppGroup("fetch")


Account = namedtuple("Account", ["url", "fyend", "regno", "size"], defaults=[None])


class CharityFetchError(Exception):
    pass


class CCEW:

    name = "ccew"
    url_base = "https://register-of-charities.charitycommission.gov.uk/charity-search/-/charity-details/{}/accounts-and-annual-returns"
    date_regex = r"([0-9]{1,2} [A-Za-z]+ [0-9]{4})"

    def __init__(self, api_key):
        self.api_key = api_key

    def get_charity_url(self, regno):
        regno = regno.lstrip("GB-CHC-")
        api = CharityCommissionAPI(self.api_key)
        org_details = api.GetCharityDetails(RegisteredNumber=regno)
        if "organisation_number" not in org_details:
            raise CharityFetchError("Charity {} not found".format(regno))
        return self.url_base.format(org_details["organisation_number"])

    def list_accounts(self, regno: str, session=HTMLSession()) -> list:
        """
        List accounts for a charity
        """
        url = self.get_charity_url(regno)
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
            date_string = re.match(self.date_regex, cell_text[1])
            if date_string:
                accounts.append(
                    Account(
                        regno=regno,
                        url=cells[-1].find("a", first=True).attrs["href"],
                        fyend=dateutil.parser.parse(date_string.group()).date(),
                    )
                )
        return sorted(accounts, key=lambda x: x.fyend, reverse=True)


class CCNI:

    name = "ccni"
    url_base = (
        "https://www.charitycommissionni.org.uk/charity-details/?regId={}&subId=0"
    )
    date_regex = r"([0-9]{1,2} [A-Za-z]+ [0-9]{4})"
    account_url_regex = r"https://apps.charitycommission.gov.uk/ccni_ar_attachments/([0-9]+)_([0-9]+)_CA.pdf"

    def get_charity_url(self, regno):
        regno = regno.lstrip("GB-NIC-").lstrip("NI")
        return self.url_base.format(regno)

    def list_accounts(self, regno: str, session=HTMLSession()) -> list:
        """
        List accounts for a charity
        """
        url = self.get_charity_url(regno)
        logging.debug("Fetching account list: {}".format(url))

        r = session.get(url)
        accounts = []
        for link in r.html.find("article#documents a"):
            if not link.attrs["href"].endswith("_CA.pdf"):
                continue
            match = re.match(self.account_url_regex, link.attrs["href"])
            if not match:
                continue
            accounts.append(
                Account(
                    regno=match.group(1).lstrip("0"),
                    url=link.attrs["href"],
                    fyend=dateutil.parser.parse(match.group(2)).date(),
                )
            )
        return sorted(accounts, key=lambda x: x.fyend, reverse=True)


class OSCR:
    name = "oscr"
    url_base = "https://www.oscr.org.uk/about-charities/search-the-register/charity-details?number={}"

    def get_charity_url(self, regno):
        regno = int(regno.lstrip("GB-SC-").lstrip("SC").lstrip("0"))
        return self.url_base.format(regno)

    def list_accounts(self, regno: str, session=HTMLSession()) -> list:
        """
        List accounts for a charity
        """
        url = self.get_charity_url(regno)
        logging.debug("Fetching account list: {}".format(url))

        r = session.get(url)
        accounts = []
        for tr in r.html.find(".history table tr"):
            cells = tr.find("td")
            try:
                fyend = dateutil.parser.parse(cells[0].text).date()
            except dateutil.parser.ParserError:
                continue
            if len(cells) != 6:
                continue
            links = list(cells[5].absolute_links)
            if not links or links[0] in (
                "https://beta.companieshouse.gov.uk",
                "https://www.gov.uk/government/organisations/charity-commission",
            ):
                continue
            accounts.append(
                Account(
                    regno=regno,
                    url=links[0],
                    fyend=fyend,
                )
            )
        return sorted(accounts, key=lambda x: x.fyend, reverse=True)


def get_charity_type(regno):
    if regno.startswith("SC") or regno.startswith("GB-SC-"):
        return OSCR()
    if regno.startswith("NI") or regno.startswith("GB-NIC-"):
        return CCNI()
    return CCEW(api_key=current_app.config.get("CCEW_API_KEY"))


class StripLinkText(str):
    def __eq__(self, other):
        return self.strip() == other.strip()


def print_header(s: str, underline: str = "="):
    print(s)
    print(underline * len(s))


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
        "regno": regno,
        "fyend": fyend,
    }


@fetch_cli.command("list")
@click.argument("regno")
@click.option("--destination", default=".", help="Folder in which to save accounts")
def list_accounts_for_download(regno: str, destination: str = ".", **kwargs: dict):
    """List all accounts for charity number REGNO.

    \b
    REGNO is the charity number
    """
    source = get_charity_type(regno)
    accounts = source.list_accounts(regno)
    if not accounts:
        print("No accounts found for charity number {}".format(regno))
        exit()
    print()
    print_header("Accounts for charity number {}".format(regno))
    for k, a in enumerate(accounts):
        print("{}: {:%Y-%m-%d}".format(k + 1, a.fyend))

    print("Enter account number to download:")
    to_download = input()
    to_download = int(to_download) - 1
    download_account(
        accounts[to_download].url,
        regno=regno,
        fyend=accounts[to_download].fyend,
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
    source = get_charity_type(regno)
    accounts = source.list_accounts(regno)
    download_account(
        accounts[0].url,
        regno=regno,
        fyend=accounts[0].fyend,
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
    source = get_charity_type(regno)
    accounts = source.list_accounts(regno, session=session)
    for a in accounts:
        download_account(
            a.url,
            regno=regno,
            fyend=a.fyend,
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
    source = get_charity_type(regno)
    accounts = source.list_accounts(regno, session=session)
    for account in accounts:
        if account.fyend == fyend:
            download_account(
                account.url,
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
    "--destination",
    type=click.Path(),
    default=".",
    help="Folder in which to save accounts",
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
        "regno",
        "fyend",
    ]

    def get_csv_row(row, regno, fyend):
        source = get_charity_type(regno)
        accounts = source.list_accounts(regno, session=session)
        urls = {account.fyend: account.url for account in accounts}
        if fyend and accounts:
            fyend = parse_datetime(fyend)
            if fyend not in urls:
                raise CharityFetchError("Financial year end not found")
            return download_account(
                urls[fyend],
                regno=regno,
                fyend=fyend,
                destination=destination,
                session=session,
            )
        elif accounts:
            return download_account(
                accounts[0].url,
                regno=regno,
                fyend=accounts[0].fyend,
                destination=destination,
                session=session,
            )
        raise CharityFetchError("No accounts found for charity {}".format(regno))

    def write_logfile(row, mode="a"):
        if logfile:
            logf = open(logfile, mode, newline="")
        else:
            logf = sys.stdout
        writer = csv.writer(logf)
        writer.writerow(row)
        logf.close()

    for k, row in tqdm(enumerate(reader)):

        if k == 0:
            write_logfile(
                [h for h in row.keys() if h not in logging_fields] + logging_fields,
                mode="w",
            )

        regno = row[regno_column]
        fyend = row.get(fyend_column)

        if skip_rows and skip_rows > k:
            result = {
                "error": "Row skipped",
                "regno": regno,
                "fyend": fyend,
            }

        else:
            try:
                result = get_csv_row(row, regno, fyend)
            except Exception as err:
                result = {
                    "error": str(err),
                    "regno": regno,
                    "fyend": fyend,
                }

        write_logfile(
            [v for h, v in row.items() if h not in logging_fields]
            + [
                result.get("file_location") is not None,
                result.get("error"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                result.get("file_location"),
                result.get("file_name"),
                result.get("file_size"),
                result.get("download_timetaken"),
                result.get("regno"),
                result.get("fyend"),
            ]
        )
