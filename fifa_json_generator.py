import json
import os
import pygsheets
import numpy as np
from google.cloud import storage
from random import random
from configs import groupShtID, round16ShtID, advanceShtID, googleshtURL, flags_mapping, acceptable_group, acceptable_round
import tempfile
tmpdir = tempfile.gettempdir()

def get_sht_data(shtID):
    # /usr/local/cronjobs/mirrormedia-1470651750304-dbc9a9119b4e
    gc = pygsheets.authorize(service_file='key.json')
    sht = gc.open_by_url(googleshtURL)
    print(sht.updated)
    wks = sht.worksheet('id', shtID)
    # wks = sht.worksheet_by_title(title)
    return wks.get_all_values()


def generateRandomKey():
    return np.base_repr(int(np.floor(random() * 2 ** 24)), 32).lower()


groupData = get_sht_data(groupShtID)
round16Data = get_sht_data(round16ShtID)
advancedData = get_sht_data(advanceShtID)

advancedTeams = []
for row in advancedData:
    if row[0] in acceptable_group:
        advancedTeams.append(row[1])


def uploadJson(filename, data, dataname):
    with open(f'{tmpdir}/{filename}', 'w') as f:
        f.write(json.dumps({dataname: data}, ensure_ascii=False))
    # storage_client = storage.Client().from_service_account_json('key.json')
    # bucket = storage_client.bucket('statics.mirrormedia.mg')
    # blob = bucket.blob(f'json/{filename}')
    # blob.upload_from_filename(f'{tmpdir}/{filename}')
    # print("File {} uploaded to {}.".format( f'{tmpdir}/{filename}', f'json/{filename}'))
    # blob.make_public()
    # blob.cache_control = 'max-age=180'
    # blob.content_type = 'application/json'
    # blob.patch()
    # print("The metadata configuration for the blob is complete")


def generate_group_schedule(row, groups):
    game = {}
    groupName = row[0]
    game["key"] = generateRandomKey()
    game["dateTime"] = f'{row[1]} {row[2]}'
    game["team1"] = f'{flags_mapping.setdefault(row[3], "")} {row[3]}'
    game["team2"] = f'{flags_mapping.setdefault(row[4], "")} {row[4]}'
    game["ended"] = True if row[5] == 'TRUE' else False
    #print(game)
    group = groups.setdefault(groupName, [])
    group.append(game)


def organize_team_result(teamName, row, team):
    team["GP"] += 1

    team1Score = int(row[6])
    team2Score = int(row[7])
    if teamName == row[3]:
        team["points"] += team1Score
        if team1Score > team2Score:
            team["wins"] += 1
            thisGameResult = True
        elif team1Score < team2Score:
            team["losses"] += 1
            thisGameResult = False
        else:
            team["draws"] += 1
            thisGameResult = None
        team["GA"] += team2Score
    else:
        team["points"] += team2Score
        if team2Score > team1Score:
            team["wins"] += 1
            thisGameResult = True
        elif team2Score < team1Score:
            team["losses"] += 1
            thisGameResult = False
        else:
            team["draws"] += 1
            thisGameResult = None
        team["GA"] += team1Score
    team["GS"] = team["points"]
    team["GD"] = team["GS"] - team["GA"]
    # recentCount = team["GP"] if team["recent"] else 0
    if teamName in advancedTeams:
        team["advanced"] = True
    
    team["recent"].insert(0, {0: thisGameResult})
    for  i, rec in enumerate(team["recent"]):
        if i in rec:
            rec[i+1] = rec.pop(i)




def generate_group_result(row, groups_result):
    groupName = row[0]
    team1Name = row[3]
    team2Name = row[4]
    team1_template = {
        "key": generateRandomKey(),
        "team": f'{flags_mapping.setdefault(team1Name, "")} {team1Name}',
        "GP": 0,
        "points": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "GS": 0,
        "GA": 0,
        "GD": 0,
        "recent": [],
        "advanced": False
    }
    team2_template = {
        "key": generateRandomKey(),
        "team": f'{flags_mapping.setdefault(team2Name, "")} {team2Name}',
        "GP": 0,
        "points": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "GS": 0,
        "GA": 0,
        "GD": 0,
        "recent": [],
        "advanced": False
    }
    group = groups_result.setdefault(groupName, {})
    team1 = group.setdefault(team1Name, team1_template)
    team2 = group.setdefault(team2Name, team2_template)
    organize_team_result(team1Name, row, team1)
    organize_team_result(team2Name, row, team2)


def generate_group_json():
    groups_schedule = {}
    groups_result = {}
    for row in groupData:
        # print(row)
        group = row[0]
        if group not in acceptable_group:
            continue
        generate_group_schedule(row, groups_schedule)

        ended = True if row[5] == 'TRUE' else False
        if ended and row[3] and row[4] and row[6] and row[7]:
            generate_group_result(row, groups_result)

    schedule = [{groupName: sorted(groupGames, key=lambda x: x['dateTime'])}
                for groupName, groupGames in groups_schedule.items()]
    schedule.sort(key=lambda x: list(x.keys()))  # sort by group

    result = [{groupName: [teamResult for teamResult in groupResult.values()]}
              for groupName, groupResult in groups_result.items()]
    result.sort(key=lambda x: list(x.keys()))  # sort by group

    # with open('fifa2022_group_schedule.json', 'w') as f:
    #     f.write(json.dumps({"schedule": schedule}, ensure_ascii=False))
    # with open('fifa2022_group_result.json', 'w') as f:
    # f.write(json.dumps({"result": result}, ensure_ascii=False))
    uploadJson('fifa2022_group_schedule.json', schedule, "schedule")
    uploadJson('fifa2022_group_result.json', result, "result")


def generate_round16_json():
    roundOf16 = []
    for row in round16Data:
        # print(row)
        round = row[0]
        if round not in acceptable_round or not (row[1] and row[2]) :
            continue
        acceptable_round[round] += 1
        ended = True if row[5] == 'TRUE' else False
        game = {
            "key": f'{round}-{acceptable_round[round]}',
            "dateTime": f'{row[1]} {row[2]}',
            "team1": {
                "teamName": f'{flags_mapping.setdefault(row[3], "")} {row[3]}'
            },
            "team2": {
                "teamName": f'{flags_mapping.setdefault(row[4], "")} {row[4]}',
            },
            "ended": ended,
            "PK": False,
            "winner": row[6]
        }

        if ended and row[7] and row[8]:
            game["team1"]["score"] = row[7]
            game["team2"]["score"] = row[8]
            if row[9] and row[10]:
                game["team1"]["scorePK"] = row[9]
                game["team2"]["scorePK"] = row[10]
                game["PK"] = True

        roundOf16.append(game)

    # with open('fifa2022_round16.json', 'w') as f:
    #     f.write(json.dumps({"roundOf16": roundOf16}, ensure_ascii=False))
    uploadJson('fifa2022_round16_result.json',
               roundOf16, "roundOf16")


def genJson():
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    generate_group_json()
    # generate_round16_json()
    print("done")
    return "OK"
genJson()  
