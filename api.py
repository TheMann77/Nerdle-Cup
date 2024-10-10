# Live API accessible at --REDACTED--

from heroku_functions import postgres_execute
from random import randint
import datetime
import pandas as pd
from flask import Flask, request, jsonify
import random
import pytz
from better_profanity import profanity

app = Flask(__name__)


def str_time_now():
    time_now = str(datetime.datetime.utcnow())[:-7]
    time_now = "TO_TIMESTAMP('" + time_now + "', 'YYYY-MM-DD HH24:MI:SS')"
    return time_now


def check_game(game_code):
    games = postgres_execute("""SELECT ID, StartTime, EndTime FROM Games""")
    if game_code in list(games['id']):
        start_time = pd.Timestamp.to_pydatetime(games[games['id'] == game_code]['starttime'].iloc[0])
        end_time = pd.Timestamp.to_pydatetime(games[games['id'] == game_code]['endtime'].iloc[0])
        now_time = datetime.datetime.utcnow()
        if now_time < start_time:
            result = "Game not started"
        elif now_time > end_time:
            result = "Game ended"
        else:
            result = "Game in progress"
    else:
        result = "Game not valid"
    return result


@app.route('/creategame/', methods=['GET'])
def create_game():
    size = request.args.get('size')
    nrounds = int(float(request.args.get('nrounds')))
    start_in = float(request.args.get('start_in'))
    time_limit_per_round = float(request.args.get('tpr'))

    # size = ['Classic', 'Mini', 'Micro']
    # mode = ['Classic', 'Speed']
    # start_in, time_limit_per_round given in minutes

    game_code = randint(100000, 999999)
    sql_string = """SELECT ID FROM Games"""
    game_list = list(postgres_execute(sql_string)['id'])
    while game_code in game_list:
        game_code = randint(10000000, 99999999)

    filename = str.lower(size) + 'words.txt'
    allwords = [x.strip() for x in open(filename, 'r').readlines()]
    words = random.sample(allwords, nrounds)
    words_string = str(words)[1:-1].replace("'", "")

    start_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=start_in)
    end_time = start_time + datetime.timedelta(minutes=time_limit_per_round * nrounds)
    start_time, end_time = str(start_time)[:-7], str(end_time)[:-7]
    start_time = "TO_TIMESTAMP('" + start_time + "', 'YYYY-MM-DD HH24:MI:SS')"
    end_time = "TO_TIMESTAMP('" + end_time + "', 'YYYY-MM-DD HH24:MI:SS')"

    sql_string = """INSERT INTO Games (ID,GameSize,NumGames,Answers,StartTime,EndTime)
    VALUES (""" + ', '.join(
        [str(game_code), "'" + size + "'", str(nrounds), "'" + words_string + "'", start_time, end_time]) + ");"
    postgres_execute(sql_string)
    response = jsonify(game_code)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/updategamestart/', methods=['GET'])
def update_game_start():
    game_code = int(request.args.get('code'))
    delay = int(request.args.get('delay')) #delay in seconds from now
    if delay is None:
        delay = 0 
    game_status = check_game(game_code=game_code)
    if game_status in ["Game ended", "Game not valid", "Game in progress"]:
        result = game_status
    elif game_status in ["Game not started"]:
        sql_text = """SELECT StartTime, EndTime FROM Games WHERE ID = **game_code**""".replace(
            '**game_code**', str(game_code))
        times = postgres_execute(sql_text)
        start_time = pd.Timestamp.to_pydatetime(times['starttime'][0])
        end_time = pd.Timestamp.to_pydatetime(times['endtime'][0])
        now_time = datetime.datetime.utcnow().replace(microsecond=0)
        now_time = min(start_time, now_time+datetime.timedelta(seconds=delay))
        new_end_time = now_time + (end_time - start_time)

        now_time_str = "TO_TIMESTAMP('" + str(now_time) + "', 'YYYY-MM-DD HH24:MI:SS')"
        new_end_time_str = "TO_TIMESTAMP('" + str(new_end_time) + "', 'YYYY-MM-DD HH24:MI:SS')"
   
        sql_text = """UPDATE Games SET StartTime = **time_now**, EndTime = **new_end_time** WHERE ID = **game_code**
            """.replace('**time_now**', now_time_str).replace('**new_end_time**', new_end_time_str).replace('**game_code**', str(game_code))
        postgres_execute(sql_text)
        result = True
    else:
        raise ValueError('Invalid check_game response:' + game_status)
    response = jsonify(result)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/checkgame/', methods=['GET'])
def check_game_api():
    try:
        game_code = int(request.args.get('code'))
        response = jsonify(check_game(game_code))
    except:
        response = jsonify("Game not valid")
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/addplayer/', methods=['GET'])
def add_player():
    game_code = int(request.args.get('code'))
    name = request.args.get('name')

    name = profanity.censor(name)
    game_status = check_game(game_code=game_code)
    if game_status in ["Game ended", "Game not valid"]:
        result = game_status
    elif game_status in ["Game not started", "Game in progress"]:
        game_names = list(postgres_execute("""
        SELECT Name FROM Actions
        WHERE Action = 'Join' AND GameID = **game_code**
        """.replace('**game_code**', str(game_code)))['name'])
        if name in game_names:
            result = "Name taken"
        elif len(game_names)>=10:
            result = "Max players"			
        else:
            time_now = str_time_now()
            sql_text = """
            INSERT INTO Actions (Action, Time, GameID, Name)
            VALUES ('Join', **time_now**, **game_code**, '**name**')
            """.replace('**time_now**', time_now).replace('**game_code**', str(game_code)).replace('**name**', name)
            postgres_execute(sql_text)
            result = True
    else:
        raise ValueError('Invalid check_game response:' + game_status)
    response = jsonify(result)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/addscore/', methods=['GET'])
def add_score():
    game_code = int(request.args.get('code'))
    user_name = request.args.get('name')
    score = int(request.args.get('score'))

    game_status = check_game(game_code)
#    if game_status == "Game in progress":  "Game not started"
    if game_status in ["Game in progress", "Game not started"]:
        time_now = str(datetime.datetime.utcnow() - datetime.timedelta(seconds=2))[:-7]
        time_now = "TO_TIMESTAMP('" + time_now + "', 'YYYY-MM-DD HH24:MI:SS')"
        sql_text = """SELECT Value FROM Actions
        WHERE GameID = **game_code**
        AND Action = 'Score'
        AND Time > **timenow**""".replace('**game_code**', str(game_code)).replace('**timenow**', time_now)
        if len(postgres_execute(sql_text)) == 0:
            sql_text = """
            INSERT INTO Actions (Action, Time, GameID, Name, Value)
            VALUES ('Score', **time_now**, **game_code**, '**name**', **value**)
            """.replace('**time_now**', str_time_now()).replace('**game_code**', str(game_code)).replace('**name**',
                                                                                                         user_name).replace(
                '**value**', str(score))
            postgres_execute(sql_text)
            result = True
        else:
            result = "Double entry error"
    else:
        result = game_status
    response = jsonify(result)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/getscores/', methods=['GET'])
def get_scores():
    game_code = int(request.args.get('code'))

    game_status = check_game(game_code)
    if game_status in ["Game in progress", "Game ended", "Game not started"]:
        sql_text = """SELECT StartTime, EndTime, NumGames FROM Games WHERE ID = **game_code**""".replace(
            '**game_code**', str(game_code))
        times = postgres_execute(sql_text)
        start_time = pd.Timestamp.to_pydatetime(times['starttime'][0])
        end_time = pd.Timestamp.to_pydatetime(times['endtime'][0])
        now_time = datetime.datetime.utcnow().replace(microsecond=0)
        num_games = times['numgames'][0]

        sql_text = """
        SELECT Name, SUM(Value) AS Score, COUNT(Value) AS Played, MAX(Time) AS LastTime FROM Actions
        WHERE Action = 'Score'
        AND GameId = **game_code**
        GROUP BY Name
        """.replace('**game_code**', str(game_code))
        data = postgres_execute(sql_text)
        data['ppg'] = round(data['score'] / data['played'], 2)

        sql_text = """
        SELECT Name, MAX(Time) AS LastTime, COUNT(Action) AS NumActions FROM Actions 
        WHERE GameId = **game_code**
        GROUP BY Name""".replace('**game_code**', str(game_code))
        data2 = postgres_execute(sql_text)
        data2 = data2[data2['numactions'] == 1].drop(columns=['numactions'])
        data2['score'] = 0
        data2['played'] = 0
        data2['ppg'] = 0
        data = pd.concat([data, data2])
        data.reset_index(drop=True, inplace=True)
        if len(data) == 0:
            response = jsonify("No players")
        else:
            for i in list(data.index):
                if data.loc[i, 'played'] >= num_games:
                    last_game_time = pd.Timestamp.to_pydatetime(data.loc[i, 'lasttime'])
                    data.loc[i, 'time'] = last_game_time - start_time
                elif now_time > start_time:
                    data.loc[i, 'time'] = min(now_time, end_time) - start_time
                else:
                    data.loc[i, 'time'] = datetime.timedelta(seconds=0)

            data.drop(columns='lasttime', inplace=True)
            data.sort_values(['score', 'time', 'ppg', 'name'], ascending=[False, True, False, True], inplace=True)
            for i in list(data.index):
                t = str(data.loc[i, 'time'])
                if t[0] == '0':
                    # Remove days
                    t = t[7:]
                    if t[0] == '0':
                        # Remove hours 1
                        t = t[1:]
                        if t[0] == '0':
                            # Remove hours 2
                            t = t[2:]
                            if t[0] == '0':
                                # Remove minutes 1
                                t = t[1:]
                data.loc[i, 'time'] = t
            data.reset_index(drop=True, inplace=True)
            prev_index = None
            for i in list(data.index):
                if prev_index is None or not data.loc[i, ['score', 'ppg', 'time']].equals(
                        data.loc[prev_index, ['score', 'ppg', 'time']]):
                    data.loc[i, 'pos'] = int(i + 1)
                else:
                    data.loc[i, 'pos'] = int(data.loc[prev_index, 'pos'])
                prev_index = i
            #data.set_index('name', inplace=True)
            data = data[['pos', 'name', 'time', 'played', 'score', 'ppg']]
            response = jsonify(data.to_json())
    else:
        response = jsonify(game_status)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/gettimes/', methods=['GET'])
def get_times():
    game_code = int(request.args.get('code'))
    times = postgres_execute("""SELECT StartTime, EndTime FROM Games WHERE ID = **game_code**""".replace('**game_code**', str(game_code)))
    if len(times):
        start_time = pytz.utc.localize(pd.Timestamp.to_pydatetime(times['starttime'][0]))
        end_time = pytz.utc.localize(pd.Timestamp.to_pydatetime(times['endtime'][0]))
        response = jsonify([start_time, end_time])
    else:
        response = jsonify("Game not valid")
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/getgameinfo/', methods=['GET'])
def get_game_info():
    game_code = int(request.args.get('code'))
    data = postgres_execute("""SELECT Answers, GameSize FROM Games WHERE ID = **game_code**""".replace('**game_code**', str(game_code)))
    if len(data) == 0:
        response = jsonify("Game not valid")
    else:
        games = data['answers'][0].split(', ')
        random.shuffle(games)
        games = ', '.join(games)
        size = data['gamesize'][0]
        response = jsonify({'games': games, 'size': size})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/')
def index():
    # A welcome message to test our server
    return """
    <h1>NerdleWars API home page</h1>
    <h2>Functions:</h2>
    <h3>/creategame/?size=Classic&nrounds=10&start_in=0&tpr=1</h3> <a>returns game code (*tpr = time per round, start_in and tpr given in minutes)</a>
    <h3>/checkgame/?code=123456</h3> <a>returns game status "Game not started", "Game in progress", "Game ended", "Game not valid"</a>
    <h3>/addplayer/?code=123456&name=Alex</h3> <a>returns True if successful, otherwise "Name taken", "Game ended", "Game not valid"</a>
    <h3>/addscore/?code=123456&name=Alex&score=4</h3> <a>returns True if succesful, otherwise "Game not started", "Game ended", "Game not valid"</a>
    <h3>/getscores/?code=123456</h3> <a>returns jsonified scores dataframe with columns: name, score, played, ppg, time, pos</a>
    <h3>/gettimes/?code=123456</h3> <a>returns [start_time, end_time], or "Game not valid"</a>
    <h3>/getgameinfo/?code=123456</h3> <a>returns {'games': '2+4=2, 3+3=6, '4+4=8', 'size': 'Classic'}, or "Game not valid"</a>
    """


if __name__ == '__main__':
    app.run(threaded=True, port=5000)
