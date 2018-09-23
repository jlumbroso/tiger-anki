#!/usr/bin/env python3

import hashlib
import os
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

IMG_DIR="images/"

def tigerbook_imgpath(netid=None, jpeg=False):
    if netid and not "{{" in netid:
        netid = netid.lower()
    else:
        netid = "{{Netid}}"
    ext = "png"
    if jpeg:
        ext = "jpeg"
    return "{}{}.{}".format(IMG_DIR, netid, ext)

def tigerbook_lookup(netid):
    r = requests.get(
        url=urllib.parse.urljoin(TIGERBOOK_API, netid),
        headers=get_wsse_headers(TIGERBOOK_USR, TIGERBOOK_KEY))
    if r.ok:
        data = r.json()

        # Also retrieve and save image in local directory
        r = requests.get(
            url=data.get(
                "photo_link",
                urllib.parse.urljoin(TIGERBOOK_IMG, netid)),
            headers=get_wsse_headers(TIGERBOOK_USR, TIGERBOOK_KEY))
        
        if r.ok and not os.path.exists(tigerbook_imgpath(netid=netid)):
            image = r.content
            open(tigerbook_imgpath(netid=netid), "wb").write(image)
        
        return data

anki_undergrad_model = genanki.Model(
  1941463750,
  'Princeton Undergrad',
  fields=[
    {'name': 'Name'},
    {'name': 'Netid'},
    {'name': 'Image'}
  ],
  templates=[
    {
      'name': 'Name to Face',
      'qfmt': '{{Name}}',
      'afmt': (
          '{{FrontSide}}<hr id="answer">{{Image}}'
      ),
    },
    {
      'name': 'Face to Name',
      'qfmt': '{{Image}}' ,
      'afmt': '{{FrontSide}}<hr id="answer">{{Name}}',
    },
  ])


def create_deck(students, name="Princeton Undergrads"):
    deck_id = random.randrange(1 << 30, 1 << 31)
    deck_obj = genanki.Deck(
        deck_id,
        name)
    
    deck_obj.add_model(anki_undergrad_model)

    for student in students:
        student_info = tigerbook_lookup(netid=student)
        if student_info == None:
            continue

        student_note = genanki.Note(
            model=anki_undergrad_model,
            fields=[
                "{full_name}".format(**student_info),
                "{net_id}".format(**student_info),
                "<img src='{}' />".format(tigerbook_imgpath(netid=student))])

        deck_obj.add_note(student_note)
    
    package_obj = genanki.Package(deck_obj)
    package_obj.media_files = list(map(
        lambda x: tigerbook_imgpath(netid=x), students)) + ["al38.jpeg"]
    
    package_obj.write_to_file('output.apkg')


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

@click.command()
@click.option("-v", "--validate/--no-validate", default=False)
@click.option("-u", "--user", default=TIGERBOOK_USR, help="Tigerbook API username", prompt=(TIGERBOOK_USR==None))
@click.option("-k", "--key", default=TIGERBOOK_KEY, help="Tigerbook API key", prompt=(TIGERBOOK_KEY==None))
@click.option("-o", "--output", default="deck.apkg", help="Filename for created deck")
@click.argument("students", nargs=-1)
def cli_root(validate, user, key, output, students):
    print(validate, user, key, output, students)

if __name__ == "__main__" and len(sys.argv) > 0 and sys.argv[0] != "":
    cli_root()
