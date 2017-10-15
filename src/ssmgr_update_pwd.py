#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, getopt, sqlite3, random, string, socket, json, hashlib, time


def current_milli_time():
    return int(round(time.time() * 1000))


def hex_strip(i):
    """
    to hex string, strip prefix '0x'
    :param i:
    :return:
    """
    return hex(i)[2:]


class SSMgrClient(object):
    def __init__(self, ssmgr_address, password):
        self.buffer_size = 200
        addr = ssmgr_address.rsplit(':', 1)
        self.addr = (addr[0], int(addr[1]))
        self.password = password

    def _connect(self):
        self.cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.cli.connect(self.addr)

    def _close(self):
        self.cli.close()

    def send(self, cmd):
        self._connect()
        self.cli.sendall(bytearray.fromhex(self._pack_hex(cmd)))
        msg = self.cli.recv(self.buffer_size)
        self._close()
        return msg

    def _pack_hex(self, cmd):
        now = current_milli_time()
        data = json.dumps(cmd)
        length = len(data)+4+6  # 6: timestamp, 4: check_code
        check_code = self._md5(str(now) + data + self.password)  # hash

        length_buffer = ('0000'+hex_strip(length))[-4:]   # make sure 4 characters (2 bytes)
        time_buffer = '0' + hex_strip(now)
        data_buffer = data.encode("hex")
        check_code_buffer = check_code[:8]  # 8 characters, (4 bytes)

        return length_buffer + time_buffer + data_buffer + check_code_buffer

    def _md5(self, s):
        m = hashlib.md5()
        m.update(s)
        return m.hexdigest()

    def list(self):
        return self.send({'command': 'list'})

    def change_password(self, port, password):
        return self.send({'command': 'pwd', 'port': port, 'password': password})


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


def test_ssmgr(manager_address, password):
    mgr = SSMgrClient(manager_address, password)
    print mgr.list()


def testing(db, manager_address, password):
    print("Verifying the options")
    print("= SQLite =")
    test_sqlite(db)
    print("= Connecting to ssmgr %s =" % manager_address)
    test_ssmgr(manager_address, password)


def update_password(sqlite_db, port, manager_address, manager_password):
    pwd = update_sqlite(sqlite_db, port)
    mgr = SSMgrClient(manager_address, manager_password)
    mgr.change_password(port, pwd)


def main(argv):
    sqlite_db = os.path.expanduser("~/.ssmgr/webgui.sqlite")
    manager_address = "127.0.0.1:4001"
    password = "123456"
    test = False

    try:
        opts, args = getopt.getopt(argv, "htd:m:p:", ["db=","manager-address=","password="])
    except getopt.GetoptError:
        show_usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            show_usage()
            sys.exit()
        elif opt == '-t':
            test = True
        elif opt in ('-d', '--db'):
            sqlite_db = arg
        elif opt in ('-m', '--manager-address'):
            manager_address = arg
        elif opt in ('-p', '--password'):
            password = arg

    if test:
        testing(sqlite_db, manager_address, password)

    elif len(args) != 1:
        show_usage()

    else:
        update_password(sqlite_db, args[0], manager_address, password)


def show_usage():
    print('Usage: ssmgr_update_pwd.py <port>')
    print('')
    print(' Options')
    print('  -h                               show help')
    print('  -d, --db [file]                  sqlite db file. Default: ~/.ssmgr/webgui.sqlite')
    print('  -t                               testing, verify SQLite and ssmgr connection')
    print('  -m, --manager-address [address]  manager address. Default: 127.0.0.1:4001')
    print('  -p, --password [password]        manager password. Default: 123456')


if __name__ == '__main__':
    """
    Usage: ssmgr_update_pwd <port>
    Return: new password 
    """
    if len(sys.argv) <= 1:
        show_usage()
    else:
        main(sys.argv[1:])
