#!/usr/bin/env bash
if [ $# -eq 0 ]
  then
    comment="bug fixed"
  else
    comment=$1
fi

git add main bot_classes.py db_call.py utils.py  comandi.py ;
git commit -m "$comment";
git push origin master;
