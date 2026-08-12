import sys
import pathlib

from dvachapi import DvachApi
from db import ImageboardDB

def createdb(dbname):
    if pathlib.Path.exists(dbname):
        raise Exception(f"File {dbname} already exists. Remove file and try again")

    with ImageboardDB(dbname) as imdb:
        imdb.create_db()

def preload(dbname):
    boardname = "dr"

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

        print("Loading threads... ")
        threads = api_instance.get_threads(boardname)

        threads_to_commit = 10
        counter = 0

        for (thread, files) in threads.items():
            if counter >= 10:
                imdb.commit()
                counter = 0

            threadnum = thread.num

            if board.find_post(threadnum) is not None:
                print(f"Thread {threadnum} found, skip")
                continue

            thread = board.add_thread(thread, files)

            print(f"Loading posts for thread {threadnum}")
            posts = api_instance.get_posts(boardname, threadnum)

            for (post, post_files) in posts.items():
                thread.add_post(post, post_files)

            counter += 1

def updating(dbname):
    preload(dbname)

    boardname = "dr"

    api_instance = DvachApi()

    with ImageboardDB(dbname) as imdb:
        board = imdb.find_board(boardname)
            
        if board is None:
            print(f"Board {boardname} not found")
            exit(1)

        l = board.find_last_posts()

        lenl = len(l)

        posts_to_commit = 10
        counter = 1

        for (tnum, pnum) in l:
            if counter % 10 == 0:
                imdb.commit()

            thread = board.find_post(tnum)

            posts = api_instance.get_posts_after(boardname, tnum, pnum)

            if len(posts) > 0:
                print(f"In thread {tnum} found {len(posts)} new posts (last is {pnum})!")

            for (post, files) in posts.items():
                thread.add_post(post, files)

            counter += 1

            print(f"[{counter}/{lenl}]")


def main():
    args = sys.argv

    if len(args) != 3 or args[1] not in ["createdb", "preload", "updating"]:
        print(f'''
            Usage: {args[0]} <command> <dbname>

            where <command> in [ createdb, preload, updating ]  
        ''')

        return

    command = args[1]

    if command == "createdb":
        createdb(args[2])
    elif command == "preload":
        preload(args[2])
    elif command == "updating":
        updating(args[2])

if __name__ == "__main__":
    main()