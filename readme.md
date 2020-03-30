# Charity Account Fetch web app

This is a flask-based web app that allows charity accounts to be
stored in an elasticsearch database and then the text searched.

## Running a local version

### Step 1 - Install Elasticsearch

[Use the instructions for your operating system](https://www.elastic.co/downloads/elasticsearch)

When it is installed then start it running (by running `elasticsearch`).

You can check it's running by visiting <http://localhost:9200/> in your web browser.

### Step 2 - Create a python virtualenv

This will mean that the dependencies don't interfere with any other
python installations

```sh
git clone -b webapp https://github.com/drkane/charity-account-fetch.git
cd charity-account-fetch/
python -m venv env
```

### Step 3 - Install dependencies

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

### Step 4 - get a charitybase API key

[Go to CharityBase and get an API key](https://charitybase.uk/api-portal/keys).

You'll need it for the next step, so make a note somewhere.

### Step 5 - create a .env file

Create a new file called `.env` in the directory. The contents of the file should
be:

```sh
FLASK_APP=docdisplay
FLASK_ENV=development
ES_URL=http://localhost:9200/
CHARITYBASE_API_KEY=insert_key_here
```

### Step 6 - initialise the elasticsearch index

```sh
flask init-db
```

This will create an index called `charityaccounts`. You can check it exists after this by 
visiting <http://localhost:9200/charityaccounts>.

### Step 7 - run the app

```sh
flask run
```

It should now be available from <http://localhost:5000/>.
