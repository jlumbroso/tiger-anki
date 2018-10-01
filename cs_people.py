import re
from urllib.parse import urljoin

import bs4
import requests

CS_BASE_ENDPOINT="http://www.cs.princeton.edu/people/"
CATEGORIES=["faculty", "research", "researchinstructors", "restech", "admins", "grad"]
SUBTYPES=["main", "emeritus", "associated"]

def filter_pictureless(people, as_dict=None):

    if type(people) is dict:
        if as_dict == None:
            as_dict = True
        people = people.values()

    if as_dict == None:
        as_dict = False

    filtered_list = [
        p
        for p in people
        if "photo_link" in p and not "default.png" in p["photo_link"]
    ]

    if as_dict:
        return { p["net_id"]: p for p in filtered_list }
    else:
        return filtered_list

def loadfeed(category="faculty", subtype=None):
    
    # Validate the category and subtype
    category = category.lower().strip()
    if not category in CATEGORIES:
        return None
    if category == "faculty" and subtype != None:
        subtype = subtype.lower().strip()
        if not subtype in SUBTYPES:
            return None
    
    # Make the request and retrieve DOM with BeautifulSoup4
    req = requests.get(urljoin(CS_BASE_ENDPOINT, category))
    if not req.ok:
        return
    dom = bs4.BeautifulSoup(req.content, features="html5lib")
    people_divs = dom.find_all(name="div", attrs={ "class": "person" })
    
    
    people = []
    
    # Process each record individual and parse out data
    for p in people_divs:
        record = {}
        
        # Extract full name
        fullname_tag = p.find("h2", attrs={"class": "person-name"})
        if fullname_tag.find("a"):
            record["full_name"] = fullname_tag.find("a").text.strip()
        else:
            record["full_name"] = fullname_tag.text.strip()
            
            if fullname_tag.find("small"):
                maintext = fullname_tag.text
                badtext = fullname_tag.find("small").text
                record["full_name"] = maintext.replace(badtext, "").strip()

        # Process other standard directory information
        record["title"] = p.find("div", attrs={"class": "person-title"}).text.strip()
        
        degree_tag = p.find("div", attrs={"class": "person-degree"})
        if degree_tag:
            record["degree"] = degree_tag.text.strip()
        
        # Process image
        photo_imgtag = p.find("div", attrs={"class": "person-photo"}).find("img")
        if photo_imgtag and photo_imgtag.has_attr("src"):
            photo_rel_url = photo_imgtag.get("src", None)
            if photo_rel_url:
                record["photo_link"] = urljoin(CS_BASE_ENDPOINT, photo_rel_url)
        
        # Process email / CS NetID
        raw_address_items = p.find_all("span", attrs={"class": "person-address-item"})
        
        for item in raw_address_items:
            if item == None or not item.find("span", "glyphicon"):
                continue
            
            item_type = list(filter(lambda s: "glyphicon-" in s,
                                    item.find("span", "glyphicon").get("class", [])))
            
            text = item.text.strip()
            
            # Email
            if "glyphicon-envelope" in item_type:
                username = re.sub(r'\W+', '', text.split("@")[0])
                domain = text.split("@")[1].strip().strip(')')
                record["email"] = "{}@{}".format(username, domain)
                record["net_id"] = username
            
            # Phone
            if "glyphicon-earphone" in item_type:
                record["phone"] = text
            
            # Address
            if "glyphicon-briefcase" in item_type:
                record["address"] = text
        
        # Add to processed records
        people.append(record)
    
    return people

def loadfeeds():
    all_people = {}
    for category in CATEGORIES:
        people = loadfeed(category=category)
        for record in people:
            all_people[record["net_id"]] = record
    return all_people
