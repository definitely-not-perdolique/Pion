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

    def find_board(self, board_id):
        self.cur.execute(DBBoard.metadata().select_query(where = 'id = ?'), (board_id, ))

        fetchedrow = self.cur.fetchone()

        if fetchedrow is None: 
            return None
        else:
            return DBBoard.from_tuple(self, fetchedrow)

    def find_post(self, board_id, postnum):
        self.cur.execute(DBPost.metadata().select_query(where="board_id = ? AND num = ?"), (board_id, postnum))

        fetchedrow = self.cur.fetchone()

        if fetchedrow is None:
            return None
        else:
            return DBPost.from_tuple(self, fetchedrow)

    def insert_object(self, DBObjClass, data, **fields):
        db_obj = DBObjClass(self, 0, data, **fields)
        self.cur.execute(DBObjClass.metadata().insert_query(), db_obj.to_tuple())
        db_obj.id = self.cur.lastrowid
        return db_obj

    def insert_board(self, board_data: ImageboardBoardData):
        return self.insert_object(DBBoard, board_data)

    def insert_post(self, board_id, thread_id, post_data: ImageboardPostData):
        return self.insert_object(DBPost, post_data, parent_id = thread_id, board_id = board_id)

    def insert_thread(self, board_id, post):
        return self.insert_post(board_id, 0, post)

    def update_post(self, post_id, post_data):
        updatesetstring = ",".join(f"{f} = ?" for (f, _) in ImageboardPostData.fields())
        updatequery = DBPost.metadata().update_query(set = updatesetstring, where = "rowid = ?")
        self.cur.execute(updatequery, post_data.to_tuple() + (post_id,))

    def insert_file(self, post_id, file_data: ImageboardFileData):
        return self.insert_object(DBFile, file_data, post_id = post_id)

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
                AND Threads.closed = 0
                AND Threads.deleted = 0
            GROUP BY
                Threads.num
            ORDER BY
                Threads.num DESC
        ''', (board_id,))

        return self.cur.fetchall()

    def create_db(self):
        self.cur.execute(DBPost.metadata().create_table_query())
        self.cur.execute(DBFile.metadata().create_table_query())
        self.cur.execute(DBBoard.metadata().create_table_query())

        self.cur.execute("PRAGMA foreign_keys=ON")

# :P
def values_placeholder(count):
    return ",".join("?" for i in range(count))

def update_string(fields):
    return ",".join(f for f in fields)

def string_of_fields(fields):
    return ",".join(f"{x}" for (x, _) in fields)

def string_of_typed_fields(fields):
    return ",".join(f"{x} {y}" for (x, y) in fields)

def set_attributes_with_aliases(self, data, aliases):
    for (f,_) in self.__class__.fields():
        name = aliases[f] if f in aliases else f

        setattr(self, f, data.get(name, 0))

def set_fields_from_dictionary(self, fields):
    for (field, value) in fields.items():
        setattr(self, field, value)

def data_class_to_tuple(self):
    tuple = ()

    for (f,_) in self.__class__.fields():
        tuple += (getattr(self, f),)

    return tuple

def tuple_to_data_class(tuple, Self):
    index_to_field = Self.index_to_field

    data = {}

    for i in range(len(tuple)):
        data[index_to_field[i]] = tuple[i]

    return Self(data)

def make_index_to_field_table(fields):
    result = []

    for (key, _) in fields:
        result.append(key)

    return result

def db_object_from_tuple(Self, db, tuple):
    dbfield_indices = make_index_to_field_table(Self.metadata().dbfields())
    datafield_indices = make_index_to_field_table(Self.metadata().data_fields())

    id = tuple[0]

    offset = 1
    dbfields = {field: tuple[index + offset] for (index, field) in enumerate(dbfield_indices)}

    offset += len(dbfields)
    datafields = {field: tuple[index + offset] for index, field in enumerate(datafield_indices)}

    return Self(db, id, Self.metadata().data_class(datafields), **dbfields)

def db_object_to_tuple(self):
    dbfields = self.__class__.metadata().dbfields()
    fields = self.__class__.metadata().data_fields()

    return tuple(getattr(self, f[0]) for f in dbfields) + tuple(getattr(self.data, f[0]) for f in fields)

class ImageboardPostData:
    datafields = [
        ("comment", "Text"),
        ("timestamp", "Integer"),
        ("email", "Text"),
        ("name", "Text"),
        ("num", "Integer"),
        ("subject", "Text"),
        ("trip", "Text"),
        ("views", "Integer"),
        ("number", "Integer"),
        ("closed", "Integer"),
        ("deleted", "Integer"),
        ("lasthit", "Integer")
    ]

    def fields():
        return __class__.datafields

    def __init__(self, data, aliases = {}):
        set_attributes_with_aliases(self, data, aliases)

    def to_tuple(self):
        return data_class_to_tuple(self)

    def from_tuple(tuple):
        return tuple_to_data_class(tuple, __class__)

class ImageboardFileData:
    datafields = [
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

    def fields():
        return __class__.datafields

    def __init__(self, data, aliases = {}):
        set_attributes_with_aliases(self, data, aliases)

    def to_tuple(self):
        return data_class_to_tuple(self)

    def from_tuple(tuple):
        return tuple_to_data_class(tuple, ImageboardFileData)

class ImageboardBoardData:
    datafields = [
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

    def fields():
        return __class__.datafields

    def __init__(self, data, aliases = {}):
        set_attributes_with_aliases(self, data, aliases)

    def to_tuple(self):
        return data_class_to_tuple(self)

    def from_tuple(tuple):
        return tuple_to_data_class(tuple, __class__)

class DBMetadata:
    def __init__(self, table_name, data_class, fields = [], constraints = []):
        self.table_name = table_name
        self.data_class = data_class
        self.fields = fields
        self.constraints = constraints

    def dbfields(self):
        return self.fields

    def data_fields(self):
        return self.data_class.fields()

    def create_table_query(self):
        return f'''
        CREATE TABLE {self.table_name}(
            {string_of_typed_fields(self.fields + self.data_class.fields())}
            {"," if len(self.constraints) > 0 else ""}
            {",".join(self.constraints)}
        );
        '''

    def select_query(self, where = ""):
        return f'''
        SELECT
            rowid,
            {string_of_fields(self.fields + self.data_class.fields())}
        FROM
            {self.table_name}
        WHERE
            {where}
        '''

    def insert_query(self):
        return f'''
            INSERT INTO {self.table_name} VALUES ({values_placeholder(len(self.fields) + len(self.data_class.fields()))})
        '''

    def update_query(self, set, where):
        return f'''
            UPDATE {self.table_name} SET {set} WHERE {where}
        '''
    
class DBBase:
    def __init__(self, db, id, data, **fields):
        self.db = db
        self.id = id
        self.data = data

        if len(fields) > 0:
            set_fields_from_dictionary(self, fields)

    def to_tuple(self):
        return db_object_to_tuple(self)

class DBFile(DBBase):
    fields = [
        ("post_id", "Integer")
    ]

    constraints = [
        "FOREIGN KEY(post_id) REFERENCES Posts(rowid)",
        "UNIQUE(post_id, md5) ON CONFLICT IGNORE"
    ]

    def metadata() -> DBMetadata: 
        return DBMetadata("Files", ImageboardFileData, __class__.fields, __class__.constraints)

    def from_tuple(db, tuple):
            return db_object_from_tuple(__class__, db, tuple)

class DBBoard(DBBase):
    def metadata() -> DBMetadata:
        return DBMetadata("Boards", ImageboardBoardData)

    def from_tuple(db, tuple):
            return db_object_from_tuple(__class__, db, tuple)

    def add_thread(self, post_data: ImageboardPostData, files:list[ImageboardFileData] = []):
        thread = self.db.insert_thread(self.id, post_data)

        for f in files:
            thread.add_file(f)

        return thread

    def find_post(self, postnum):
        return self.db.find_post(self.id, postnum)

    def find_last_posts(self):
        return self.db.last_posts_in_threads(self.id)

class DBPost(DBBase):
    fields = [
        ("parent_id", "Integer"), 
        ("board_id", "Integer")
    ]

    constraints = [
        "FOREIGN KEY(board_id) REFERENCES Boards(rowid)",
        "UNIQUE(board_id, num) ON CONFLICT IGNORE"
    ]

    def metadata() -> DBMetadata:
        return DBMetadata("Posts", ImageboardPostData, __class__.fields, __class__.constraints)

    def from_tuple(db, tuple):
        return db_object_from_tuple(__class__, db, tuple)

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
        self.db.update_post(self.id, self.data)
