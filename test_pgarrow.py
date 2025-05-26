import uuid

import pytest
import sqlalchemy as sa


def test_trivial_query():
    engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/')
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT 1")).fetchall() == [(1,)]


def test_basic_transaction_isolation():
    engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/')
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
