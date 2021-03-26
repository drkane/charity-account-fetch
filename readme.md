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

### Step 3 - create a .env file

Create a new file called `.env` in the directory. The contents of the file should
be:

```
FLASK_APP=docdisplay
FLASK_ENV=development
```

## Using the command line

You can use the command line to fetch account PDFs from charities.

Follow steps 1-3 above to get the flask app installed. You can then
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

### Step 4 - get a charitybase API key

[Go to CharityBase and get an API key](https://charitybase.uk/api-portal/keys).

You'll need it for the next step, so make a note somewhere.

### Step 5 - Install Elasticsearch

[Use the instructions for your operating system](https://www.elastic.co/downloads/elasticsearch)

When it is installed then start it running (by running `elasticsearch`).

You can check it's running by visiting <http://localhost:9200/> in your web browser.

### Step 6 - update your .env file

Add the following two lines to the `.env` file created in step 3.

```
ES_URL=http://localhost:9200/
CHARITYBASE_API_KEY=insert_key_here
```

### Step 7 - initialise the elasticsearch index

```sh
flask init-db
```

This will create an index called `charityaccounts`. You can check it exists after this by 
visiting <http://localhost:9200/charityaccounts>.

### Step 8 - run the app

```sh
flask run
```

It should now be available from <http://localhost:5000/>.
