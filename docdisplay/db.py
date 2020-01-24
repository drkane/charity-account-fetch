import elasticsearch

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    if 'es' not in g:
        g.es = elasticsearch.Elasticsearch(current_app.config['ES_URL'])

    return g.es


def close_db(e=None):
    es = g.pop('es', None)


def init_db():
    es = get_db()
    if not es.indices.exists(index=current_app.config['ES_INDEX']):
        es.indices.create(index=current_app.config['ES_INDEX'])
    es.ingest.put_pipeline(
        'accounts',
        body={
            "description" : "Store account documents",
            "processors" : [
                {
                    "attachment" : {
                        "field" : "filedata"
                    }
                }
            ]
        }
    )


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')