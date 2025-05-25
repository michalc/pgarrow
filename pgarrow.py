import adbc_driver_postgresql.dbapi
from sqlalchemy.dialects.postgresql.base import PGDialect


class PgDialect_pgarrow(PGDialect):
    @classmethod
    def import_dbapi(cls):
        return adbc_driver_postgresql.dbapi
