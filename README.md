Quickpaste
==========

A dead simple code snippet sharing tool.

Requirements
------------

* python 3.7 (_May work on earlier versions but is totally untested_)
* [pipenv](https://pipenv.readthedocs.io/en/latest/) is used for dependency management.
* A database supported by [SQLAlchemy](https://docs.sqlalchemy.org/en/latest/core/engines.html#supported-databases)


Setup
-----

1.
	Clone the repo somewhere.  Master *should* always be stable but you can
	checkout the latest tag from [releases](https://github.com/carc1n0gen/quickpaste/releases) if you wish.

	`git clone https://github.com/carc1n0gen/quickpaste.git`

    (optional) `cd quickpaste && git checkout <version>`

2.
    Create a `quickpaste/data` directory.

3.
	Install dependencies.

	`pipenv sync`

4.
	Run database migrations.

	`pipenv run flask db upgrade head`

Configuration
-------------

Copy the `config.json.example` file to `config.json` in the same directory, and
edit as needed.  Below is a copy of the latest example config.

```json
{
    "BEHIND_PROXY": false,

    "LOG_FILE": "./data/app.log",
    "LOG_LEVEL": "INFO",

    "MAX_PASTE_LENGTH": 10240,
    "MINIFY_PAGE": true,
    "RATELIMIT_DEFAULT": "2 per second",

    "GA_ENABLED": false,
    "GA_ID": "ENTER YOUR GOOGLE ANALYTICS ID",

    "SQLALCHEMY_DATABASE_URI": "sqlite:///data/database.db",
    "SQLALCHEMY_TRACK_MODIFICATIONS": false,

    "MAIL_SERVER": "smtp.example.com",
    "MAIL_PORT": 25,
    "MAIL_USE_TLS": false,
    "MAIL_USE_SSL": false,
    "MAIL_USERNAME": "username",
    "MAIL_PASSWORD": "password",
    "MAIL_DEFAULT_SENDER": "sender <sender@example.com>",
    "MAIL_RECIPIENT": "recipient@example.com"
}
``` 

Running In Development
----------------------

`FLASK_ENV=development pipenv run flask run`

Running In Production
---------------------

Use a proper wsgi container.  I like to use waitress with nginx reverse proxy
in front of it, but that's totally personal preference.  More info at the
official [flask deployment page](http://flask.pocoo.org/docs/1.0/deploying/).

**Example running with waitress-serve**:

`PYTHONPATH=/path/to/quickpaste waitress-serve --call app.create_app:create_app`

You'll want to configure a daemon of some kind to keep the app running.

Updating
--------

Pull the latest changes from master, or checkout the latest tag, sync
dependencies, check for new configuration keys, and run migrations

`git fetch`

`git pull` or `git checkout <version>`

`pipenv sync`

`pipenv run flask db upgrade head`

Running Cleanup
---------------

There is a built in cleanup command to delete pastes that are older than one
week.

`pipenv run flask cleanup`

You will need to configure something like a cron to run that.

Random Things
-------------

**How long are pastes on official [quickpaste](https://quickpaste.net/) kept?**

The built in script that deletes week old pastes is run once a day.

**Why do I need to configure an email sender?**

If an unknown error occurs in the system, an email containing details will be
sent to the `MAIL_RECIPIENT` configured email.  These details will be vital
for debugging and reporting issues.
