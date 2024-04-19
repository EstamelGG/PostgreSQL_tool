#!/usr/bin/python

import psycopg2


def connect(host, password, port="5432", user="postgres", db="template1"):
    conn = psycopg2.connect(database=db, user=user, password=password, host=host, port=port)
    print("Opened database successfully")
    return conn


def sql_query(conn, sql):
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    print(rows)


def quit(conn):
    conn.close()


password = "123456"
host = "192.168.18.131"

sql_query(connect(host=host, password=password), "show server_version;")
