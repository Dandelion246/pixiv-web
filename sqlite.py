import sqlite3
import time
import utils

db_name = '/Users/mac/Desktop/pixiv/pixiv.db'
conn = sqlite3.connect(db_name, check_same_thread=False)
# conn = sqlite3.connect(src.config.get('Settings', 'db_path'))


# def trace_callback(statement):
#     print(f'Executing SQL: {statement}')
#
#
# conn.set_trace_callback(trace_callback)


def create_table():
    cursor = conn.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS pixiv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pixiv_id INTEGER NOT NULL DEFAULT 0,
            name TEXT NOT NULL,
            author TEXT NOT NULL,
            author_id INTEGER NOT NULL DEFAULT 0,
            type TEXT NOT NULL DEFAULT illust,
            path TEXT NOT NULL,
            created_time DATE
        );
        
        CREATE TABLE error (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          url TEXT NOT NULL,
          save_path TEXT NOT NULL DEFAULT '',
          count INTEGER NOT NULL DEFAULT 0,
          error TEXT NOT NULL DEFAULT '',
          res TEXT NOT NULL DEFAULT '',
          created_time DATE
        );
    ''')
    conn.commit()


def insert_error_data(url, save_path, err):
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO error (url, save_path, count, error, res, created_time) VALUES (?, ?, ?, ?, ?, ?)',
        (url,
         save_path,
         0,
         err,
         'error',
         time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())))
    conn.commit()


def insert_data(pixiv_id, name, author, author_id, t, path):
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO pixiv (pixiv_id, name, author, author_id, type, path, created_time) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (pixiv_id, name, author, author_id, t, path,
         time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())))
    conn.commit()


def query_all_pixiv():
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pixiv')
    rows = cursor.fetchall()
    return rows


def query_all_errors():
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM error')
    rows = cursor.fetchall()
    return rows


def pixiv_id_exists(pixiv_id):
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM pixiv WHERE pixiv_id = ?', (pixiv_id,))
    return cursor.fetchone() is not None


def work_exists(pixiv_id, title: str = ''):
    cursor = conn.cursor()

    sql = 'SELECT count(*) FROM pixiv WHERE pixiv_id = ?'
    params = (pixiv_id,)

    if title:
        title = title.replace('%', '%%')
        sql += ' OR name LIKE ?'
        params = (pixiv_id, f'%{title}%')

    cursor.execute(sql, params)
    return bool(cursor.fetchone()[0])


def delete_by_id(id):
    cursor = conn.cursor()
    cursor.execute('DELETE FROM pixiv WHERE id = ?', (id,))
    conn.commit()


def get_error_count():
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM error;')
    conn.commit()
    row_count = cursor.fetchone()[0]
    cursor.close()
    return row_count


def delete_error_by_id(id):
    cursor = conn.cursor()
    cursor.execute('DELETE FROM error WHERE id = ?', (id,))
    conn.commit()


# 示例使用
if __name__ == "__main__":
    try:
        # errors = query_all_errors()
        count = get_error_count()
        print(count)
        # print(work_exists('22222', '(C101) [八百萬堂 (AkiFn)] 誰も知らない夜 (オリジナル)'))
        # print(work_exists('110123836'))
        # 创建表
        # create_table()
        # work_exists('99677275', "ina99677275")
        #
        # # 插入数据
        # insert_data(227727, 'test', 'a1', 1, '', '')
        # insert_data(292999, 'test2', 'v2', 2, '', '')
        #
        # # 查询数据
        # rows = query_all_data()
        # for row in rows:
        #     print(f'ID: {row[0]}, pixivID: {row[1]}, Name: {row[2]}, Author: {row[3]}, AuthorID: {row[4]}')

        # 删除数据（例如，删除 ID 为 1 的用户）
        # delete_by_id(1)

        # 再次查询数据
        # rows = query_all_data()
        # for row in rows:
        #     print(f'ID: {row[0]}, pixivID: {row[1]}, Name: {row[2]}, Author: {row[3]}, AuthorID: {row[4]}')

    finally:
        # 关闭数据库连接
        conn.close()
