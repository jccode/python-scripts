#!/bin/sh

# Usage: ssmgr_update_pwd.sh <port>

EXEC_SCRIPT=../ssmgr_update_pwd.py

SQLITE_DB=~/.ssmgr/webgui.sqlite
MANAGE_ADDRESS=127.0.0.1:4001
MANAGE_PASSWORD=123456

python $EXEC_SCRIPT -d $SQLITE_DB -m $MANAGE_ADDRESS -p $MANAGE_PASSWORD $1
