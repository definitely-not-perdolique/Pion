import requests
import db
import settings

from utilities import active_sleep

# Я не знаю, что оно делает, писал пьяным.
# Переделывать не буду, разбираться тоже, работает не трожь
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

    # Сосач бля ебаный криво хуйню возвращает
    # ПОЧЕМУ-ТО иногда posts завернут в threads, причём 
    # в этом случае threads это всегда массив с одним элементом
    # почему нельзя было просто засунуть posts напрямую в корень
    # жсона - непонятно
    # абу пидорас ротибаль
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

def get_cold():
    time_to_get_cold = settings.cold_delay

    print(f"{time_to_get_cold} seconds to get cold...")
    active_sleep(time_to_get_cold)
    print("Retry")

def trying_until_ok(query):
    while True:
        try:
            r = requests.get(query)

            if not r.ok:
                if 400 <= r.status_code < 500:
                    return None
                else:
                    get_cold()
            else:
                return r

        except requests.Timeout:
            get_cold()
            

class DvachApi:
    endpoint = "https://2ch.su"

    @staticmethod
    def get_threads(boardname):
        query_path = f"{DvachApi.endpoint}/{boardname}/catalog.json"
        r = trying_until_ok(query_path)
        return parse_posts_from_json(r.json())

    @staticmethod
    def get_posts(boardname, threadnum):
        query_path = f"{DvachApi.endpoint}/{boardname}/res/{threadnum}.json"
        r = trying_until_ok(query_path)
        return parse_posts_from_json(r.json())

    @staticmethod
    def get_board(boardname):
        query_path = f"{DvachApi.endpoint}/api/mobile/v2/boards"
        r = trying_until_ok(query_path)
        return parse_boards_from_json(r.json())[boardname]

    @staticmethod
    def get_posts_after(boardname, threadnum, postnum):
        query_path = f"{DvachApi.endpoint}/api/mobile/v2/after/{boardname}/{threadnum}/{postnum+1}"
        r = trying_until_ok(query_path)
        return parse_after_from_json(r.json())