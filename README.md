# pgarrow

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
