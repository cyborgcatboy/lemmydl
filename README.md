# lemmydl
a lemmy downloader python script meow !

## installation
install the (singular) requirement in requirements.txt, which is [pythorhead](https://github.com/db0/pythorhead/), a python Lemmy API, the you can run lemmydl.py!

lemmydl.py can be executed either with or without python.

Made with python 3.11, should work on any python 3.6+ 

## usage
refer to `lemmydl.py --help` for command line arguments.

## examples

`python lemmydl.py -u username -p password -i lemmy.instance.com -c community -n 40` - connects to lemmy.instance.com with the credentials username and password, and gets the newest 40 posts from community@lemmy.instance.com

`lemmydl.py -x config.toml -c community -m -s top_all` - uses the pwd's config.toml as a config, and gets all the posts in community, sorted by the top of all 17:47

`./lemmydl.py -f subscribed -s top_day -n 100 -o todays_top_100 -t -b` - gets the top 100 posts from the users' subscribed feed, without cleaning filenames and outputting non-colored text.

## License
This code is licensed under the GNU GPLv3 meow :3
