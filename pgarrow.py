import adbc_driver_postgresql.dbapi

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

    @util.memoized_property
    def _constraint_query(self):
        return sql.visitors.replacement_traverse(super()._constraint_query, {}, self._work_around_query_adbc_base_incompatibilities)

    @util.memoized_property
    def _index_query(self):
        return sql.visitors.replacement_traverse(super()._index_query, {}, self._work_around_query_adbc_base_incompatibilities)

    def _work_around_query_adbc_base_incompatibilities(self, obj):
        '''Works around cases where ADBC is not compatible with the base PostgreSQL dialect queries

        1. Cases of arguments to functions that have to have INT arguments to INT

           This works around the issues that the underlying adbc driver converts bound Python int
           arguments to BIGINT, which happens due to the queries in _constraint_query and
           _index_query

           Discussed at https://github.com/apache/arrow-adbc/discussions/2865
           WIP PR at https://github.com/apache/arrow-adbc/pull/2881, which when released this
           function should be removed

           When removed, might be able to reduce the minimum SQLAlchemy on Python 3.13 from 2.0.41
           to 2.0.31, because the minimum version was only increased to support this

        2. Cases of querying int2vector fields, and specifically pg_index.indoption

           This works around the fact that querying int2vector seems to result in binary data
           returned. To avoid this, we maniuplate the query in PostgreSQL to return array of ints,
           which behaves as the query in the base dialect expects

           Discussed at https://github.com/apache/arrow-adbc/discussions/2899
        '''
        if isinstance(obj, sql.schema.Column) and obj._label == 'pg_catalog_pg_index_indoption':
            return cast(sql.func.string_to_array(cast(pg_catalog.pg_index.c.indoption, TEXT), ' '), ARRAY(INT)).label('indoption')

        if isinstance(obj, sql.functions.Function) and obj.name in ('generate_subscripts', 'pg_get_indexdef'):
            arguments = [
                argument
                for child in obj.get_children()
                for sub in child.get_children()
                for argument in sub.clauses
            ]
            new_arguments = [
                (argument if i != 1 else cast(argument, INT))
                for i, argument in enumerate(arguments)
            ]
            function_call = getattr(sql.func, obj.name)(*new_arguments)
            return \
                function_call.label("ord") if obj.name == 'generate_subscripts' else \
                function_call


class AdbcFixedParamStyleDBAPI():
    # adbc_driver_postgresql.dbapi has paramstyle of pyformat
    paramstyle = "numeric_dollar"
    Error = adbc_driver_postgresql.dbapi.Error

    def connect(self, *args, **kwargs):
        return adbc_driver_postgresql.dbapi.connect(*args, **kwargs)
