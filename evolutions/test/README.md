# Testing

Different cases of evolutions directories and database states are tested in
the subdirectories `case_1`, `case_2`, etc..  The `runtests.py` script
contains comments on what is being tested.

Before running the tests, you must set up MySQL and PostgreSQL databases.
This is done by use of the scripts `init_mysql_test.sql` (to be run as MySQL
admin user) and `init_psql_test.sh` (to be run as normal unix user with
postgres admin credentials).

To invoke the tests, run, *from the top level directory (../..)*:

    ./evolutions/test/runtests.py -q

To run only for one database type:

    ./evolutions/test/runtests.py -q TestEvolutions_MySQL
    ./evolutions/test/runtests.py -q TestEvolutions_PostgreSQL
    ./evolutions/test/runtests.py -q TestEvolutions_Sqlite

Output lines starting with 'evolutions: ERROR' are as expected (as long as the
tests pass).

You can also invoke the whole suite using `setup` by:

    python3 setup.py test
