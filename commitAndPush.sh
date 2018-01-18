#!/usr/bin/env bash
#usage ./commitAndPush.sh comment, comment is optional
if [ $# -eq 0 ]
  then
    comment="bug fixed"
  else
    comment="$@"
fi

git add main commitAndPush.sh;
git add Resources/ Loot/ Other/ ;
git commit -m "$comment";
git push origin master;
git push heroku master;
