#!/usr/bin/env python3

# evolutions: Provides play-evolutions-like functionality for Python
#             https://www.playframework.com/documentation/2.7.x/Evolutions
# usage: ./evolutions.py <db_url> <db_user> <db_pass> <evolutions_dir>

import glob, hashlib, logging, os.path as path, re, subprocess, sys


# Clean, uniform informational and error output
logging.basicConfig(level='INFO', format='evolutions: %(message)s')
logger = logging.getLogger()

def excepthook(type, value, traceback):
    print('evolutions: ERROR: ' + str(value), file=sys.stderr)
sys.excepthook = excepthook


# Holds a DB connection and info it was created from
class DBConn:
    def __init__(self, db_type, cmd, host, port, db_name, user, pw, conn,
                 param):
        self.db_type = db_type
        self.cmd     = cmd
        self.host    = host
        self.port    = port
        self.db_name = db_name
        self.user    = user
        self.pw      = pw
        self.conn    = conn
        self.param   = param

    # Ugh, different DB-API2 impls use '?' or '%s' for parameter wildcard
    def fix_params(self, stmt):
        return stmt.replace('_?', self.param)

    # Wraps to handle parameter formatting
    def execute(self, stmt, *args):
        db = self.conn.cursor()
        db.execute(self.fix_params(stmt), *args)
        return db


# Holds info on a single evolution stage (both ups and downs)
class Stage:
    def __init__(self, idx, apply_hash, revert_hash,
                 apply_script, revert_script, applied_at):
        self.idx = idx
        self.apply_hash = apply_hash
        self.revert_hash = revert_hash
        self.apply_script = apply_script
        self.revert_script = revert_script
        self.applied_at = applied_at

    def __str__(self):
        return 'Stage %d (apply len = %d, revert len = %d)' % (
            self.idx, len(self.apply_script), len(self.revert_script))


# Utility
def read_textfile(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        return f.read()


# Return DBConn wrapping DB-API2 conn (https://python.org/dev/peps/pep-0249/)
def get_connection(url, user, pw):
    url_re = re.compile(r'([^:]+)://([^:]+):([0-9]+)/(.+)')
    file_re = re.compile(r'([^:]+):(/.+)')
    match = url_re.match(url)
    if match:
        db_type, host, port, db_name = (match.group(1), match.group(2),
                                        match.group(3), match.group(4))
    else:
        match = file_re.match(url)
        if match:
            db_type, host, port, db_name = (match.group(1), None,
                                            None, match.group(2))
        else:
            raise Exception("Unrecognized DB URL format: '" + url + "'")
    if db_type == 'mysql':
        import mysql.connector
        conn = mysql.connector.connect(user=user, password=pw,
                                       host=host, port=port, database=db_name,
                                       charset='utf8', autocommit=True)
        cmd = ['mysql', '-u', user, '--password='+pw, db_name]
        param = '%s'
    elif db_type == 'postgresql':
        import psycopg2
        conn = psycopg2.connect(user=user, password=pw,
                                host=host, port=port, database=db_name)
        conn.set_session(autocommit=True)
        cmd = ['psql', '-h', 'localhost', '-U', user, db_name]
        param = '%s'
    elif db_type == 'sqlite':
        import sqlite3
        # Note: URL is assumed to contain absolute path in this case
        conn = sqlite3.connect(db_name, isolation_level=None)
        cmd = ['sqlite3', db_name]
        param = '?'
    else:
        raise Exception("Unsupported database type: '" + db_type + "'")

    return DBConn(db_type, cmd, host, port, db_name, user, pw, conn, param)


# Connects to database and ensures evolutions table present
def connect_and_ensure(url, user, pw):
    dbConn = get_connection(url, user, pw)
    dbConn.execute('''
      CREATE TABLE IF NOT EXISTS evolutions (
          id             INT NOT NULL PRIMARY KEY,
          applied_at     TIMESTAMP NOT NULL,
          apply_hash     VARCHAR(64) NOT NULL,
          revert_hash    VARCHAR(64) NOT NULL,
          apply_script   TEXT,
          revert_script  TEXT )
    ''')
    return dbConn


# Sha1 of a file; use only with small files, else chunk it
def sha1_file(fname):
    with open(fname, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


# Reads in and collects hashes for all evolutions files in a directory
def scan_dir_stages(ev_dir):
    numeric_re = re.compile(r'([0-9]+)(-downs)?\.sql')
    sql_files = glob.glob(path.join(ev_dir, '*.sql'))
    ups = []
    downs = []

    for sql_file in sql_files:
        m = numeric_re.fullmatch(path.basename(sql_file))
        if m:
            idx = int(m.group(1))
            is_ups = m.group(2) is None
            if is_ups:
                ups.append(idx)
            else:
                downs.append(idx)
    ups = sorted(ups)
    downs = sorted(downs)

    if ups != downs:
        raise Exception("Ups and downs SQL files are not in correspondence.")

    stages = []
    for idx in ups:
        ups_f = path.join(ev_dir, str(idx) + '.sql')
        downs_f = path.join(ev_dir, str(idx) + '-downs.sql')
        stages.append(Stage(idx, sha1_file(ups_f), sha1_file(downs_f),
                            read_textfile(ups_f), read_textfile(downs_f), None))
    return stages


def scan_db_stages(dbConn):
    res = dbConn.execute('''
        SELECT id, apply_hash, revert_hash, apply_script, revert_script, applied_at FROM evolutions ORDER BY id ASC;
    ''')

    stages = []
    for row in res.fetchall():
        stages.append(Stage(row[0], row[1], row[2], row[3], row[4], row[5]))

    return stages


# Check if stages start with 1 and go in sequence, assuming sorted
def check_stages(stages, src):
    if stages:
        indices = [ stage.idx for stage in stages ]
        if indices[0] != 1 or indices[-1] != len(indices):
            raise Exception('Illegal stage sequence ' + str(indices)
                            + ' in ' + src)
    return stages


# Invoke db command to execute script (DBAPI has no multistatement support)
def execute_script(idx, script_str, dbConn):
    db_proc = subprocess.Popen(dbConn.cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               stdin=subprocess.PIPE)
    output, _ = db_proc.communicate(script_str.encode('utf-8'))
    if db_proc.returncode != 0:
        raise Exception('evolutions: script ' + str(idx) + ' failed: '
                        + output.decode('utf-8'))


# Executes given stage downs, and removes stage from db
def run_and_remove_downs(stage, dbConn):
    logger.info('Running downs for stage %d', stage.idx)
    execute_script(stage.idx, stage.revert_script, dbConn)
    dbConn.execute('DELETE FROM evolutions WHERE id = _?', [stage.idx])


# Executes ups (unless in list to skip as already run) and record to db
def run_and_add_ups(stage, skip, dbConn):
    if stage.idx in skip:
        logger.warning('Force skip running ups for stage %d', stage.idx)
    else:
        logger.info('Running ups for stage %d', stage.idx)
        execute_script(stage.idx, stage.apply_script, dbConn)

    dbConn.execute('''
        INSERT INTO evolutions (id, applied_at, apply_hash, revert_hash,
                                apply_script, revert_script) VALUES
                                (_?, CURRENT_TIMESTAMP, _?, _?, _?, _?)
    ''', [stage.idx, stage.apply_hash, stage.revert_hash,
          stage.apply_script, stage.revert_script])


# Updates an evolution row
def update_db(stage, dbConn):
    dbConn.execute('''
        UPDATE evolutions SET apply_hash = _?, revert_hash = _?,
                              apply_script = _?, revert_script = _?
                          WHERE id = _?
    ''', [stage.apply_hash, stage.revert_hash,
          stage.apply_script, stage.revert_script, stage.idx])


# Inserts or updates stages we were told to skip, return updated DB stages
def update_for_skips(dir_stages, db_stages, skip, dbConn):
    dir_len = len(dir_stages)
    db_len = len(db_stages)
    dir_i = 0
    db_i = 0
    for idx in sorted(list(skip)):
        # Find idx in dir and db
        while dir_i < dir_len:
            if dir_stages[dir_i].idx == idx:
                break
            dir_i += 1
        if dir_i == dir_len:
            raise Exception("Skip requested for missing file: %d.sql" % (idx))
        while db_i < db_len:
            if db_stages[db_i].idx == idx:
                # update
                dir_stages[dir_i].applied_at = db_stages[db_i].applied_at
                db_stages[db_i] = dir_stages[dir_i]
                update_db(db_stages[db_i], dbConn)
                break
            db_i += 1
            # If not found, will get added later under evolve() in sequence
    return db_stages


# 1. Go forward through DB rows to find first difference from files
# 2. Run downs from above down to and including that row, removing DB rows
# 3. Run files and insert DB rows starting from there
# 4. Return resulting updated DB stage objects
def evolve(dir_stages, db_stages, skip, prod_mode, dbConn):
    dir_len = len(dir_stages)
    db_len = len(db_stages)

    # Finds first differing stage, executes downs from DB up to that one,
    s = 0
    while s < min(dir_len, db_len):
        if dir_stages[s].apply_hash != db_stages[s].apply_hash:
            break
        s += 1

    # s is now index of first file that needs to be run
    # Run all DB downs in reverse through here
    downs_r = range(db_len-1, s-1, -1)
    if prod_mode and downs_r:
        raise Exception('In production mode but downs ' + str(downs_r)
                        +' needs running; aborting!')
    for i in downs_r:
        run_and_remove_downs(db_stages[i], dbConn)
    db_stages = db_stages[0:s]

    # Now run the ups
    for i in range(s, dir_len):
        run_and_add_ups(dir_stages[i], skip, dbConn)

    return db_stages[0:s] + dir_stages[s:]


def usage(invoked_name):
    print("usage: " + path.basename(invoked_name)
          + " <db_url> <db_user> <db_pass> <evolutions_dir> [--skip=<stages>] [--prod]\n"
          + "   --skip=<stages> = comma-separated indices to assume already run\n"
          + "   --prod          = abort if downs need to be run (for production)")
    return 1


def main(args):

    # Arg processing
    if len(args) < 5 or len(args) > 7:
        return usage(args[0])

    db_url, user, pw, ev_dir = args[1:5]

    skip_arg = '--skip='
    prod_arg = '--prod'
    skip = set()
    prod_mode = False
    for arg in args[5:]:
        if arg.startswith(skip_arg):
            skip = set(map(int, args[5][len(skip_arg):].split(',')))
            logger.info('Force skip: %s', (','.join(map(str, skip))))
        elif arg == prod_arg:
            prod_mode = True
        else:
            return usage(args[0])

    # 1. Connect to DB and ensure evolutions table, begin transaction
    dbConn = connect_and_ensure(db_url, user, pw)

    # 2. Scan dir files in order, compute hashes (hashlib.sha1().hexdigest())
    dir_stages = check_stages(scan_dir_stages(ev_dir), ev_dir)
    if not dir_stages:
        raise Exception("No evolutions found in dir '" + ev_dir + "'")
    logger.info("Got %d stages from dir '%s'", len(dir_stages), ev_dir)
    logger.debug('\n\t%s', '\n\t'.join(map(str, dir_stages)))

    # 3. Scan DB files
    db_stages = check_stages(scan_db_stages(dbConn), 'db')
    logger.info("Got %d stages from DB '%s'", len(db_stages), dbConn.db_name)
    logger.debug('\n\t%s', '\n'.join(map(str, db_stages)))

    # Handle skips
    db_stages = update_for_skips(dir_stages, db_stages, skip, dbConn)

    # 5. Evolve
    upd_stages = evolve(dir_stages, db_stages, skip, prod_mode, dbConn)

    dbConn.conn.close()
    logger.info('Completed with %d stages.', len(upd_stages))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[:]))
