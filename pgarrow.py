import adbc_driver_postgresql.dbapi
from sqlalchemy.dialects.postgresql.base import PGDialect


class PgDialect_pgarrow(PGDialect):
    # This is already set in PGDialect, but shows an error if we don't set to true
    # AttributeError: 'PgDialect_pgarrow' object has no attribute 'driver'
    supports_statement_cache = True

    @classmethod
    def import_dbapi(cls):
        return AdbcFixedParamStyleDBAPI()

    def create_connect_args(self, url):
        return ((url._replace(drivername='postgresql').render_as_string(hide_password=False),), {})

    def get_isolation_level(self, dbapi_connection):
        with dbapi_connection.cursor(
            adbc_stmt_kwargs={
                adbc_driver_postgresql.StatementOptions.USE_COPY.value: False,
            }
        ) as cursor:
            cursor.execute("show transaction isolation level")
            val = cursor.fetchone()[0]
        return val.upper()

    def _set_backslash_escapes(self, connection):
        with connection._dbapi_connection.cursor(
            adbc_stmt_kwargs={
                adbc_driver_postgresql.StatementOptions.USE_COPY.value: False,
            }
        ) as cursor:
            cursor.execute("show standard_conforming_strings")
            self._backslash_escapes = cursor.fetchone()[0] == "off"


class AdbcFixedParamStyleDBAPI():
    # adbc_driver_postgresql.dbapi has paramstyle of pyformat
    paramstyle = "numeric_dollar"
    Error = adbc_driver_postgresql.dbapi.Error

    def connect(self, *args, **kwargs):
        return adbc_driver_postgresql.dbapi.connect(*args, **kwargs)
