import sqlalchemy as sa


def test_initialise():
	engine = sa.create_engine('postgresql+pgarrow://postgres@127.0.0.1:5432/')
