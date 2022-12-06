import datetime
import json

import requests

import lib.ddb as ddb
import lib.utils as utils


def update_exchange_data_handler(event, context):
    """This Lambda function fetches the data from ecb and store it into dynamodb with last day change

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
        Exchange rates in json format
    """
    try:
        response = requests.get('https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml')
        if response.status_code == 200:
            exchange_rates_xml = response.text
            exchange_rates_dict = utils.xml_to_dict(exchange_rates_xml)
            exchange_rates_with_diff = utils.calculate_rate_diff(exchange_rates_dict, list(exchange_rates_dict)[0],
                                                                 list(exchange_rates_dict)[1])
            ddb.ddb_put_items(ddb_table_name='currency_exchange', data_items_list=exchange_rates_with_diff)

        return {
            "statusCode": 200,
            "body": json.dumps(exchange_rates_with_diff),
        }

    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': str(e)})
        }


def daily_exchange_rate_handler(event, context):
    """This Lambda function return daily rates of ecb from dynamodb

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
        Daily Exchange rates in json format
    """
    try:
        date = datetime.date.today()
        if datetime.datetime.utcnow().time() < datetime.time(17, 30):
            # exchange updates their rates on around 4:15 pm CET so if current time is less
            # than 4:15pm CET then fetch the rates of the last date
            date = datetime.date.today() - datetime.timedelta(days=1)
        if date.strftime("%A") in ['Saturday', 'Sunday']:
            # as Exchange rates are not update on Saturday and Sunday, so it will return the Friday rates
            date = get_last_friday()

        res, exchange_rates = ddb.ddb_get_item('exchangeRates', ('date', date.strftime('%Y-%m-%d')
                                                                 ))
        return {
            'statusCode': 200,
            'body': json.dumps(exchange_rates)
        }
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': str(e)})
        }


def get_last_friday():
    """
    This function return the date of last Friday
    :return: date object
    """
    now = datetime.datetime.now()
    closest_friday = now + datetime.timedelta(days=(4 - now.weekday()))
    return (closest_friday if closest_friday < now
            else closest_friday - datetime.timedelta(days=7))
