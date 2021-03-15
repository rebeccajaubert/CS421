import psycopg2


def connect():
    return psycopg2.connect(
        host='comp421.cs.mcgill.ca',
        port=5432,
        database='cs421',
        user='cs421g87',
        password='T3@m.87.is.the.b3st'
    )
