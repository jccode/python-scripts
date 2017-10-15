#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, getopt, sqlite3, random, string, socket, json, struct, hashlib, time
from datetime import datetime


class SSCmd(object):
    """
    Shadowsocks manager-api command
    """
    def __init__(self, manager_address):
        self.buffer_size = 1024 * 8
        if ':' in manager_address:
            addr = manager_address.rsplit(':', 1)
            self.addr = (addr[0], int(addr[1]))
            self.cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            self.addr = manager_address
            self.cli = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    def _connect(self):
        self.cli.connect(self.addr)

    def _close(self):
        self.cli.close()

    def _send(self, cmd, payload=None):
        self._connect()
        msg = self._send_raw(cmd, payload)
        self._close()
        return msg

    def _send_raw(self, cmd, payload=None):
        pl = (cmd + ':' + json.dumps(payload)) if payload else cmd
        self.cli.send(pl.encode())
        msg = self.cli.recv(self.buffer_size).decode()
        return msg

    def ping(self):
        return self._send(b"ping")

    def add_port(self, port, password):
        return self._send("add", {"server_port": port, "password": password})

    def remove_port(self, port):
        return self._send('remove', {'server_port': port})

    def change_password(self, port, password):
        self._connect()
        self._send_raw("add", {"server_port": port, "password": password})
        result = self._send_raw('remove', {'server_port': port})
        self._close()
        return result
        # self.remove_port(port)
        # return self.add_port(port, password)


def current_milli_time():
    return int(round(time.time() * 1000))


def milli_time_to_date(millis):
    return datetime.fromtimestamp(millis)


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


class SSMgr(object):
    def __init__(self, ssmgr_address, password):
        self.buffer_size = 200
        addr = ssmgr_address.rsplit(':', 1)
        self.addr = (addr[0], int(addr[1]))
        self.password = password

    def __enter__(self):
        self.cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.cli.connect(self.addr)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cli.close()

    def send(self, cmd):
        self.cli.sendall(bytearray.fromhex(self._pack_hex(cmd)))
        msg = self.cli.recv(self.buffer_size)
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


def test2(manager_address, password):
    print('%s,%s' % (manager_address, password))
    cmd = {'command': 'list'}
    mgr = SSMgrClient(manager_address, password)

    print mgr._pack_hex(cmd)
    print("--------------------------")
    print(mgr.send({'command': 'list'}))
    print("Change password 8390")
    print(mgr.send({'command': 'pwd', 'port': '8390', 'password': 'nhello1'}))
    print("--------------------------")
    print(mgr.send({'command': 'list'}))

    print("================================")

    with SSMgr(manager_address, password) as mgr2:
        print(mgr2._pack_hex(cmd))
        print("------------------------")
        print(mgr2.send({'command': 'list'}))
        print("Change password 8390")
        print(mgr2.send({'command': 'pwd', 'port': '8390', 'password': 'nhello2'}))
        print("--------------------------")
        print(mgr2.send({'command': 'list'}))


def update_password(sqlite_db, port, manager_address):
    sscmd = SSCmd(manager_address)
    pwd = update_sqlite(sqlite_db, port)
    sscmd.change_password(port, pwd)


def main(argv):
    sqlite_db = os.path.expanduser("~/temp/vagrant-u1604/data/webgui.sqlite")
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

    if len(args) != 1:
        show_usage()

    if test:
        # test_sqlite(sqlite_db)
        test2(manager_address, password)
        sys.exit()

    update_password(sqlite_db, args[0], manager_address)


def show_usage():
    print('Usage: ssmgr_update_pwd.py <port>')
    print('')
    print(' Options')
    print('  -h                               show help')
    print('  -d, --db [file]                  sqlite db file. Default: ~/.ssmgr/webgui.sqlite')
    print('  -t                               test, verify sqlite db is usable')
    print('  -m, --manager-address [address]  manager address. Default: 127.0.0.1:8383')
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
