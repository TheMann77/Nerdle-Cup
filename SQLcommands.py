from heroku_functions import postgres_execute

postgres_execute("""
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE Actions (
ID UUID NOT NULL DEFAULT uuid_generate_v1(),
Action varchar,
Time timestamp,
GameID int,
Name varchar,
Value int,
PRIMARY KEY (ID));
""")
