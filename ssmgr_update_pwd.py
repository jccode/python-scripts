#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os, sys, getopt, sqlite3, random, string, socket


def random_password(n):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))


def update_sqlite(db, port):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    pwd = random_password(6)
    c.execute("UPDATE account_plugin SET password = '%s' WHERE port = '%s'" % (pwd, port))
    conn.commit()
    conn.close()
    print pwd
    return pwd


def test_sqlite(db):
    conn = sqlite3.connect(db)
    try:
        with conn:
            print("Accounts: ")
            for port in conn.execute("SELECT port FROM account_plugin"):
                print(" - %s" % port)
    except Exception as e:
        print("sqlite db isn't valid")
    conn.close()


def main(argv):
    sqlite_db = os.path.expanduser("~/temp/vagrant-u1604/data/webgui.sqlite")
    try:
        opts, args = getopt.getopt(argv, "htd:", ["db="])
    except getopt.GetoptError:
        show_usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            show_usage()
            sys.exit()
        elif opt == '-t':
            test_sqlite(sqlite_db)
            sys.exit()
        elif opt in ('-d', '--db'):
            sqlite_db = arg
    if len(args) != 1:
        show_usage()
    update_sqlite(sqlite_db, args[0])


def show_usage():
    print('ssmgr_update_pwd.py <port>')
    print('  -h: show help')
    print('  -d, --db: sqlite db file. Default: ~/.ssmgr/webgui.sqlite')
    print('  -t: test, verify sqlite db is usable')


if __name__ == '__main__':
    """
    Usage: ssmgr_update_pwd <port>
    Return: new password 
    """
    if len(sys.argv) <= 1:
        show_usage()
    else:
        main(sys.argv[1:])
