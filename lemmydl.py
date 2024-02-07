#!/bin/env python
"""
lemmydl.py

A lemmy downloader script in python using the pythorhead lemmy API python library

This code is licensed under the GNU GPLv3, copyright © 2024 © max 74.25 <maximillian[at]disroot[dot]org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by 
the Free Software Foundation, either version 3 of the License, or 
(at your option) any later version.

This program is distributed in the hope that it will be useful, but 
WITHOUT ANY WARRANTY; without even the implied warranty of 
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the 
GNU General Public License for more details.
 
You should have received a copy of the GNU General Public License 
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""


from pythorhead import Lemmy
from pythorhead.types import SortType, ListingType

from pathlib import Path
import os, re, unicodedata, json, requests, argparse, math, time, tomllib, subprocess, sys

from typing import Any, List, Optional

colors = (sys.platform != 'win32')

request_delay = 1

def pprint_sl(string, fmt):
    if colors:
        sys.stdout.write('\r')
        sys.stdout.write(f"\x1b[{fmt}m{string}\x1b[0m")
        sys.stdout.flush()
    else:
        sys.stdout.write('\r')
        sys.stdout.write(string)
        sys.stdout.flush()
def pprint(string, fmt): 
    if colors: print(f"\x1b[{fmt}m{string}\x1b[0m")
    else: print(string)
def pstr(string, fmt): 
    if colors: return f"\x1b[{fmt}m{string}\x1b[0m" 
    else: return string

# finds all the urls in a string
def find_urls(string) -> list:
    regex = r"(?:(?:https?):\/\/|www\.)(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[-A-Z0-9+&@#\/%=~_|$?!:,.])*(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[A-Z0-9+&@#\/%=~_|$])"
    if args.verbose: print("Finding urls in string:", string)
    url = re.findall(regex, string)
    return [x[0] for x in url]

# returns if the image url ends in a media suffix
def is_image_url(url):
    if url.split(".")[-1].lower() in ["png", "webp", "jpg", "jpeg", "gif", "mp4", "mkv", "mp3", "ogg", "flac", "m4a", "mov", "opus", "apng", "avif", "jfif", "svg", "bmp", "ico", "tif", "tiff"]:
        return True
# 
def clean_text(text):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. ~~Convert to lowercase~~ // not that. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    text = str(text)
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    if dont_clean_text:
        return text
    if args.verbose: print("body text: `", text, "`") 
    text = re.sub(r'[^\w\s-]', '', text) #.lower()
    return re.sub(r'[-\s]+', '-', text).strip('-_')

def download_file(url, file_path):
    file_path = Path(file_path)
    try:
        response = requests.get(url, stream=True, timeout=15)

        with file_path.open(mode="wb") as file:
            for chunk in response.iter_content(chunk_size=10 * 1024):
                file.write(chunk)
    except requests.exceptions.Timeout:
        if args.verbose: print("Connection timed out", url)
    except Exception as e:
        pprint(f"Exception occured when connecting to URL ({url}): {e}", "1;31")

def get_media_posts(post_list):
    media_posts = []
    for post in post_list:
        image_urls = []
        use_post = False
        if args.all:
            use_post = True
        if "url" in post["post"]:
            if is_image_url(post["post"]["url"]):
                image_urls.append(post["post"]["url"])
                use_post = True
        if "body" in post["post"]:
            body = post["post"]["body"]
            urls = find_urls(body)
            for url in urls:
                if is_image_url(url):
                    image_urls.append(url)
                    use_post = True
        post["media"] = image_urls
        if use_post:
            if args.verbose: print("downloading post !! : ", post["post"]["name"])
            media_posts.append(post)
    return media_posts

def download_posts(page, post_list, count):
    counter = 1
    for post in post_list:
        pprint_sl(f"Getting post {counter} of 20 in group {page} (actual {counter + (page * 20) - 20}/{count})...", "0;32")
        if (counter + (page * 20) - 20) - count >= 0:
            return
        # get community name and process it 
        community = post["community"]
        community_name = community["name"]
        community_path = Path(base_directory, clean_text(community_name))
        # make dir of community
        if not community_path.exists() and not community_path.is_dir():
            community_path.mkdir(parents=True)
            if args.verbose: print("Created Community Path:", community_path)
            metadata_path = community_path / "community.json"
            
            # if making a new dir save community metadata
            metadata_path.write_text(json.dumps(community))

        # make dir of post
        post_data = post["post"]
        post_name = post_data["name"]
        post_path = community_path / str( str(post_data["id"]) + "_" + clean_text(post_name) )
        
        if args.verbose: print("Saving \"", post_name, "\" to ", post_path)

        if not post_path.exists() and not post_path.is_dir():
            post_path.mkdir(parents=True)
            
            # download each image file
            for file in post["media"]:
                file_name = file.split("/")[-1]
                file_path = Path(post_path) / file_name
                if args.verbose: print("Downloading file: ", file_path)

                download_file(file, file_path)
            
            # dump post json in a file
            post_data_path = post_path / str( clean_text(post_name) + ".json" )
            post_data_path.write_text(json.dumps(post))

            # download comments for the post
            post_comments = lemmy.comment.list(post_id=post_data["id"])
            post_comments_path = post_path / "comments.json" 
            post_comments_path.write_text(json.dumps(post_comments))
            time.sleep(request_delay)
        counter += 1

def get_post_list(count=0, community_id: Optional[int]=None, community_name: Optional[str]=None, sort_type: Optional[SortType]=None, list_type: Optional[ListingType]=None):
    posts_per_page = 20
    pprint(f"Getting ~{count} posts in groups of {posts_per_page}", "0;34")
    pages = int(math.ceil(count/posts_per_page))
    if args.verbose: print("Total number of pages:", pages)
    for page in range(1, pages + 1):
        if args.verbose: print("Getting page", page, "of", pages)
        if list_type == ListingType.Community:
            post_list = lemmy.post.list(page=page, limit=posts_per_page, community_id=community_id, community_name=community_name, sort=sort_type) # note to self: pages start at 1
            time.sleep(request_delay)
        else: 
            post_list = lemmy.post.list(page=page, limit=posts_per_page, sort=sort_type, type_=list_type) # note to self: pages start at 1
            time.sleep(request_delay)
        if post_list is not None:
            media_posts = get_media_posts(post_list)
            if media_posts is not None:
                download_posts(page, media_posts, count)
#"""
"""
TODO

nicer print statements w ansi colors
maybe a smart like progresss cli a la pacman or smthn => sys.write("\rajskfhshfkjsj") + sys.flush()

"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                        prog=pstr('lemmydl', '4;37'),
                        description=pstr('a lemmy downloader', '1;37'),
                        epilog=pstr('made w/ love by maxy <3', '1;35')
                        )

    parser.add_argument("-i", "--instance", help=pstr("the url of the lemmy instance you are using", "0;36"), type=str)
    parser.add_argument("-u", "--username", help=pstr("the username to use when logging into the lemmy instance", "0;36"), type=str)
    parser.add_argument("-p", "--password", help=pstr("the password to use when logging into the lemmy instance", "0;36"), type=str)

    parser.add_argument("-n", "--number", help=pstr("the number of posts to get", "0;36"), type=int, default=20)
    parser.add_argument("-m", "--max", help=pstr("get all the posts in a community, only works if getting a community, doesn't work with feeds", "0;36"), action='store_true', default=False)
    parser.add_argument("-c", "--community", help=pstr("the name or id of the community to get. e.g. <name> for a local community and <name>@instance.net for a federated one. for a numerically name community, use the full federated name .", "0;36"))
    parser.add_argument("-s", "--sort", help=pstr("the way to sort the posts (default: new)", "0;36"), choices=[
        'hot', 'new', 'old', 'active', 'top_all', 'top_day', 'top_week', 'top_month', 'top_year', 'top_hour', 'top_sixhour', 'top_twelvehour', 'new_comments', 'most_comments'
    ], default='new')

    parser.add_argument("-f", "--feed", help=pstr("the name of the feed to get (default: community)", "0;36"), choices=['all', 'community', 'local', 'subscribed'], default='community')
    parser.add_argument("-o", "--output_dir", help=pstr("specify the name of the output directory downloads are stored in", "0;36"), type=str)
    parser.add_argument("-a", "--all", help=pstr("get all posts, not just the ones with media in them", "0;36"), action='store_true')
    parser.add_argument("-t", "--dont_clean_text", help=pstr("don't clean post and community path names (not recommended for windows systems, off by default)", "0;36"), action='store_true')
    parser.add_argument("-x", "--config", help=pstr("path for a config file [config files not implemented yet !!]", "0;36"), type=str)
    parser.add_argument("-v", "--verbose", help=pstr("prints verbose log", "0;36"), action="store_true")
    parser.add_argument("-b", "--no-colors", help=pstr("disables ansi color output", "0;36"), action="store_true")

    '''
    Arguments: 
        username
        password
        instance_url
        count
        max - get all the posts from the community << optional
        community - id or name or url << optional
        sort type << optional
        feed name - subscribed all local etc << optional
        dir_name << optional
        all_posts - get all posts, not just the ones with media in them << optional
        dont_clean_text - on by default, makes text not utf8 and replaces spaces with dashes
        config - the config file to use (take precidence over config directories) << optional
        verbose - logs all the things [not implemented]
    '''

    args = parser.parse_args()
    if args.verbose: print("Arguments:", args)

    colors = (sys.platform != 'win32')
    if args.no_colors:
        colors = False

    config_path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config/"), "lemmydl/config.toml").resolve()
    if args.verbose: print("Config Path:", config_path)
    config_file = {}
    if config_path.exists():
        if args.verbose: print("config path exists!!")
        config_file = tomllib.load(config_path.open("rb"))
        if args.verbose: print("Config:", config_file)

    username = config_file.get("username")
    password = config_file.get("password")
    instance_url = config_file.get("instance")
    dont_clean_text = config_file.get("dont_clean_text")
    output_dir = str(Path(config_file.get("output_dir").replace("~", str(Path.home()))).resolve())
    # request_delay = config_file.get("request_delay")
    get_max = config_file.get("get_max")

    if config_file.get("password_command"):
        pw_cmd = subprocess.run(config_file.get("password_command"), 
                                stdout=subprocess.PIPE, 
                                shell=True, 
                                timeout=30,
                                text=True
                                ) # python 3.5 or higher
        password = pw_cmd.stdout.strip()

    if args.verbose: print(username, password, instance_url, clean_text, output_dir)

    if args.output_dir: output_dir = args.output_dir
    if args.dont_clean_text: 
        dont_clean_text = args.dont_clean_text
    else:
        dont_clean_text = False

    if output_dir.startswith('/') or output_dir.startswith('~'):
        base_directory = Path(output_dir)
    else: # assumes the path given is relative to the script pwd
        base_directory = Path.cwd() / output_dir

    if args.verbose: print("Base directory:", base_directory)

    if args.instance: instance_url = args.instance
    if args.username: username = args.username
    if args.password: password = args.password

    request_delay = 1

    get_max = args.max

    instance_url = instance_url.strip("/") # it doesnt agree with trailing /'s
    if not "http" in instance_url: # add the protocol if it doesnt have it
        instance_url = "https://" + instance_url

    feed_type = None
    if args.feed == "all":
        feed_type = ListingType.All
    elif args.feed == "community":
        feed_type = ListingType.Community
    elif args.feed == "local":
        feed_type = ListingType.Local
    elif args.feed == "subscribed":
        feed_type = ListingType.Subscribed


    if args.verbose: print("Feed Type:", feed_type)

    sort_type = None
    if args.sort == "hot":
        sort_type = SortType.Hot
    elif args.sort == "new":
        sort_type = SortType.New
    elif args.sort == "old":
        sort_type = SortType.Old
    elif args.sort == "active":
        sort_type = SortType.Active
    elif args.sort == "top_all":
        sort_type = SortType.TopAll
    elif args.sort == "top_day":
        sort_type = SortType.TopDay
    elif args.sort == "top_week":
        sort_type = SortType.TopWeek
    elif args.sort == "top_month":
        sort_type = SortType.TopMonth
    elif args.sort == "top_year":
        sort_type = SortType.TopYear
    elif args.sort == "top_hour":
        sort_type = SortType.TopHour
    elif args.sort == "top_sixhour":
        sort_type = SortType.TopSixHour
    elif args.sort == "top_twelvehour":
        sort_type = SortType.TopTwelveHour
    elif args.sort == "new_comments":
        sort_type = SortType.NewComments
    elif args.sort == "most_comments":
        sort_type = SortType.MostComments
    if args.verbose: print("Sorting Type", sort_type)

    community_id = None
    community_name = None

    if args.feed == "community":
        if args.community != None:
            try:
                community_id = int(args.community)
            except Exception as e:
                try:
                    community_name = str(args.community)
                except Exception as e2:
                    if args.verbose: print(e, e2)
        else:
            raise Exception("You need to specify a community!")

    if args.verbose: print("Community ID:", community_id)
    if args.verbose: print("Community Name:", community_name)

    if username == None or password == None or instance_url == None:
        raise Exception("You must specify a username, password and instance !!")

    lemmy = Lemmy(instance_url)
    lemmy.log_in(username, password)
    pprint("Successfully logged in!", "1;32")
    time.sleep(request_delay)
    if args.verbose: print(args.number, community_id, community_name, sort_type, feed_type)

    number = args.number
    if get_max and (community_id != None or community_name != None):
        disc = lemmy.discover_community(community_name)
        time.sleep(request_delay)
        comm = lemmy.community.get(id=community_id, name=community_name)
        time.sleep(request_delay)
        number = comm["community_view"]["counts"]["posts"]
        if args.verbose: print("Total posts:", number)

    get_post_list(number, community_id, community_name, sort_type, feed_type)
    pprint(f"\nSuccess !! :3", "1;32")
    # """
