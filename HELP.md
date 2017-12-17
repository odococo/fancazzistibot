For any of the above commands to work you need to be in the fancazzistibot repository

If the robot is experiencing some unwanted behavior you would want to kill it, use:
`heroku ps:scale web=0` in the terminal window where your repository is located to kill the application
To restart it use `heroku ps:scale web=1`

If you want to connect to the database use the command:
`heroku pg:psql`