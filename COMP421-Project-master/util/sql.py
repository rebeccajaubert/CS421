from datetime import datetime


class FixedRecord(dict):
    def __init__(self, *args, **kwargs):
        super(FixedRecord, self).__init__(*args, **kwargs)
        self.__dict__ = self


def objects(cursor):
    column_names = [col[0] for col in cursor.description]

    for row in cursor:
        yield FixedRecord(zip(column_names, row))


def sql_format_value(value):
    if isinstance(value, str):
        return "'%s'" % value.replace("'", "''")
    elif isinstance(value, datetime):
        return "'%s'" % value
    else:
        return str(value)


def sql_format_tuple(tup):
    return "(" + ', '.join(sql_format_value(x) for x in tup) + ")"


def insert_query(table_name, fields, tuples, return_fields=None):
    tuple_string = ",\n".join(sql_format_tuple(tup) for tup in tuples)

    query = "INSERT INTO %s (%s) VALUES\n%s\n" % (table_name, ','.join(fields), tuple_string)

    if return_fields is not None:
        query += " RETURNING %s" % (','.join(return_fields))

    return query
