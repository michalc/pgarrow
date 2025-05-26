# pgarrow [![PyPI package](https://img.shields.io/pypi/v/pgarrow?label=PyPI%20package)](https://pypi.org/project/pgarrow/) [![Test suite](https://img.shields.io/github/actions/workflow/status/michalc/pgarrow/test.yaml?label=Test%20suite)](https://github.com/michalc/pgarrow/actions/workflows/test.yaml) [![Code coverage](https://img.shields.io/codecov/c/github/michalc/pgarrow?label=Code%20coverage)](https://app.codecov.io/gh/michalc/pgarrow)

A SQLAlchemy PostgreSQL dialect for ADBC (Arrow Database Connectivity)


## Installation

pgarrow can be installed from PyPI using pip:

```bash
pip install pgarrow
```


## Usage

pgarrow can be used using the `postgresql+pgarrow` dialect. For example, to connect to a running database on 127.0.0.1 (localhost) on port 5432 as user _postgres_ with password _password_ and run a trivial query:

```python
import sqlalchemy as sa

engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/')

with engine.connect() as conn:
    results = conn.execute(sa.text("SELECT 1")).fetchall()
```

To fetch data as an arrow table, which should be the most performant for large datasets, you must use SQLAlchemy's `driver_connection` to access the ADBC-level connection, create a cursor from it to run the query and fetch the table using `fetch_arrow_table`:

```python
import sqlalchemy as sa

engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/')

with \
        engine.connect() as conn, \
        conn.connection.driver_connection.cursor() as cursor:

        cursor.execute("SELECT 1 AS a, 2.0::double precision AS b, 'Hello, world!' AS c")
        table = cursor.fetch_arrow_table()
```

To insert data into the database from an arrow table, a similar pattern must be used to use `adbc_ingest`

```python
import sqlalchemy as sa

engine = sa.create_engine('postgresql+pgarrow://postgres:password@127.0.0.1:5432/')
table = pa.Table.from_arrays([[1,], [2,], ['Hello, world!',]], schema=pa.schema([
    ('a', pa.int32()),
    ('b', pa.float64()),
    ('c', pa.string())
]))

with \
        engine.connect() as conn, \
        conn.connection.driver_connection.cursor() as cursor:

    cursor.adbc_ingest("my_table", table, mode="create")
    conn.commit()
```

Or to create a table using SQLAlchemy, and then append as pyarrow table to it:

```python
import sqlalchemy as sa

metadata = sa.MetaData()
sa.Table(
    "my_table",
    metadata,
    sa.Column("a", sa.INTEGER),
    sa.Column("b", sa.DOUBLE_PRECISION),
    sa.Column("c", sa.TEXT),
    schema="public",
)
table = pa.Table.from_arrays([[1,], [2,], ['Hello, world!',]], schema=pa.schema([
    ('a', pa.int32()),
    ('b', pa.float64()),
    ('c', pa.string())
]))

with \
        engine.connect() as conn, \
        conn.connection.driver_connection.cursor() as cursor:

    metadata.create_all(conn)
    cursor.adbc_ingest("my_table", table, mode="append")
    conn.commit()
```


## Compatibility

- Python >= 3.9 (tested on 3.9.0, 3.10.0, 3.11.1, 3.12.0, and 3.13.0)
- PostgreSQL >= 13.0 (tested on 13.0, 14.0, 15.0, and 16.0)
- SQLAlchemy >= 2.0.7 on Python < 3.13, and SQLAlchemy >= 2.0.31 on Python >= 3.13 (tested on 2.0.7 on Python before 3.13.0; and SQLAlchemy 2.0.31 on Python 3.13.0)
- PyArrow >= 15.0.0 on Python < 3.13, and PyArrow >= 18.0.0 on Python >= 3.13.0 (tested on 15.0.0, 16.0.0, 17.0.0, 18.0.0, 19.0.0, 20.0.0 on Python before 3.13.0; and 18.0.0, 19.0.0, and 20.0.0 on Python 3.13.0)
- adbc-driver-postgresql >= 1.6.0 (tested on 1.6.0)
