from pathlib import Path
import asyncio

visualise_path = "visualised"

path_to_root = Path.joinpath(Path.cwd(), visualise_path)
path_to_res = Path.joinpath(path_to_root, "dr", "res")

async def create_root(threads):
    print("Creating root file index.html")
    with open(Path.joinpath(path_to_root, "index.html"), "w", encoding="UTF-8") as index:
        lines = []

        for t in threads:
            threadpath = f"dr/res/{t.data.num}.html"
            lines.append(f"<div><a href=\"{threadpath}\">{t.data.subject}</a></div>")

        index.writelines(lines)

def format_post(p):
    post_data = p.data
    return f"<div id=\"{post_data.num}\">{post_data.num} {post_data.subject} {post_data.comment}</div>"

async def create_thread(thread, posts_dict):
    threadnum = thread.data.num
    print(f"Creating thread {threadnum}")

    posts = posts_dict[thread.id]

    head = f"<!DOCTYPE><html><body>"

    lines_to_write = [head] + [format_post(p) for p in posts] + ["</body></html>"]
    
    with open(Path.joinpath(path_to_res, f"{threadnum}.html"), "w", encoding="UTF-8") as threadfile:
        threadfile.writelines(lines_to_write)

async def create_threads(board, threads):
    all_posts = board.find_all_posts()

    posts_dict = {}

    for t in threads:
        posts_dict[t.id] = [t] 

    for p in all_posts:
        if p.parent_id != 0:
            posts_dict[p.parent_id].append(p)
        
    tasks = []

    for thread in threads:
        tasks.append(asyncio.create_task(create_thread(thread, posts_dict)))

    for t in tasks:
        await t

async def visualise_async(board, threads):
    task1 = asyncio.create_task(create_root(threads))
    task2 = asyncio.create_task(create_threads(board, threads))

    await task1
    await task2

def visualise(board, threads):
    Path.mkdir(path_to_res, parents = True, exist_ok = True)
    asyncio.run(visualise_async(board, threads))