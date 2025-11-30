import adbc_driver_manager
import adbc_driver_postgresql.dbapi
import pyarrow as pa

from sqlalchemy import sql, cast
from sqlalchemy.dialects import util
from sqlalchemy.dialects.postgresql import pg_catalog
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.types import ARRAY, INT, TEXT


class PgDialect_pgarrow(PGDialect):
    # This is already set in PGDialect, but shows an error or warning (depending on if we also set
    # driver) if we don't set it again
    supports_statement_cache = True

    # This should be an "identifying name for the dialect's DBAPI". Was torn on the form of this,
    # for example should it be "adbc_driver_postgresql" the Python module name, or
    # "adbc-driver-postgresql" the published package name, or something shorter like "adbc?
    # Opted to have it match the user facing "postgresql+pgarrow" used when defining the engine,
    # which seems to be the case for many other dialects. This also means it can be used to to
    # identify this dialect seperate from other adbc dialects that might be written in future
    driver = 'pgarrow'

    @classmethod
    def import_dbapi(cls):
        return AdbcDbapi()

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


class AdbcDbabiConnection(adbc_driver_manager.dbapi.Connection):
    def cursor(
        self,
        *,
        adbc_stmt_kwargs = None,
    ) :
        return AdbcDbabiCursor(self, adbc_stmt_kwargs, dbapi_backend=self._backend)

class AdbcDbabiCursor(adbc_driver_manager.dbapi.Cursor):
    def execute(self, operation, parameters=None):
        parameters_schema = self.adbc_prepare(operation)
        return super().execute(operation,
            parameters if not bool(parameters_schema) else \
            pa.RecordBatch.from_arrays([parameters], schema=parameters_schema)
        )

class AdbcDbapi():
    # adbc_driver_postgresql.dbapi has paramstyle of pyformat
    paramstyle = "numeric_dollar"
    Error = adbc_driver_postgresql.dbapi.Error

    def connect(self,uri: str,
        db_kwargs = None,
        conn_kwargs = None,
        *,
        autocommit: bool = False,
        **kwargs
    ):
        db = None
        conn = None

        try:
            db = adbc_driver_postgresql.connect(uri, db_kwargs=db_kwargs)
            conn = adbc_driver_manager.AdbcConnection(db, **(conn_kwargs or {}))
            return AdbcDbabiConnection(
                db, conn, conn_kwargs=conn_kwargs, autocommit=autocommit, **kwargs
            )
        except Exception:
            if conn:
                conn.close()
            if db:
                db.close()
            raise
