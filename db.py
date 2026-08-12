import sqlite3

class ImageboardDB:
    def __init__(self, dbname):
        self.dbname = dbname
        self.con = None

    def __enter__(self):
        self.con = sqlite3.connect(self.dbname)
        self.cur = self.con.cursor()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.commit()
        self.con.close()

    def begin_transaction(self):
        self.cur.execute("BEGIN TRANSACTION")

    def commit(self):
        self.con.commit()

    def insert_board(self, board_data: ImageboardBoardData):
        data_to_add = board_data.to_tuple()

        self.cur.execute(f'''
            INSERT INTO Boards VALUES({values_placeholder(len(data_to_add))})
        ''', data_to_add)

        return DBBoard(self, self.cur.lastrowid, board_data)

    def find_board(self, boardid):
        self.cur.execute(f'''
            SELECT 
                rowid, 
                {get_sorted_string_of_fields(ImageboardBoardData)}
            FROM Boards 
            WHERE id=?
        ''', (boardid,))

        fetchedrow = self.cur.fetchone()

        if fetchedrow is None: 
            return None
        else:
            return DBBoard(self, fetchedrow[0], ImageboardBoardData.from_tuple(fetchedrow[1:]))

    def insert_post(self, board_id, thread_id, post_data: ImageboardPostData):
        data_to_add = (thread_id, board_id) + post_data.to_tuple()

        self.cur.execute(f'''
            INSERT INTO Posts
            VALUES({values_placeholder(len(data_to_add))});
        ''', data_to_add)

        return DBPost(self, self.cur.lastrowid, thread_id, board_id, post_data)

    def insert_thread(self, board_id, post):
        return self.insert_post(board_id, 0, post)

    def update_post(self, post_id, post_data):
        updatestring = ",".join(f"{f} = ?" for f in ImageboardPostData.sorted_fields)

        self.cur.execute(f'''
            UPDATE Posts 
            WHERE rowid = ? 
            SET {updatestring}
        ''', post_id, post_data.to_tuple())

    def find_post(self, board_id, postnum):
        self.cur.execute(f'''
            SELECT
                rowid,
                parent_id,
                board_id,
                {get_sorted_string_of_fields(ImageboardPostData)}
            FROM Posts 
            WHERE board_id = ? and num = ?
        ''', (board_id, postnum))

        fetchedrow = self.cur.fetchone()

        if fetchedrow is None:
            return None
        else:
            return DBPost(
                    self,
                    fetchedrow[0],
                    fetchedrow[1],
                    fetchedrow[2],
                    ImageboardPostData.from_tuple(fetchedrow[3:]))

    def insert_file(self, post_id, file_data: ImageboardFileData):
        data_to_add = (post_id,) + file_data.to_tuple()
        self.cur.execute(f'''
            INSERT INTO Files
            VALUES({values_placeholder(len(data_to_add))});
        ''', data_to_add)
        return DBFile(self, self.cur.lastrowid, file_data)

    def last_posts_in_threads(self, board_id):
        self.cur.execute('''
            SELECT
                Threads.num AS ThreadNum,
                MAX(Posts.num) AS PostNum
            FROM
                Posts AS Posts
                INNER JOIN Posts AS Threads
                ON Threads.rowid = Posts.parent_id
            WHERE
                Posts.board_id = ?
                AND Posts.parent_id <> 0
            GROUP BY
                Threads.num
            ORDER BY
                Threads.num DESC
        ''', (board_id,))

        return self.cur.fetchall()

    def create_db(self):
        self.cur.execute(f"CREATE TABLE Boards({get_sorted_string_of_typed_fields(ImageboardBoardData)})")

        self.cur.execute(f'''
            CREATE TABLE Posts(
                parent_id Integer,
                board_id Integer,
                {get_sorted_string_of_typed_fields(ImageboardPostData)},
                FOREIGN KEY(board_id) REFERENCES Boards(rowid),
                UNIQUE(board_id, num) ON CONFLICT IGNORE
            );
        ''')

        self.cur.execute(f'''
            CREATE TABLE Files(
                post_id Integer,
                {get_sorted_string_of_typed_fields(ImageboardFileData)},
                FOREIGN KEY(post_id) REFERENCES Posts(rowid)
            );
        ''')

        self.cur.execute("PRAGMA foreign_keys=ON")

# :P
def values_placeholder(count):
    return ",".join("?" for i in range(count))

def get_sorted_string_of_fields(Self):
    return ",".join(f"{x}" for (x, _) in Self.sorted_fields)

def get_sorted_string_of_typed_fields(Self):
    return ",".join(f"{x} {y}" for (x, y) in Self.sorted_fields)

def set_attributes_with_aliases(self, Self, data, aliases):
    for (f,_) in Self.sorted_fields:
        name = aliases[f] if f in aliases else f

        setattr(self, f, data.get(name, 0))

def data_class_to_tuple(self, Self):
    tuple = ()

    for (f,_) in Self.sorted_fields:
        tuple += (getattr(self, f),)

    return tuple

def tuple_to_data_class(tuple, Self):
    index_to_field = Self.index_to_field

    data = {}

    for i in range(len(tuple)):
        data[index_to_field[i]] = tuple[i]

    return Self(data)
    
def make_index_to_field(sorted_fields):
    result = []

    for (key, _) in sorted_fields:
        result.append(key)

    return result


class ImageboardPostData:
    sorted_fields = [
        ("comment", "Text"),
        ("timestamp", "Integer"),
        ("email", "Text"),
        ("name", "Text"),
        ("num", "Integer"),
        ("subject", "Text"),
        ("trip", "Text"),
        ("views", "Integer"),
        ("number", "Integer"),
        #("closed", "Integer"),
        #("deleted", "Integer")
    ]

    index_to_field = make_index_to_field(sorted_fields)

    def __init__(self, data, aliases = {}):
        set_attributes_with_aliases(self, ImageboardPostData, data, aliases = {})

    def to_tuple(self):
        return data_class_to_tuple(self, ImageboardPostData)

    def from_tuple(tuple):
        return tuple_to_data_class(tuple, ImageboardPostData)

class ImageboardFileData:
    sorted_fields = [
        ("md5", "Text"),
        ("path", "Text"),
        ("displayname", "Text"),
        ("fullname", "Text"),
        ("height", "Integer"),
        ("size", "Integer"),
        ("thumbnail", "Text"),
        ("tn_height", "Integer"),
        ("tn_width", "Integer"),
        ("type", "Integer"),
        ("width", "Integer")
    ]

    index_to_field = make_index_to_field(sorted_fields)

    def __init__(self, data, aliases = {}):
        set_attributes_with_aliases(self, ImageboardFileData, data, aliases)

    def to_tuple(self):
        return data_class_to_tuple(self, ImageboardFileData)

    def from_tuple(tuple):
        return tuple_to_data_class(tuple, ImageboardFileData)

class ImageboardBoardData:
    sorted_fields = [
        ("id", "Text"),
        ("name", "Text"),
        ("bump_limit", "Integer"),
        ("info", "Text"),
        ("info_outer", "Text"),
        ("max_comment", "Integer"),
        ("max_files_size", "Integer"),
        ("max_pages", "Integer"),
        ("threads_per_page", "Integer")
    ]

    index_to_field = make_index_to_field(sorted_fields)

    def __init__(self, data, aliases = {}):
        set_attributes_with_aliases(self, ImageboardBoardData, data, aliases)

    def to_tuple(self):
        return data_class_to_tuple(self, ImageboardBoardData)

    def from_tuple(tuple):
            return tuple_to_data_class(tuple, ImageboardBoardData)

class DBFile:
    def __init__(self, db, id, file_data):
        self.db = db
        self.id = id
        self.file_data = file_data

class DBBoard:
    def __init__(self, db: ImageboardDB, id: int, board_data: ImageboardBoardData):
        self.db = db
        self.id = id
        self.board_data = board_data

    def add_thread(self, post_data:ImageboardPostData, files:list[ImageboardFileData] = []):
        thread = self.db.insert_thread(self.id, post_data)

        for f in files:
            thread.add_file(f)

        return thread

    def get_threads(self):
        return self.db.get_threads(self.id)

    def find_post(self, threadnum):
        return self.db.find_post(self.id, threadnum)

    def find_last_posts(self):
        return self.db.last_posts_in_threads(self.id)

class DBPost:
    def __init__(self, db: ImageboardDB, id: int, parent_id: int, board_id: int, post_data: ImageboardPostData):
        self.db = db
        self.id = id
        self.post_data = post_data
        self.parent_id = parent_id
        self.board_id = board_id

    def add_post(self, post_data: ImageboardPostData, files:list[ImageboardFileData] = []):
        if self.parent_id != 0:
            raise Exception("Tryna add post to post that is not thread")
        
        post = self.db.insert_post(self.board_id, self.id, post_data)

        for f in files:
            post.add_file(f)

        return post

    def add_file(self, file_data):
        return self.db.insert_file(self.id, file_data)

    def update_data(self):
        self.db.update_post(self.id, self.post_data)