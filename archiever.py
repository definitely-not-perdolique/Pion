import sys
import pathlib

from dvachapi import DvachApi
from db import ImageboardDB
import visualiser

from utilities import active_sleep

import settings

def createdb(dbname):
    if pathlib.Path.exists(dbname):
        raise Exception(f"File {dbname} already exists. Remove file and try again")

    with ImageboardDB(dbname) as imdb:
        imdb.create_db()

def load_posts_after(api, thread, boardname, tnum, pnum):
    posts = api.get_posts_after(boardname, tnum, pnum)

    if posts is None:
        return None

    if len(posts) > 0:
        print(f"In thread {tnum} found {len(posts)} new posts (last is {pnum})!")

    for (post, files) in posts.items():
        thread.add_post(post, files)

    return len(posts)

def visualise(dbname):
    with ImageboardDB(dbname) as imdb:
        board = imdb.find_board(settings.board_to_archive)
        visualiser.visualise(board, board.find_all_threads())

def checknone(val):
    if val is None:
        print("Something went wrong :c")

    return val is None

def updating(dbname):

    boardname = settings.board_to_archive
    update_delay = settings.update_delay

    api_instance = DvachApi()

    board_data = api_instance.get_board(boardname)

    with ImageboardDB(dbname) as imdb:
        print("Tryna found board")
        board = imdb.find_board(boardname)

        if board is None:
            print(f"Not found, creating board {boardname}")
            board = imdb.insert_board(board_data)
        else:
            print("Found!")

        while True:
            print("Loading threads... ")

            all_threads = api_instance.get_threads(boardname)

            updated_threads = []

            # Блять ну, вот, что-то, сука, не так пошло, и запрос вернул None
            # забиваем пробуем ещё раз через 2 минуты, или сколько там в настройках задано
            # это вообще тупость какая-то проверять это каждый раз, но я чёт лучше не придумал
            # и исключения мне ловить не особо хочется
            if checknone(all_threads): continue

            lastposts = {tnum: pnum for tnum, pnum in board.find_last_posts()}

            for (thread, files) in all_threads.items():
                threadnum = thread.num

                foundthread = board.find_post(threadnum)

                if foundthread is not None:
                    if thread.lasthit != foundthread.data.lasthit:
                        print(f"Thread {threadnum} found, loading new posts")
                        posts_loaded = load_posts_after(api_instance, foundthread, boardname, threadnum, lastposts.get(threadnum, threadnum))

                        if checknone(posts_loaded): continue

                        print(f"\t{posts_loaded} posts loaded, updating thread in db")
                        imdb.update_post(foundthread.id, thread)

                        updated_threads.append(thread)
                else:
                    new_thread = board.add_thread(thread, files)

                    print(f"New thread {threadnum} found! Loading posts...")
                    posts = api_instance.get_posts(boardname, threadnum)

                    if checknone(posts): continue

                    for (post, post_files) in posts.items():
                        new_thread.add_post(post, post_files)

                    updated_threads.append(new_thread)

                imdb.commit()

            if len(updated_threads) > 0:
                visualiser.visualise(board, updated_threads)

            print("Done!")
            print()

            print(f"Waiting for {update_delay} seconds...")
            print()

            active_sleep(update_delay)

def main():
    args = sys.argv

    if len(args) != 3 or args[1] not in ["createdb", "updating", "visualise"]:
        print(f'''
            Usage: {args[0]} <command> <dbname>

            where <command> in [ createdb, updating, visualise ]  
        ''')

        return

    command = args[1]
    dbpath = args[2]

    if command == "createdb":
        createdb(dbpath)
    elif command == "updating":
        updating(dbpath)
    elif command == "visualise":
        visualise(dbpath)

if __name__ == "__main__":
    main()