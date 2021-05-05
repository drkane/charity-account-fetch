import click
import elasticsearch
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    if "es" not in g:
        g.es = elasticsearch.Elasticsearch(current_app.config["ES_URL"])

    return g.es


def close_db(e=None):
    g.pop("es", None)


def init_db():
    es = get_db()
    if not es.indices.exists(index=current_app.config["ES_INDEX"]):
        es.indices.create(index=current_app.config["ES_INDEX"])


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(update_db_setting_command)


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo("Initialized the database.")


@click.command("update-index-setting")
@click.argument("name")
@click.argument("value")
@with_appcontext
def update_db_setting_command(name, value):
    """Update setting NAME on the index to VALUE."""
    es = get_db()
    es.indices.put_settings(
        index=current_app.config["ES_INDEX"],
        body={"index": {name: value}},
    )
    click.echo(f"Set '{name}' to '{value}'")
