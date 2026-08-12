import requests
import db
import time

def add_item_to_dictionary(dictionary, element):
    ibpostdata = db.ImageboardPostData(element)

    files = []

    if "files" in element and element["files"] is not None:
        for f in element["files"]:
            files.append(db.ImageboardFileData(f))

    dictionary[ibpostdata] = files


def parse_posts_from_json(json):
    if "threads" not in json:
        return {}

    d = {}

    for element in json["threads"]:
        if "posts" in element:
            for post in element["posts"]:
                add_item_to_dictionary(d, post)
        else:
            add_item_to_dictionary(d, element)

    return d

def parse_after_from_json(json):
    d = {}
    
    for post in json["posts"]:
        add_item_to_dictionary(d, post)

    return d

def parse_boards_from_json(json):
    d = {}

    for element in json:
        d[element["id"]] = db.ImageboardBoardData(element)

    return d

def trying_until_ok(query):
    while True:
        try:
            r = requests.get(query, timeout = 5)

            if not r.ok:
                if 400 <= r.status_code < 500:
                    raise Exception("Косяк в запросе")

                print("10 seconds to get cold...")
                time.sleep(10)
                print("Retry")
            else:
                return r
        except requests.ReadTimeout:
            print("10 seconds to get cold...")
            time.sleep(10)
            print("Retry")
            

class DvachApi:
    endpoint = "https://2ch.su"

    def get_threads(_, boardname):
        query_path = f"{DvachApi.endpoint}/{boardname}/catalog.json"
        r = trying_until_ok(query_path)
        return parse_posts_from_json(r.json())

    def get_posts(_, boardname, threadnum):
        query_path = f"{DvachApi.endpoint}/{boardname}/res/{threadnum}.json"
        r = trying_until_ok(query_path)
        return parse_posts_from_json(r.json())

    def get_board(_, boardname):
        query_path = f"{DvachApi.endpoint}/api/mobile/v2/boards"
        r = trying_until_ok(query_path)
        return parse_boards_from_json(r.json())[boardname]

    def get_posts_after(_, boardname, threadnum, postnum):
        query_path = f"{DvachApi.endpoint}/api/mobile/v2/after/{boardname}/{threadnum}/{postnum+1}"
        r = trying_until_ok(query_path)
        return parse_after_from_json(r.json())