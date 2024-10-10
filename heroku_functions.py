import psycopg2
import pandas as pd
import os


def postgres_connect():
    try:
        DATABASE_URL = os.environ['DATABASE_URL']
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        conn.set_session(readonly=False)  # *******WRITE-ENABLED CONNECTION*******
        return conn
    except psycopg2.Error as e:
        error_info = str(e)
        error_message = 'Failed to connect to database. Error: {' + error_info + '}'
        print(error_message)
        raise ConnectionError


def postgres_execute(sql_text):
    """Execute an SQL query"""
    conn = postgres_connect()
    cur = conn.cursor()
    # rollback any errors
    # cur.execute("ROLLBACK")
    cur.execute(sql_text)
    try:
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        result = pd.DataFrame(rows, columns=colnames)

    except:
        result = pd.DataFrame()
    conn.commit()
    cur.close()
    conn.close()
    return result

def list_index():
	query = """select *
	from pg_indexes
	where tablename not like 'pg%'"""
	result = postgres_execute(query)
	
def create_index():
	query = """create index actions_gameid on public.actions using btree (gameid)"""
	result = postgres_execute(query)

	
#delete rows from public.actions
def delete_old_actions(ndays=7):
	import datetime
	now = datetime.datetime.now()
	then = datetime.datetime.now() - datetime.timedelta(days=ndays)
	query = """select * from public.actions where time<**time**""".replace("**time**", "TO_TIMESTAMP('" + str(then)[:19] + "', 'YYYY-MM-DD HH24:MI:SS')")
	result = postgres_execute(query)
	print("delete "+str(len(result))+" rows from actions?")
	x = input()
	if x.lower()=='y': 
		query = """delete from public.actions where time<**time**""".replace("**time**", "TO_TIMESTAMP('" + str(then)[:19] + "', 'YYYY-MM-DD HH24:MI:SS')")
		result = postgres_execute(query)
		print('deleted')
	else:
		print('not deleted')

def delete_old_games(ndays=7):
	import datetime
	now = datetime.datetime.now()
	then = datetime.datetime.now() - datetime.timedelta(days=ndays)
	query = """select * from public.games where startTime<**time**""".replace("**time**", "TO_TIMESTAMP('" + str(then)[:19] + "', 'YYYY-MM-DD HH24:MI:SS')")
	result = postgres_execute(query)
	print("delete "+str(len(result))+" rows from actions?")
	x = input()
	if x.lower()=='y': 
		query = """delete from public.games where startTime<**time**""".replace("**time**", "TO_TIMESTAMP('" + str(then)[:19] + "', 'YYYY-MM-DD HH24:MI:SS')")
		result = postgres_execute(query)
		print('deleted')
	else:
		print('not deleted')

