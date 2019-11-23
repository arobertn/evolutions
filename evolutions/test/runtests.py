#!/usr/bin/env python3

# Invoke from top-level dir

import os, os.path as path, subprocess, sys, unittest

sys.path.append('.')


class TestEvolutions_MySQL(unittest.TestCase):

    # This and next are seriously abusing Python's loose OO implementation
    @classmethod
    def setUpClass(cls):
        db_name = 'evtest'
        db_user = 'evtestuser'
        db_pass = 'evtestpass'
        cls.db_cmd = ['./evolutions/evolutions.py',
                      'mysql://localhost:3306/' + db_name,
                      db_user, db_pass]
        cls.db_check_cmd = ['mysql', '-u', db_user,
                            '--password=' + db_pass, db_name,
                            '--skip-column-names']
        print("\nMySQL Tests\n", file=sys.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.do_db_check(cls, "DROP TABLE soup;")
        cls.do_db_check(cls, "DROP TABLE evolutions;")


    def do_db_check(self, query, expected_result=None):
        db_proc = subprocess.Popen(self.db_check_cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=sys.stderr,
                                   stdin=subprocess.PIPE)
        output, _ = db_proc.communicate(query.encode('utf-8'))
        if db_proc.returncode != 0:
            raise Exception('check query "' + query + '" failed: '
                            + output.decode('utf-8'))
        if expected_result:
            self.assertEqual(output.strip().decode('utf-8'), expected_result)

    def setUp(self):
        print("\nTest '%s'\n" % (self._testMethodName), file=sys.stderr)


    # Load a single stage correctly, no-op on rerun
    def test_case_1(self):
        subprocess.check_call(self.db_cmd + ['evolutions/test/case_1'])
        self.do_db_check("SELECT COUNT(*) FROM SOUP;", "2")

        # Repeat should be ok, be a no-op
        subprocess.check_call(self.db_cmd + ['evolutions/test/case_1'])
        self.do_db_check("SELECT COUNT(*) FROM SOUP;", "2")

    # Add a second and third stage to the first
    def test_case_2(self):
        subprocess.check_call(self.db_cmd + ['evolutions/test/case_2'])
        self.do_db_check("SELECT COUNT(*) FROM SOUP;", "4")

    # Change stage 1, but run in prod mode, causing abort
    def test_case_3a(self):
        ret = subprocess.call(self.db_cmd + ['evolutions/test/case_3',
                                             '--prod'])
        self.assertEqual(ret, 1)
        self.do_db_check("SELECT COUNT(*) FROM SOUP;", "4")

    # Change stage 1, triggering downs and rerun of all stages
    def test_case_3b(self):
        subprocess.check_call(self.db_cmd + ['evolutions/test/case_3'])
        self.do_db_check("SELECT COUNT(*) FROM SOUP;", "5")

    # Check file misconfiguration (missing downs)
    def test_case_4(self):
        ret = subprocess.call(self.db_cmd + ['evolutions/test/case_4'])
        self.assertEqual(ret, 1)

    # Check file misconfiguration (incorrect naming)
    def test_case_5(self):
        ret = subprocess.call(self.db_cmd + ['evolutions/test/case_5'])
        self.assertEqual(ret, 1)

    # Check file misconfiguration (skipped stage)
    def test_case_6(self):
        ret = subprocess.call(self.db_cmd + ['evolutions/test/case_6'])
        self.assertEqual(ret, 1)

    # Add stage 5 but skip running it
    def test_case_7(self):
        subprocess.check_call(self.db_cmd + ['evolutions/test/case_7',
                                             '--skip=5'])
        self.do_db_check("SELECT COUNT(*) FROM SOUP;", "5")
        self.do_db_check("SELECT COUNT(*) FROM evolutions;", "5")
        # Skip not needed after that
        subprocess.check_call(self.db_cmd + ['evolutions/test/case_7'])
        self.do_db_check("SELECT COUNT(*) FROM evolutions;", "5")

    # Modify stage 3, but skip running it, in prod mode
    def test_case_8(self):
        subprocess.check_call(self.db_cmd + ['evolutions/test/case_8',
                                             '--skip=3', '--prod'])
        self.do_db_check("SELECT COUNT(*) FROM SOUP;", "5")
        self.do_db_check("SELECT COUNT(*) FROM evolutions;", "5")
        # Skip not needed after that
        subprocess.check_call(self.db_cmd + ['evolutions/test/case_8',
                                             '--prod'])
        self.do_db_check("SELECT COUNT(*) FROM evolutions;", "5")


class TestEvolutions_PostgreSQL(TestEvolutions_MySQL):

    @classmethod
    def setUpClass(cls):
        db_name = 'evtest'
        db_user = 'evtestuser'
        db_pass = ''
        cls.db_cmd = ['./evolutions/evolutions.py',
                      'postgresql://localhost:5432/' + db_name,
                      db_user, db_pass]
        cls.db_check_cmd = ['psql', '-h', 'localhost', '-U', db_user, db_name,
                            '--tuples-only', '--quiet']
        print("\nPostgreSQL Tests\n", file=sys.stderr)


class TestEvolutions_Sqlite(TestEvolutions_MySQL):

    @classmethod
    def setUpClass(cls):
        db_name = 'evtest.db'
        cls.db_cmd = ['./evolutions/evolutions.py',
                      'sqlite:' + path.join(os.getcwd(),
                                            'evolutions', 'test', db_name),
                      '""', '""']
        cls.db_check_cmd = ['sqlite3', path.join('evolutions', 'test', db_name)]
        print("\nSqlite Tests\n", file=sys.stderr)


if __name__ == '__main__':
    unittest.main()
