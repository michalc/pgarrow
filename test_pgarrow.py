import uuid

import adbc_driver_postgresql
import pytest
import pyarrow as pa
import sqlalchemy as sa


engine_future = {'future': True} if tuple(int(v) for v in sa.__version__.split('.')) < (2, 0, 0) else {}


def test_trivial_query():
    engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/', **engine_future)
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT 1")).fetchall() == [(1,)]


def test_basic_transaction_isolation():
    engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/', **engine_future)
    table_name = "table_" + uuid.uuid4().hex

    with \
            engine.connect() as conn_1, \
            engine.connect() as conn_2, \
            engine.connect() as conn_3:

        conn_1.execute(sa.text(f"CREATE TABLE {table_name} (id int)"))
        conn_1.execute(sa.text(f"INSERT INTO {table_name} VALUES (1)"))

        with pytest.raises(sa.exc.ProgrammingError, match=f'relation "{table_name}" does not exist'):
            conn_2.execute(sa.text(f"SELECT * FROM {table_name}"))

        conn_1.commit()
        assert conn_3.execute(sa.text(f"SELECT * FROM {table_name}")).fetchall() == [(1,)]


def test_bound_parameters_prepared():
    # Doesn't exactly test behaviour of pgarrow, but more that the underlying adbc-driver-postgresql can
    # prepare queries (which means sending them to the DB to get the parameter types if it can work them
    # out)
    engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/', **engine_future)

    with \
            engine.connect() as conn, \
            conn.connection.driver_connection.cursor() as cursor:

        # Chosen because the default binding for integers ends up being int64, and there is no matching
        # generate_subscripts for that type
        query = "SELECT generate_subscripts('{NULL,1,NULL,2}'::int[], $1)"

        parameters_schema = cursor.adbc_prepare(query)
        parameters = [1,]
        assert cursor.execute(query,
            pa.RecordBatch.from_arrays([parameters], schema=parameters_schema)
        ).fetchall() == [(1,), (2,), (3,), (4,)]


def test_select_as_pyarrow_table():
    engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/', **engine_future)

    with \
            engine.connect() as conn, \
            conn.connection.driver_connection.cursor() as cursor:

        cursor.execute("SELECT 1 AS a, 2.0::double precision AS b, 'Hello, world!' AS c")
        table = cursor.fetch_arrow_table()
        assert table == pa.Table.from_arrays([[1,], [2,], ['Hello, world!',]], schema=pa.schema([
            ('a', pa.int32()),
            ('b', pa.float64()),
            ('c', pa.string())
        ]))


def test_create_from_pyarrow_table():
    engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/', **engine_future)
    table_name = "table_" + uuid.uuid4().hex

    with \
            engine.connect() as conn_1, \
            engine.connect() as conn_2, \
            engine.connect() as conn_3, \
            conn_1.connection.driver_connection.cursor() as cursor:

        table = pa.Table.from_arrays([[1,], [2,], ['Hello, world!',]], schema=pa.schema([
            ('a', pa.int32()),
            ('b', pa.float64()),
            ('c', pa.string())
        ]))

        cursor.adbc_ingest(table_name, table, mode="create")

        assert conn_1.execute(sa.text(f"SELECT * FROM {table_name}")).fetchall() == [(1, 2.0, 'Hello, world!')]

        # Make sure adbc_ingest doesn't commit under the hood
        with pytest.raises(sa.exc.ProgrammingError, match=f'relation "{table_name}" does not exist'):
            conn_2.execute(sa.text(f"SELECT * FROM {table_name}"))

        conn_1.commit()
        assert conn_3.execute(sa.text(f"SELECT * FROM {table_name}")).fetchall() == [(1, 2.0, 'Hello, world!')]


def test_create_sqlalchemy_table_and_append_pyarrow_table():
    engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/', **engine_future)
    table_name = "table_" + uuid.uuid4().hex

    metadata = sa.MetaData()
    sa.Table(
        table_name,
        metadata,
        sa.Column("a", sa.INTEGER),
        sa.Column("b", sa.DOUBLE_PRECISION),
        sa.Column("c", sa.TEXT),
        schema="public",
    )

    with \
            engine.connect() as conn_1, \
            engine.connect() as conn_2, \
            engine.connect() as conn_3, \
            conn_1.connection.driver_connection.cursor() as cursor:

        metadata.create_all(conn_1)

        table = pa.Table.from_arrays([[1,], [2,], ['Hello, world!',]], schema=pa.schema([
            ('a', pa.int32()),
            ('b', pa.float64()),
            ('c', pa.string())
        ]))

        cursor.adbc_ingest(table_name, table, mode="append")

        assert conn_1.execute(sa.text(f"SELECT * FROM {table_name}")).fetchall() == [(1, 2.0, 'Hello, world!')]

        # Make sure adbc_ingest doesn't commit under the hood
        with pytest.raises(sa.exc.ProgrammingError, match=f'relation "{table_name}" does not exist'):
            conn_2.execute(sa.text(f"SELECT * FROM {table_name}"))

        conn_1.commit()
        assert conn_3.execute(sa.text(f"SELECT * FROM {table_name}")).fetchall() == [(1, 2.0, 'Hello, world!')]


def test_reflection():
    engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/', **engine_future)
    table_name = "table_" + uuid.uuid4().hex

    with engine.connect() as conn:
        conn.execute(sa.text(f"CREATE TABLE {table_name} (id int)"))
        conn.execute(sa.text(f"CREATE INDEX ON {table_name} (id)"))
        table = sa.Table(table_name, sa.MetaData(), schema="public", autoload_with=conn)
        assert table.name == table_name
        assert table.columns[0].name == 'id'
        assert isinstance(table.columns[0].type, sa.INTEGER)
