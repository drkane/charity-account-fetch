import os
import argparse
from datetime import date, datetime
import csv
import logging

import requests
import requests_cache
from bs4 import BeautifulSoup
import dateutil.parser

def print_header(s: str, underline: str="="):
    print(s)
    print(underline * len(s))

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

def parse_datetime(d: str, f: str="%Y-%m-%d") -> date:
    """
    Parse a date from a string
    """
    return datetime.strptime(d, f).date()

def ccew_list_accounts(regno: str) -> list:
    """
    List accounts for a charity
    """
    url = "https://beta.charitycommission.gov.uk/charity-details/?regId={}&subId=0".format(regno)
    r = requests.get(url)
    logging.debug("Fetching account list: {}".format(url))
    if getattr(r, "from_cache", False):
        logging.debug("Used cache")
    soup = BeautifulSoup(r.text, 'html.parser')
    accounts = [
        {
            'url': a['href'],
            'fyend': dateutil.parser.parse(a.find(class_='pcg-charity-details__doc-title').text),
            'size': filesize_text_to_int(a.find(class_='pcg-charity-details__doc-size').text),
        }
        for a in soup.find(id="documents").find_all('a', class_='pcg-charity-details__doc')
    ]
    return sorted(accounts, key=lambda x: x['fyend'], reverse=True)

def construct_ccew_account_url(regno: str, fyend: date) -> str:
    """
    Turn a charity number and financial year end into a Charity Commission account PDF format URL
    """
    return "http://apps.charitycommission.gov.uk/Accounts/Ends{ends}/{regno:0>10}_AC_{fyend}_E_C.PDF".format(
        ends=regno[-2:],
        regno=regno,
        fyend=fyend.strftime("%Y%m%d")
    )

def download_account(url: str, regno: str=None, fyend: date=None, destination: str=".", session=None) -> dict:
    """
    Download a charity account from an URL
    """

    if not session:
        session = requests.Session()

    if regno is None or fyend is None:
        filename = url.rsplit('/', 1)[-1]
    else:
        filename = '{}_{:%Y%m%d}.pdf'.format(regno, fyend)
    r = session.get(url)
    logging.debug("Fetching account PDF: {}".format(url))
    if getattr(r, "from_cache", False):
        logging.debug("Used cache")
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        logging.error("Account not found: {}".format(url))
        return {
            "error": "Account not found"
        }
    
    if not os.path.exists(destination):
        logging.debug("Creating directory: {}".format(destination))
        os.makedirs(destination)

    dest = os.path.join(destination, filename)
    logging.debug("Saving to: {}".format(dest))
    with open(dest, 'wb') as f:
        f.write(r.content)

    return {
        "file_location": dest,
        "file_name": filename,
        "file_size": len(r.content),
        "download_timetaken": r.elapsed.total_seconds(),
    }

def list_accounts_for_download(regno: str, destination: str=".", **kwargs: dict):
    accounts = ccew_list_accounts(regno)
    print()
    print_header("Accounts for charity number {}".format(regno))
    for k, a in enumerate(accounts):
        print("{}: {:%Y-%m-%d}".format(k+1, a['fyend']))

    print("Enter account number to download:")
    to_download = input()
    to_download = int(to_download) - 1
    download_account(accounts[to_download]['url'], destination=destination)

def download_latest_account(regno: str, destination: str=".", **kwargs: dict):
    accounts = ccew_list_accounts(regno)
    download_account(
        accounts[0]['url'],
        regno=regno,
        fyend=accounts[0]['fyend'],
        destination=destination
    )

def download_all_accounts(regno: str, destination: str=".", **kwargs: dict):
    accounts = ccew_list_accounts(regno)
    session = requests.Session()
    for a in accounts:
        download_account(
            a['url'],
            regno=regno,
            fyend=a['fyend'],
            destination=destination,
            session=session,
        )

def download_account_parser(regno: str, fyend: date, destination: str=".", **kwargs):
    download_account(
        construct_ccew_account_url(regno, fyend),
        regno=regno,
        fyend=fyend,
        destination=destination
    )

def download_from_csv(csvfile, regno_column: str="regno", fyend_column: str="fyend", destination: str=".", logfile=None, skip_rows: int=0, **kwargs):
    reader = csv.DictReader(csvfile)
    session = requests.Session()

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

        if logfile and k==0:
            with open(logfile, 'w', newline='') as logf:
                writer = csv.writer(logf)
                writer.writerow(
                    [
                        h for h in row.keys() if h not in logging_fields
                    ] + logging_fields
                )

        if skip_rows and skip_rows > k:
            result = {
                "error": "Row skipped"
            }

        else:
            regno = row[regno_column]
            fyend = row.get(fyend_column)
            result = {}
            if fyend:
                fyend = parse_datetime(fyend)
                result = download_account(
                    construct_ccew_account_url(regno, fyend),
                    regno=regno,
                    fyend=fyend,
                    destination=destination,
                    session=session,
                )
        

        if logfile:
            with open(logfile, 'a', newline='') as logf:
                writer = csv.writer(logf)
                writer.writerow([v for h, v in row.items() if h not in logging_fields] + [
                    result.get("file_location") is not None,
                    result.get("error"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    result.get("file_location"),
                    result.get("file_name"),
                    result.get("file_size"),
                    result.get("download_timetaken"),
                ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Download charity accounts for organisations 
    registered with the Charity Commission for England and Wales""")
    parser.add_argument("-v", "--verbose", action='store_true', help="More descriptive output")

    subparsers = parser.add_subparsers(help='Operation to perform')

    list_parser = subparsers.add_parser('list', help='List accounts for download from a charity by number')
    list_parser.add_argument('regno', help="Charity number")
    list_parser.add_argument('--destination', default=".", help='Folder in which to save accounts')
    list_parser.set_defaults(func=list_accounts_for_download)

    latest_parser = subparsers.add_parser('latest', help='Download the latest account for a charity number')
    latest_parser.add_argument('regno', help="Charity number")
    latest_parser.add_argument('--destination', default=".", help='Folder in which to save accounts')
    latest_parser.set_defaults(func=download_latest_account)

    all_parser = subparsers.add_parser('all', help='Download all available accounts for a charity number')
    all_parser.add_argument('regno', help="Charity number")
    all_parser.add_argument('--destination', default=".", help='Folder in which to save accounts')
    all_parser.set_defaults(func=download_all_accounts)

    account_parser = subparsers.add_parser('account', help='Download an account based on charity number and financial year end')
    account_parser.add_argument('regno', help="Charity number")
    account_parser.add_argument('fyend', type=parse_datetime, help="Financial year end (format YYYY-MM-DD)")
    account_parser.add_argument('--destination', default=".", help='Folder in which to save accounts')
    account_parser.set_defaults(func=download_account_parser)

    csv_parser = subparsers.add_parser('csv', help='Download accounts for a selection of charities from a CSV file')
    csv_parser.add_argument('csvfile', type=argparse.FileType('r'), help='Location of the CSV file to download')
    csv_parser.add_argument('--regno-column', default="regno", help='Name of the column with a charity number in')
    csv_parser.add_argument('--fyend-column', default="fyend", help='Name of the column with the financial year end in (if not found then the latest accounts will be used)')
    csv_parser.add_argument('--destination', default=".", help='Folder in which to save accounts')
    csv_parser.add_argument('--logfile', help='File to output results')
    csv_parser.add_argument('--skip-rows', type=int, default=0, help='Number of rows to skip when parsing file')
    csv_parser.set_defaults(func=download_from_csv)
    
    args = parser.parse_args()
    requests_cache.install_cache()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    args.func(**args.__dict__)
