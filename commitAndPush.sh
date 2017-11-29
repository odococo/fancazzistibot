#!/usr/bin/env bash
#usage ./commitAndPush.sh comment, comment is optional
if [ $# -eq 0 ]
  then
    comment="bug fixed"
  else
    comment="$@"
fi

git add main bot_classes.py db_call.py utils.py comandi.py commitAndPush.sh README.md;
git commit -m "$comment";
git push origin master;
