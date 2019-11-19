
# Evolutions

The evolutions package provides a facility similar to
[play-evolutions](https://www.playframework.com/documentation/2.7.x/Evolutions)
([source](https://github.com/playframework/playframework/tree/master/persistence/play-jdbc-evolutions/src/main/scala/play/api/db/evolutions))
for use with Python.  It differs from other similar tools in its simple,
lightweight philosophy and its pure SQL orientation.  It enforces a linear
history in schema development with no branching or dependencies.  Migrations
are contained in SQL files and run automatically as needed, with no code
embedding or hand-tuned invocations needed.  Evolutions plays well with source
control as well as differences between development and production
environments.  Finally, it's not tied to any application framework so can be
used anywhere that Python 3 and the target database are available, regardless
of whether the using application is itself implemented in Python.

## Ups

The basic idea is that, as the database schema is developed incrementally, the
changes are placed in *ups* files named `1.sql` (the original schema),
`2.sql`, `3.sql`, etc..  When the tool is invoked (usually just before the app
starts up, see Usage), a table is checked in the database to see which
of these scripts have been run, and any missing are run in sequence.  The
scripts should contain both schema changes and data migration.  This way, the
app and the schema can be developed together, without worrying about manual
database updates, legacy data support, or schema-code synchronization.

### Example

An application is deployed with its schema in a file `1.sql`,
containing a lot of `CREATE TABLE` statements.  Some development is done and
`2.sql` with some `ALTER TABLE` statements is written.  When this is deployed
and the evolutions tool run before application startup, it detects that
`1.sql` has already been run, but `2.sql` has not, so it runs that.  Later on,
`3.sql` and `4.sql` are developed but reach deployment together.  When the
evolutions tool is run, it runs first `3.sql` then `4.sql` in sequence.

## Downs

In addition to the *ups*, a set of corresponding *downs* files `1-downs.sql`,
`2-downs.sql`, `3-downs.sql` are created during development, which undo the
effects of the corresponding ups files.  If the tool detects that a change has
been made to an ups file, then it will rerun it.  However, its former version,
as well as any later ups that have been run "on top" of it, must be undone
first.  So the tool first runs these in reverse, using versions cached in the
database itself in case *those* have changed as well, then runs back up the
sequence starting from the first modified file.  This process allows tweaking
changes during development, without needing to manually adjust the database
each time.  It also enables collaboration, so that, for example, a single
`#.sql` file can be used by everyone for an entire sprint (merging in changes
to a shared git branch).

### Example

The application in the first example continues being developed. In addition to
the ups files mentioned earlier, `1-downs.sql` (a bunch of `DROP TABLE`
statements), `2-downs.sql` (`ALTER TABLE` statements undoing the alterations
in `2.sql`), `3-downs.sql`, and `4-downs.sql` were all written.  At one point,
someone realizes there was a mistake in `3.sql` and it should be fixed.  They
modify this file, as well as `3-downs.sql`, then deploy the application.

When the evolutions tool runs, it detects that `3.sql` has changed.  It then
runs `4-downs.sql` and `3-downs.sql` (in that order) to get to a point where
it can correctly apply the new version of `3.sql`.  Then it runs that script,
and finally `4.sql` to bring the database fully up to date.

## Production

In general, although running downs will ensure a consistent database schema,
some data loss is often unavoidable, simply because elements of the schema are
lost through downgrade, meaning the data cannot be preserved.  **For this
reason, you should not run downs in production. Ever.** Once you deploy an
evolution stage to production, you should freeze it, so evolutions will not
run it again.  In addition, you can and should enable a safety check by adding
the `--prod` switch when invoking (see Usage).  If the tool encounters an ups
script change when this switch is active, it will abort rather than run any
downs, so you can address the situation manually.

In this case, you will end up in a situation where the database is out of sync
with the evolutions scripts.  This can also occur if evolutions is only taken
into use.  This can be remedied by using the `--skip=<indices>` switch to the
tool, which will cause the tool to assume the scripts with the given
comma-separated indices have already been run, and mark them so in the
database, without actually running them.

### Example

The deployment mentioned in the preceding examples as assumed to be on a
development environment, where it's OK to lose data in the case *downs*
scripts need to be run.  However, in the production deployment, the evolutions
tool is invoked with the `--prod` argument.  Hence, in the situation described
in the previous example where `3.sql` has changed, it will abort and return an
error code.  The user will then need to address the situation manually.
Possibly they will apply the new change needed from `3.sql` manually, taking
care to preserve data.

Then they can invoke the tool using `--skip=3`.  This will cause it to mark
`3.sql` has having been "run" in its new modified version, *without actually
running it*.  Then, after noting that `4.sql` has not changed, the database is
now considered to be up to date.  (Subsequent invocations do not need the
`--skip` argument and will not trigger an abort, unless there has been a new,
different change of an already-run script.)


# Database Support

MySQL, PostgreSQL, and Sqlite are supported.  The database is accessed through
a combination of the command line clients and
[DB-API2](https://www.python.org/dev/peps/pep-0249/), using
[mysql-connector-python](https://dev.mysql.com/doc/connector-python/en/),
[PsycoPg2](http://initd.org/psycopg/docs/), and
[sqlite3](https://docs.python.org/3.8/library/sqlite3.html).  (These are not
listed as dependencies of this package, so you should install the one needed
for your own case yourself.)


## Transactions

The evolutions scripts themselves are run by invoking the command line client
for the database being used (e.g., `psql` for Postgres).  Transactionality is
therefore under control of the script itself.


# Usage

The tool is invoked via a Python 3 command line script, and should be called
just before or as part of starting the application, or, in an auto-deploy
environment, whenever the schema files have been changed.

    ./evolutions.py <db_url> <db_user> <db_pass> <evolutions_dir> [--skip=<stages>] [--prod]
        --skip=<stages> = comma-separated indices to assume already run
        --prod          = abort if downs need to be run (for production)

- *db\_url:* e.g.: `mysql://localhost:3306/dbname`,
                 `postgresql://localhost:5432/dbname`,
                 `sqlite:/absolute/path/to/database.db`
- *db\_user, db\_pass:* db\_pass is ignored for Postgres (must use .pgpass
  file), and both db\_user and db\_pass are ignored for Sqlite; pass empty
  strings ("")
- *evolutions_dir:* directory containing the #.sql/#-downs.sql files; can be
  relative or absolute path
- *--skip:* comma-separated list of stage indices to skip running if you have
  a database which has already had one or more of the #.sql files run on it;
  will insert rows to the `evolutions` table to make it up to date, but will
  not actually run the scripts
- *--prod:* if given, tool will abort immediately if it determines any downs would
  need to be run; database is not touched


# Implementation

The evolutions tool operates by collecting the SHA1 hash of each ups and downs
script in the evolutions directory, and storing these values, together with
the script contents themselves, in a dedicated table (named `evolutions`) in
the database.  Decisions on which ups and downs scripts to run are made by
comparing the database record and the scripts found in the directory, and
updates are made according to the runs.


# Development

On [GitHub](https://github.com/arobertn/evolutions).
