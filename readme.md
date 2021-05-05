# Charity Account Fetch web app

This is a flask-based web app that allows charity accounts to be
stored in an elasticsearch database and then the text searched.

## Set up a local version

### Step 1 - Create a python virtualenv

This will mean that the dependencies don't interfere with any other
python installations

```sh
git clone https://github.com/drkane/charity-account-fetch.git
cd charity-account-fetch/
python -m venv env
```

### Step 2 - Install dependencies

First activate your virtual environment:

```sh
# windows
env/Scripts/activate

# or mac/linux
source env/bin/activate
```

Then install the python requirements.

```sh
pip install -r requirements.txt
```

### Step 3 - sign up for Charity Commission API

Register for an API key with the Charity Commission beta API:

<https://register-of-charities.charitycommission.gov.uk/documentation-on-the-api>

Once you've signed up click on Profile > Subscriptions to create an API key. You'll need the key for the next step.

### Step 4 - create a .env file

Create a new file called `.env` in the directory. The contents of the file should be:

```
FLASK_APP=docdisplay
FLASK_ENV=development
CCEW_API_KEY=<insert api key>
```

Replace `<insert api key>` with your charity Commission API key from step 3.

## Using the command line

You can use the command line to fetch account PDFs from charities.

Follow steps 1-4 above to get the flask app installed. You can then
run commands to find and fetch account PDFs.

On the command line, use `flask fetch` to run the commands. If you
run `flask fetch --help` you will see a list of the available commands.

The commands are:

 - `flask fetch account` - Download account for FYEND for REGNO.
 - `flask fetch all` - Download all available accounts for charity number REGNO.  
 - `flask fetch csv` - Download accounts for a selection of charities from CSVFILE
 - `flask fetch latest` - Download the latest account for charity number REGNO.      
 - `flask fetch list` - List all accounts for charity number REGNO.

Most of the commands take a charity number as the variable, eg `flask fetch latest 123456` will fetch the latest PDF for charity number 123456.

To view help for an individual command run `flask fetch <command> --help`, eg
`flask fetch all --help`.

## Setting up the web app

These steps are optional if all you need is to manually download 
documents using the command line.

### Step 5 - get a charitybase API key

[Go to CharityBase and get an API key](https://charitybase.uk/api-portal/keys).

You'll need it for the next step, so make a note somewhere.

### Step 6 - Install Elasticsearch

[Use the instructions for your operating system](https://www.elastic.co/downloads/elasticsearch)

When it is installed then start it running (by running `elasticsearch`).

You can check it's running by visiting <http://localhost:9200/> in your web browser.

### Step 7 - update your .env file

Add the following two lines to the `.env` file created in step 3.

```
ES_URL=http://localhost:9200/
CHARITYBASE_API_KEY=insert_key_here
```

### Step 8 - initialise the elasticsearch index

```sh
flask init-db
```

This will create an index called `charityaccounts`. You can check it exists after this by 
visiting <http://localhost:9200/charityaccounts>.

### Step 9 - run the app

```sh
flask run
```

It should now be available from <http://localhost:5000/>.

## Uploading documents

It's possible to upload documents through the web app using <http://localhost:5000/doc/upload>.

You can also use the command line through the command:

```sh
flask doc upload NI100002_20200331.pdf
```

The command line expects the filename to be in the correct format `<regno>_<fyend>.pdf`. Where `<fyend>` is in format `YYYYMMDD`.

## `max_result_window` setting

Where there are more than 10,000 documents it can cause issues with 
elasticsearch due to the `max_result_window` setting.

To increase the maximum number of results run the following command:

```sh
flask update-index-setting max_result_window 10001
```
