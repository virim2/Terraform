#!/usr/bin/env python3
import argparse, time, sys
import pymysql

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="localhost")
parser.add_argument("--port", type=int, default=3306)
parser.add_argument("--user", default="root")
parser.add_argument("--password", default="")
parser.add_argument("--database", default=None)
parser.add_argument("--timeout", type=int, default=30)
args = parser.parse_args()

start = time.time()
while True:
    try:
        conn = pymysql.connect(
            host=args.host, port=args.port,
            user=args.user, password=args.password,
            database=args.database if args.database else None,
            connect_timeout=3
        )
        conn.close()
        print("MySQL disponible.")
        sys.exit(0)
    except Exception as e:
        if time.time() - start > args.timeout:
            print("Timeout esperando MySQL:", str(e), file=sys.stderr)
            sys.exit(1)
        time.sleep(1)

