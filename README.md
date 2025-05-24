# pgarrow

A SQLAlchemy PostgreSQL dialect for ADBC (Arrow Database Connectivity)


## Installation

pgarrow can be installed from PyPI using pip:

```bash
pip install pgarrow
```


## Usage

pgarrow can be used using the `postgresql+pgarrow` dialect:

```python
import sqlalchemy as sa

engine = sa.create_engine('postgresql+pgarrow://postgres@127.0.0.1:5432/')
```
