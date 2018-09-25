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

try:
    from tigerbook_credentials import API_KEY as TIGERBOOK_KEY
    from tigerbook_credentials import USERNAME as TIGERBOOK_USR
except ImportError:
    TIGERBOOK_USR = os.environ.get("TIGERBOOK_USR", None)
    TIGERBOOK_KEY = os.environ.get("TIGERBOOK_KEY", None)

TIGERBOOK_IMG="https://tigerbook.herokuapp.com/images/"
TIGERBOOK_API="https://tigerbook.herokuapp.com/api/v1/undergraduates/"
TIGERBOOK_CACHE = {}

def tigerbook_load_cache():
    global TIGERBOOK_CACHE
    try:
        if cache:
            TIGERBOOK_CACHE = json.loads(open(tigerbook_imgpath("data.json")).read())
    except:
        TIGERBOOK_CACHE = {}

def tigerbook_save_cache():
    global TIGERBOOK_CACHE
    try:
        if cache:
            with open(tigerbook_imgpath("data.json"), "w") as f:
                f.write(json.dumps(TIGERBOOK_CACHE, indent=2))
    except:
        pass

IMG_DIR="images/"

def tigerbook_imgpath(netid=None, no_prefix=False):
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

def tigerbook_lookup(netid):
    global TIGERBOOK_CACHE

    # Cached the directory info
    if netid in TIGERBOOK_CACHE:
        # And also cached the student photo
        if os.path.exists(tigerbook_imgpath(netid=netid, no_prefix=True)):
            # So no need to make any requests
            return TIGERBOOK_CACHE[netid]

    r = requests.get(
        url=urllib.parse.urljoin(TIGERBOOK_API, netid),
        headers=get_wsse_headers(TIGERBOOK_USR, TIGERBOOK_KEY))

    if r.ok:
        data = r.json()
        TIGERBOOK_CACHE[netid] = data

        # Also retrieve and save image in local directory
        r = requests.get(
            url=data.get(
                "photo_link",
                urllib.parse.urljoin(TIGERBOOK_IMG, netid)),
            headers=get_wsse_headers(TIGERBOOK_USR, TIGERBOOK_KEY))
        
        if r.ok and not os.path.exists(tigerbook_imgpath(netid=netid, no_prefix=True)):
            image = r.content
            open(tigerbook_imgpath(netid=netid, no_prefix=True), "wb").write(image)
        
        return data

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


def create_deck(students, name="Princeton Undergrads", output="output.apkg"):
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

    added_students = []

    for student in students:
        student_info = tigerbook_lookup(netid=student)

        # No student info
        if student_info == None:
            continue
        
        # No photo
        if not os.path.exists(tigerbook_imgpath(netid=student, no_prefix=True)):
            continue

        added_students.append(student)

        student_note = genanki.Note(
            model=anki_undergrad_model,
            fields=[
                "{full_name}".format(**student_info),
                "{net_id}".format(**student_info),
                "<img src='{}' />".format(tigerbook_imgpath(netid=student, no_prefix=True))])

        deck_obj.add_note(student_note)

    package_obj = genanki.Package(deck_obj)
    package_obj.media_files = list(map(
        lambda x: tigerbook_imgpath(netid=x, no_prefix=True), added_students))
    
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
    global TIGERBOOK_CACHE

    # Print help message if no students provided:
    if len(students) == 0:
        click_print_help_msg(cli_root, "tiger-anki")
        return

    # Load Tigerbook cache
    tigerbook_load_cache()

    # Pre-filter NetIDs
    if check:
        students = list(filter(validate_netid, students))
    
    # Update credentials
    TIGERBOOK_USR = user
    TIGERBOOK_KEY = key

    # Create the deck
    create_deck(
        students=students,
        name=title,
        output=output)

    # Save Tigerbook cache
    tigerbook_save_cache()

if __name__ == "__main__" and len(sys.argv) > 0 and sys.argv[0] != "":
    cli_root()
