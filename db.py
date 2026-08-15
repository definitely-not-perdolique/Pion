import sqlite3
from utilities import *

class ImageboardDB:
    def __init__(self, dbname):
        self.dbname = dbname

    def __enter__(self):
        self.con = sqlite3.connect(self.dbname)
        self.cur = self.con.cursor()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.commit()
        self.con.close()

    @staticmethod
    def create_table_query(metadata):
        return f'''
        CREATE TABLE {metadata.table_name}(
            {string_of_typed_fields(metadata.dbfields() + metadata.data_fields())}
            {"," if len(metadata.constraints) > 0 else ""}
            {",".join(metadata.constraints)}
        );
        '''

    @staticmethod
    def select_query(metadata, where = ""):
        query = f'''
        SELECT
            rowid,
            {string_of_fields(metadata.dbfields() + metadata.data_fields())}
        FROM
            {metadata.table_name}
        '''

        if(where != ""):
            query += f'''
            WHERE
                {where}
            '''

        return query
    
    @staticmethod
    def insert_query(metadata):
        return f'''
            INSERT INTO {metadata.table_name} VALUES ({values_placeholder(len(metadata.dbfields()) + len(metadata.data_fields()))})
        '''

    @staticmethod
    def update_query(metadata, set, where):
        return f'''
            UPDATE {metadata.table_name} SET {set} WHERE {where}
        '''

    def begin_transaction(self):
        self.cur.execute("BEGIN TRANSACTION")

    def commit(self):
        self.con.commit()

    def find_board(self, board_id):
        self.cur.execute(ImageboardDB.select_query(DBBoard.metadata(), where = 'id = ?'), (board_id, ))

        fetchedrow = self.cur.fetchone()

        if fetchedrow is None: 
            return None
        else:
            return DBBoard.from_tuple(self, fetchedrow)

    def find_post(self, board_id, postnum):
        self.cur.execute(ImageboardDB.select_query(DBPost.metadata(), where="board_id = ? AND num = ?"), (board_id, postnum))

        fetchedrow = self.cur.fetchone()

        if fetchedrow is None:
            return None
        else:
            return DBPost.from_tuple(self, fetchedrow)

    def find_all_posts(self, board_id):
        self.cur.execute(ImageboardDB.select_query(DBPost.metadata(), where="board_id = ?"), (board_id,))

        fetched = self.cur.fetchall()
        return list(map(lambda x: DBPost.from_tuple(self, x), fetched))

    def find_all_files(self, board_id):
            self.cur.execute(ImageboardDB.select_query(DBFile.metadata()))
            fetched = self.cur.fetchall()
            return list(map(lambda x: DBFile.from_tuple(self, x), fetched))

    def find_posts_with_parent(self, board_id, parent_id):
        self.cur.execute(ImageboardDB.select_query(DBPost.metadata(), where="board_id = ? AND parent_id = ?"), (board_id, parent_id))

        fetched = self.cur.fetchall()

        return list(map(lambda x: DBPost.from_tuple(self, x), fetched))

    def insert_object(self, DBObjClass, data, **fields):
        db_obj = DBObjClass(self, 0, data, **fields)

        self.cur.execute(ImageboardDB.insert_query(DBObjClass.metadata()), db_obj.to_tuple())

        db_obj.id = self.cur.lastrowid

        return db_obj

    def insert_board(self, board_data):
        return self.insert_object(DBBoard, board_data)

    def insert_post(self, board_id, thread_id, post_data):
        return self.insert_object(DBPost, post_data, parent_id = thread_id, board_id = board_id)

    def insert_thread(self, board_id, post):
        return self.insert_post(board_id, 0, post)

    def update_post(self, post_id, post_data):
        updatesetstring = update_set_placeholder(ImageboardPostData.fields())
        updatequery = ImageboardDB.update_query(DBPost.metadata(), set = updatesetstring, where = "rowid = ?")
        self.cur.execute(updatequery, post_data.to_tuple() + (post_id,))

    def insert_file(self, post_id, file_data):
        return self.insert_object(DBFile, file_data, post_id = post_id)

    def find_last_posts_in_threads(self, board_id):
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

class ImageboardDataBaseClass:
    def __init__(self, data, aliases = {}):
        set_attributes_with_aliases(self, data, aliases)
        
    def to_tuple(self):
        return tuple(getattr(self, f) for (f, _) in self.__class__.fields())

    @classmethod
    def from_tuple(cls, tuple):
        index_to_field = make_index_to_field_table(cls.fields())
        data = { index_to_field(i): val for (i, val) in enumerate(tuple) }
        return cls(data)

    @classmethod
    def fields(cls):
        return cls._datafields

class ImageboardPostData(ImageboardDataBaseClass):
    _datafields = [
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

class ImageboardFileData(ImageboardDataBaseClass):
    _datafields = [
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

class ImageboardBoardData(ImageboardDataBaseClass):
    _datafields = [
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
    
class DBBase:
    def __init__(self, db, id, data, **fields):
        self.db = db
        self.id = id
        self.data = data

        if len(fields) > 0:
            set_fields_from_dictionary(self, fields)

    def to_tuple(self):
        dbfields = self.__class__.metadata().dbfields()
        fields = self.__class__.metadata().data_fields()
    
        return tuple(getattr(self, f[0]) for f in dbfields) + tuple(getattr(self.data, f[0]) for f in fields)
        
    @classmethod
    def from_tuple(cls, db, tuple):
        dbfield_indices = make_index_to_field_table(cls.metadata().dbfields())
        datafield_indices = make_index_to_field_table(cls.metadata().data_fields())
    
        id = tuple[0]
    
        offset = 1
        dbfields = {field: tuple[index + offset] for (index, field) in enumerate(dbfield_indices)}
    
        offset += len(dbfields)
        datafields = {field: tuple[index + offset] for index, field in enumerate(datafield_indices)}
    
        return cls(db, id, cls.metadata().data_class(datafields), **dbfields)

class DBFile(DBBase):
    _fields = [
        ("post_id", "Integer")
    ]

    _constraints = [
        "FOREIGN KEY(post_id) REFERENCES Posts(rowid)",
        "UNIQUE(post_id, md5) ON CONFLICT IGNORE"
    ]

    @classmethod
    def metadata(cls) -> DBMetadata: 
        return DBMetadata("Files", ImageboardFileData, cls._fields, cls._constraints)

class DBBoard(DBBase):
    def metadata() -> DBMetadata:
        return DBMetadata("Boards", ImageboardBoardData)

    def add_thread(self, post_data: ImageboardPostData, files:list[ImageboardFileData] = []):
        thread = self.db.insert_thread(self.id, post_data)

        for f in files:
            thread.add_file(f)

        return thread

    def find_post(self, postnum):
        return self.db.find_post(self.id, postnum)

    def find_last_posts(self):
        return self.db.find_last_posts_in_threads(self.id)

    def find_posts_of_thread(self, thread_id):
        return self.db.find_posts_with_parent(self.id, thread_id)

    def find_all_threads(self):
        return self.db.find_posts_with_parent(self.id, 0)

    def find_all_posts(self):
        return self.db.find_all_posts(self.id)

    def find_all_files(self):
        return self.db.find_all_files(self.id)

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
