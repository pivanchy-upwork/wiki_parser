import sys
sys.path.insert(0, 'src/vendor')
import json

import boto3
import pandas as pd
import requests

from datetime import datetime, timedelta

from botocore.exceptions import ClientError
from bs4 import BeautifulSoup

BUCKET_NAME = 'parsed-wiki'
DATE_FORMAT = '%H:%M, %d %B %Y'
HISTORY_DAYS_LIMIT = 30
JSON_FILE = 'parsed_wiki.json'
JSON_URL = 'https://parsed-wiki.s3.eu-central-1.amazonaws.com/parsed_wiki.json'
UPDATE_FIELD = 'number_update_time'
URL_TEMPLATE = 'https://en.wikipedia.org/w/index.php?title={}&action=history'


def parse_wiki(title: str) -> dict:
    """ Parses wiki page change history for some specific topic.
    Returns result in the following format:
    
        {
            <title>: 
                {
                    "latest_update_time": <iso_formatted_date>,
                    "number_update_time": <number_of_updates_in_last_30_days>
                },

        }

    Example:
        {
            "Washington,_D.C.":
                {
                    "latest_update_time": "2022-07-23T00:48:00",
                    "number_update_time": 19
                }
        }

    """
    result = {}
    iso_date = ''
    response = requests.get(URL_TEMPLATE.format(title))
    if response.status_code != 200:
        return "Invalid topic has been provided"
    content = BeautifulSoup(response.content, 'html.parser')
    history = content.find(id="pagehistory")
    count = 0
    last_month = datetime.now() - timedelta(days=HISTORY_DAYS_LIMIT)
    for change in history.find_all(class_='mw-changeslist-date'):
        change_date = datetime.strptime(change.text, DATE_FORMAT)
        if not iso_date:
            iso_date = change_date.isoformat()
        if change_date.timestamp() >= last_month.timestamp():
            count += 1
    result[title] = {"latest_update_time": iso_date, UPDATE_FIELD: count}
    return result


def calculate_updates(json_data: dict) -> dict:
    """Transforms JSON into dataframe and
    calculates sum/mean of updates with values > 2

    Input JSON example:
      {
        "Ukraine":
          {
            "latest_update_time": "2022-07-21T01:03:00",
            "number_update_time": 40
          },
        "Washington,_D.C.":
          {
            "latest_update_time": "2022-07-23T00:48:00",
            "number_update_time": 19
          },
        "Movies":
          {
            "latest_update_time": "2018-08-17T20:28:00",
            "number_update_time": 0
          },
        "Football":
          {
            "latest_update_time": "2022-07-17T13:29:00",
            "number_update_time": 6
          }
    }

    Created dataframe:
                           latest_update_time  number_update_time
        Ukraine           2022-07-21T01:03:00                  40
        Washington,_D.C.  2022-07-23T00:48:00                  19
        Movies            2018-08-17T20:28:00                   0
        Football          2022-07-17T13:29:00                   6

    Response:

        {'mean': 21.666666666666668, 'sum': 65}
    """
    df = pd.DataFrame.from_dict(json_data, orient="index")
    filtered_data = df.loc[df[UPDATE_FIELD] > 2]
    mean = filtered_data[UPDATE_FIELD].mean()
    sum_ = filtered_data[UPDATE_FIELD].sum()
    # Converted sum into `int` to avoid issues with data serialization.
    # Pandas returns Int64 that is not supported by default `json` library.
    return {"mean": mean, "sum": int(sum_)}


def read_data(local: bool, filename: str) -> dict:
    """ Read data from S3 bucket or from local JSON file."""
    if local:
        # Read data from the local JSON file.
        try:
            with open(filename, 'r') as f:
                data_json = json.load(f)
        except FileNotFoundError:
            # JSON file does not exist.
            data_json = {}
    else:
        # Read data from S3 bucket.
        try:
            s3_client = boto3.client('s3')
            data_object = s3_client.get_object(Bucket=BUCKET_NAME, Key=filename)
            data_json = json.loads(data_object.get('Body').read().decode('UTF-8'))
        except ClientError:
            # JSON file dost not exists yet.
            data_json = {}
    return data_json


def write_data(data: dict, local: bool, filename: str) -> None:
    """ Write data to a local JSON file or S3 bucket."""
    if local:
        # Write data to local JSON file.
        with open(filename, 'w') as f:
            json.dump(data, f)
    else:
        # Store data to S3 bucket.
        s3_client = boto3.client('s3')
        byte_str = bytes(json.dumps(data).encode('UTF-8'))
        try:
            s3_client.put_object(Bucket=BUCKET_NAME, Key=filename, Body=byte_str)
        except ClientError:
            print(f'Bucket -> {BUCKET_NAME} does not exist.')


def wiki_handler(event, context):
    local = event.get('local', False)
    filename = event.get('filename', JSON_FILE)
    data_json = read_data(local, filename)
    params = event.get('queryStringParameters', {})
    title = params.get('title', '')
    result = parse_wiki(title)
    data_json.update(result)
    calculated_updates = calculate_updates(data_json)
    write_data(data_json, local, filename)
    data_json.update(calculated_updates)
    return {'statusCode': 200, 'body': json.dumps(data_json)}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Local execution guide")
    parser.add_argument('--local',
                        dest="local",
                        type=bool,
                        default=False,
                        help="Add a flag for local execution .")
    parser.add_argument('--filename',
                        help="Provide name for resulting JSON file. (default: parsed_wiki.json)",
                        dest="filename",
                        type=str,
                        default="parsed_wiki.json")
    parser.add_argument('--title',
                        dest="title",
                        type=str,
                        help="Title for Wikipedia search")
    args = parser.parse_args()
    local, filename, title = args.local, args.filename, args.title
    lambda_res = wiki_handler({
                                "queryStringParameters":
                                  {
                                    'title': title,
                                  },
                                "local": local
                              }, '')
    print(lambda_res)

