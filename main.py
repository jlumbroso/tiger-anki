#!/usr/bin/env python3

import hashlib
import os
import json
import random
import sys
import urllib.parse
import urllib.request
from base64 import b64encode
from datetime import datetime

import click
import genanki
import requests

###############################################################################

try:
    from tigerbook_credentials import API_KEY as TIGERBOOK_KEY
    from tigerbook_credentials import USERNAME as TIGERBOOK_USR
except ImportError:
    TIGERBOOK_USR = os.environ.get("TIGERBOOK_USR", None)
    TIGERBOOK_KEY = os.environ.get("TIGERBOOK_KEY", None)

TIGERBOOK_IMG="https://tigerbook.herokuapp.com/images/"
TIGERBOOK_API="https://tigerbook.herokuapp.com/api/v1/undergraduates/"

###############################################################################

DEBUG=True

def _printdebug(msg="debug print message"):
    if DEBUG:
        from inspect import currentframe, getframeinfo
        callingframe = currentframe().f_back
        cf_info = getframeinfo(callingframe)
        print("{filename}:{line}: {msg}".format(
            filename=cf_info.filename,
            line=cf_info.lineno,
            msg=msg))

###############################################################################

LOCAL_CACHE_DICT = {}

def cache_load():
    global LOCAL_CACHE_DICT
    try:
        LOCAL_CACHE_DICT = json.loads(
            open(cache_buildpath("data.json")).read())
    except:
        LOCAL_CACHE_DICT = {}
    
    # Try to load CS people
    try:
        import cs_people
        cs_people_dict = cs_people.loadfeeds()
        _printdebug(cs_people_dict)
        cs_people_dict = cs_people.filter_pictureless(cs_people_dict)
        _printdebug(cs_people_dict)
        for row in cs_people_dict.values():
            row["source"] = "cs"
        _printdebug(cs_people_dict)
        LOCAL_CACHE_DICT.update(cs_people_dict)
    except ImportError:
        raise
        _printdebug("import err for cs_people")

def cache_save():
    global LOCAL_CACHE_DICT
    try:
        with open(cache_buildpath("data.json"), "w") as f:
            f.write(json.dumps(LOCAL_CACHE_DICT, indent=2))
    except:
        pass

IMG_DIR="images/"

def cache_buildpath(netid=None, no_prefix=False):
    if netid and not "{{" in netid:
        netid = netid.lower()
    else:
        netid = "{{Netid}}"
    ext = ".png"
    if ".json" in netid:
        ext = ""
    if no_prefix:
        return "{}{}".format(netid, ext)
    else:
        return "{}{}{}".format(IMG_DIR, netid, ext)

###############################################################################

def lookup(netid):

    person = None

    try:
        person = cs_lookup(netid=netid)
    except:
        person = None
        raise

    if person:
        return person
    
    try:
        person = tigerbook_lookup(netid=netid)
    except:
        person = None
        raise
        
    if person:
        return person

def cs_lookup(netid):
    global LOCAL_CACHE_DICT
    _printdebug()
    # Cached the directory info
    if netid in LOCAL_CACHE_DICT:
        _printdebug()
        record = LOCAL_CACHE_DICT[netid]

        # First check that it is a Tigerbook entry
        if "source" in record and record["source"] == "cs":
            _printdebug()
            # And also cached the student photo
            if os.path.exists(cache_buildpath(netid=netid)):
                _printdebug()
                # So no need to make any requests
                return LOCAL_CACHE_DICT[netid]

            elif "photo_link" in record:
                _printdebug()
                # Retrieve and save image in local directory
                r = requests.get(url=record["photo_link"])
                
                if r.ok and not os.path.exists(cache_buildpath(netid=netid)):
                    _printdebug()
                    image = r.content
                    open(cache_buildpath(netid=netid), "wb").write(image)
                    return LOCAL_CACHE_DICT[netid]
    _printdebug()
    # CS people cannot be returned if not from cache
    return None

def tigerbook_lookup(netid):
    global LOCAL_CACHE_DICT
    _printdebug(netid in LOCAL_CACHE_DICT)
    # Cached the directory info
    if netid in LOCAL_CACHE_DICT:
        _printdebug()
        record = LOCAL_CACHE_DICT[netid]
        _printdebug()
        # First check that it is a Tigerbook entry
        if "source" in record and record["source"] == "tigerbook":
            # And also cached the student photo
            _printdebug()
            if os.path.exists(cache_buildpath(netid=netid)):
                # So no need to make any requests
                _printdebug()
                return LOCAL_CACHE_DICT[netid]

    r = requests.get(
        url=urllib.parse.urljoin(TIGERBOOK_API, netid),
        headers=get_wsse_headers(TIGERBOOK_USR, TIGERBOOK_KEY))
    _printdebug((TIGERBOOK_USR, TIGERBOOK_KEY))
    _printdebug(urllib.parse.urljoin(TIGERBOOK_API, netid))
    _printdebug((r.status_code, r.content))

    if r.ok:
        _printdebug()
        data = r.json()
        data["source"] = "tigerbook"
        LOCAL_CACHE_DICT[netid] = data
        _printdebug()
        # Also retrieve and save image in local directory
        r = requests.get(
            url=data.get(
                "photo_link",
                urllib.parse.urljoin(TIGERBOOK_IMG, netid)),
            headers=get_wsse_headers(TIGERBOOK_USR, TIGERBOOK_KEY))
        
        if r.ok and not os.path.exists(cache_buildpath(netid=netid)):
            _printdebug()
            image = r.content
            open(cache_buildpath(netid=netid), "wb").write(image)
        _printdebug(data)
        return data

###############################################################################

anki_undergrad_model = genanki.Model(
  1941463750,
  'Princeton Undergraduate Student',
  fields=[
    {'name': 'Name'},
    {'name': 'Netid'},
    {'name': 'Image'}
  ],
  templates=[
    {
      'name': 'Face to Name',
      'qfmt': '{{Image}}' ,
      'afmt': '{{FrontSide}}<hr id="answer">{{Name}}',
    },
    {
      'name': 'Name to Face',
      'qfmt': '{{Name}}',
      'afmt': (
          '{{FrontSide}}<hr id="answer">{{Image}}'
      ),
    },
  ])


def create_deck(persons, name="Princeton Undergrads", output="output.apkg"):

    # Validate the persons that were requested

    validated_persons = []

    for person_id in persons:
        person = lookup(netid=person_id)

        # No student info
        if person == None:
            continue
        
        # No photo
        if not os.path.exists(cache_buildpath(netid=person_id)):
            continue
        
        validated_persons.append((person_id, person))
    
    validated_persons_id = map(lambda pair: pair[0], validated_persons)

    # Build the deck

    deck_id = random.randrange(1 << 30, 1 << 31)
    deck_obj = genanki.Deck(
        deck_id,
        name)
    
    deck_obj.add_model(anki_undergrad_model)

    initial_cwd = os.getcwd()
    try:
        if not os.path.exists(IMG_DIR):
            os.mkdir(IMG_DIR)
    except:
        pass
    finally:
        os.chdir(IMG_DIR)

    for (person_id, person_info) in validated_persons:
        student_note = genanki.Note(
            model=anki_undergrad_model,
            fields=[
                "{full_name}".format(**person_info),
                "{net_id}".format(**person_info),
                "<img src='{}' />".format(cache_buildpath(netid=person_id, no_prefix=True))])
        
        deck_obj.add_note(student_note)

    package_obj = genanki.Package(deck_obj)
    package_obj.media_files = list(map(
        lambda x: cache_buildpath(netid=x, no_prefix=True), validated_persons_id))
    
    package_obj.write_to_file(os.path.join(initial_cwd, output))
    os.chdir(initial_cwd)


def get_wsse_headers(username, password):
    """
    Returns the WSSE headers needed for authentication
    into the Tigerbook API / website.
    """
    if username == None or password == None:
        return {}
    
    NONCE_SIGNATURE = (
        "0123456789abcdefghijklmnopqrstuvwxyz" +
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ+/=")
    rand_chars = ''.join([random.choice(NONCE_SIGNATURE) for i in range(32)])
    nonce = b64encode(rand_chars.encode("ascii")).decode("ascii")
    created = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    digest = b64encode(hashlib.sha256((nonce + created + password).encode('ascii')).digest())
    headers = {
        'Authorization': 'WSSE profile="UsernameToken"',
        'X-WSSE': ('UsernameToken Username="%s", PasswordDigest="%s", '
                   + 'Nonce="%s", Created="%s"')
                  % (username, digest.decode("ascii"), nonce, created)
    }
    return headers

def validate_netid(s):
    if s == None or not type(s) is str or len(s) == 0 or len(s) > 8:
        return False
    return s.isalnum()

def click_print_help_msg(command, info_name):
    with click.Context(command, info_name=info_name) as ctx:
        click.echo(command.get_help(ctx))

@click.command()
@click.option("-c", "--check/--no-check", default=False, help="Prefilter provided student NetIDs")
@click.option("-u", "--user", default=TIGERBOOK_USR, help="Tigerbook API username", prompt=(TIGERBOOK_USR==None))
@click.option("-k", "--key", default=TIGERBOOK_KEY, help="Tigerbook API key", prompt=(TIGERBOOK_KEY==None))
@click.option("-n", "--cache/--no-cache", default=True, help="Tigerbook API cache")
@click.option("-o", "--output", default="deck.apkg", help="Filename for created deck")
@click.option("-t", "--title", default="Princeton Undergraduates", help="Name of the Deck")
@click.argument("students", nargs=-1)
def cli_root(check, user, key, cache, output, title, students):
    """
    Generate an Anki deck to learn the names of a set of Princeton undergraduate
    students, specified by their NetID (official, eight alphanumerical character long,
    student identifier).
    """
    global LOCAL_CACHE_DICT

    # Print help message if no students provided:
    if len(students) == 0:
        click_print_help_msg(cli_root, "tiger-anki")
        return

    # Load Tigerbook cache
    cache_load()

    # Pre-filter NetIDs
    if check:
        students = list(filter(validate_netid, students))
    
    # Update credentials
    TIGERBOOK_USR = user
    TIGERBOOK_KEY = key

    # Create the deck
    create_deck(
        persons=students,
        name=title,
        output=output)

    # Save Tigerbook cache
    cache_save()

if __name__ == "__main__" and len(sys.argv) > 0 and sys.argv[0] != "":
    cli_root()
