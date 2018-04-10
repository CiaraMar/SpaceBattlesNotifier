#!/bin/sh
DIR=`date +%m%d%y`
DEST=/db_backups/$DIR
mkdir -p $DEST
mongodump -v -h localhost --db sb_notif_data -o $DEST