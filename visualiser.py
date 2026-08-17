from pathlib import Path
import asyncio
import datetime
import settings

visualise_path = "visualised"

path_to_root = Path.joinpath(Path.cwd(), visualise_path)
path_to_res = Path.joinpath(path_to_root, "dr", "res")

def quote(s):
    return f"\"{s}\""

def join_attributes(attrs: dict):
    # Костыль бля ебаный, class нельзя в питоне 
    # использовать, поэтому вместо него cls
    if "cls" in attrs:
        attrs["class"] = attrs.pop("cls")
        
    return " ".join(f"{attr}={quote(val)}" for (attr, val) in attrs.items())

def empty(): pass

# Не знаю, я лучше не придумал
def is_lambda(item):
    return type(item) == type(empty)

def call_if_lambda(body_item):
    return str(body_item() if is_lambda(body_item) else body_item);

def join_body_items(body_items):
    # короче, прикол в том, что в body_items 
    # не всегда строки, там, бля, может быть лямбда
    return "".join(map(call_if_lambda, body_items))

def tag_implementation(tag_name, attrs, body_items):
    return f"<{tag_name} {join_attributes(attrs)}>" + (f"{join_body_items(body_items)}</{tag_name}>" if len(body_items) > 0 else "")
    
def tag(tag_name, attrs = {}):
    return lambda *body_items: tag_implementation(tag_name, attrs, body_items)

def div(**attrs):
    return tag("div", attrs)

def a(**attrs):
    return tag("a", attrs)

def img(**attrs):
    return tag("img", attrs)

def doctype():
    return tag("!DOCTYPE")()

def html():
    return tag("html")

def link(**attrs):
    return tag("link", attrs)

def head():
    return tag("head")

def body():
    return tag("body")

def span(**attrs):
    return tag("span", attrs)

def create_root(threads):
    print("Creating root file index.html")
    with open(Path.joinpath(path_to_root, "index.html"), "w", encoding="UTF-8") as index:
        lines = []

        for t in threads:
            threadpath = f"dr/res/{t.data.num}.html"
            lines.append(f"<div><a href=\"{threadpath}\">{t.data.subject}</a></div>")

        index.writelines(lines)

def post_body_without_files(post_data):
    return div(cls = "post_body")(
        div(cls = "post_text_containment")(
            div(cls = "post_subject")(post_data.subject),
            div(cls = "post_comment")(post_data.comment)
        )
    )

def generate_image(file_data):
    return div(cls = "post_image") (
        a(href = f"{settings.api_endpoint}/{file_data.path}")(
            img(loading = "lazy", src = f"{settings.api_endpoint}/{file_data.thumbnail}")
        )
    )

def post_body_with_one_file(post_data, file):
    return div(cls = "post_body one_file")(
        div(cls = "one_image")(
            generate_image(file.data)
        ),
        div(cls = "post_text_containment")(
            div(cls = "post_subject")(post_data.subject),
            div(cls = "post_comment")(post_data.comment)
        )
    )

def post_body_with_many_files(post_data, files):

    images = (generate_image(f.data) for f in files)

    return div(cls = "post_body many_files")(
        div(cls = "many_images")(
            *images
        ),
        div(cls = "post_text_containment")(
            div(cls = "post_subject")(post_data.subject),
            div(cls = "post_comment")(post_data.comment)
        )
    )

def format_post(p, files_dict):
    post_data = p.data
    files = files_dict.get(p.id)

    if files is None:
        post_body = post_body_without_files(post_data)
    elif len(files) == 1:
        post_body = post_body_with_one_file(post_data, files[0])
    else:
        post_body = post_body_with_many_files(post_data, files)

    return div(id = post_data.num, cls = "post")(
                div(cls = "post_header")(
                    span(cls = "post_header_element")(post_data.name),
                    span(cls = "post_header_element")(post_data.trip),
                    span(cls = "post_header_element")(datetime.datetime.fromtimestamp(post_data.timestamp)),
                    span(cls = "post_header_element")(f"№{post_data.num}"),
                    span(cls = "post_header_element")(post_data.number)
                ),
                post_body
            )

def posts_css():
    return '''
    body {
        background-color: #ededed;
        font-family: sans-serif;
        line-height: 1.3;
    }

    a {
        color: red;
        text-decoration: none;
    }

    .post {
        background-color: #dcdcdc;
        border-radius: 0.4em;
        border: 1px solid #d8d8d8;
        width: fit-content;
        max-width: 60vw;
        padding: 5px 10px;
        color: #333;
        margin: 5px;
        word-wrap: break-word;
    }

    .post_header {
        color: #5d5d5d;
    }

    .post_image {
        display: inline-block;
        border: 1px dotted #333;
        margin: 0px 2px;
    }

    .post_image img {
        max-width: 100%;
        vertical-align: top;
    }

    .post_body {
        margin: 10px;
    }

    .post_body.one_file {
        display: grid;
        grid-template-columns: 200px 1fr; 
    }

    .one_image {
        max-width: 100%;
        height: fit-content; 
    }

    .many_images {
        width: fit-content;
        max-height: 100%; 
    }

    .post_text_containment {
        margin: 10px;
    }

    .post_header_element {
        margin-right: 0.4em
    }

    '''

def create_css_file():
    with open(Path.joinpath(path_to_res, "post.css"), "w", encoding="utf-8") as cssfile:
        cssfile.write(posts_css())
        
def create_thread(thread, posts_dict, files_dict):
    threadnum = thread.data.num
    print(f"Creating thread {threadnum}")

    posts = posts_dict[thread.id]

    posts_string = "".join(format_post(p, files_dict) for p in posts)

    document = doctype() + html()(
        head()(
            link(rel = "stylesheet", href = "post.css")
        ),
        body()(
            posts_string
        )
    )
    
    with open(Path.joinpath(path_to_res, f"{threadnum}.html"), "w", encoding="UTF-8") as threadfile:
        threadfile.write(document)

def create_threads(board, threads):

    all_posts = board.find_all_posts()
    all_files = board.find_all_files()

    posts_dict = {}

    for t in threads:
        posts_dict[t.id] = [t] 

    for p in all_posts:
        if p.parent_id != 0:
            posts_dict.setdefault(p.parent_id, []).append(p)

    files_dict = {}
    for f in all_files:
        list = files_dict.setdefault(f.post_id, [])
        list.append(f)

    for thread in threads:
        create_thread(thread, posts_dict, files_dict)

def visualise(board, threads):
    Path.mkdir(path_to_res, parents = True, exist_ok = True)

    create_root(threads)
    create_threads(board, threads)
    create_css_file()