# Sample Lambda Function to post notifications to a Chime room when an AWS Health event happens
from __future__ import print_function
import json
import logging
import os
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Setting up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# helper functions

# although markdown has a number of special chars (\\`*_{}[]()#+-.!) the chime
# android app seems to have a problem with just underscores (the desktop app
# doesn't), so we put anything contaning underscores into a markdown code block
def escape_markdown_special_chars(s):
    if type(s) is list:
        l = []
        for i in s:
            l.append(escape_markdown_special_chars(i))
        return l
    elif s is not None:
        if s.count('_') > 0:
            return '`{}`'.format(s)
        else:
            return s
    else:
        return None

def val(d, key):
    if key in d:
        return d[key]
    else:
        return None

# create a url from a cloudformation parameter, if it was specified (not blank)
def optional_url(env_var_url, data):
    if env_var_url in os.environ and os.environ[env_var_url]:
        raw_url = os.environ[env_var_url]
        return raw_url.format(**data)
    else:
        return None

# main function
def lambda_handler(event, context):
    detail = event['detail']
    d = {
        'account': val(event, 'account'),
        'description': detail['eventDescription'][0]['latestDescription'],
        'endTime': val(detail, 'endTime'),
        'eventArn': val(detail, 'eventArn'),
        'eventTypeCategory': val(detail, 'eventTypeCategory'),
        'eventTypeCode': val(detail, 'eventTypeCode'),
        'resources': val(event, 'resources'),
        'region': val(event, 'region'),
        'service': val(detail, 'service'),
        'startTime': val(detail, 'startTime')
    }
    # use raw values to construct optional urls 
    event_arn_url = optional_url('EVENTURL', d)
    account_url = optional_url('ACCOUNTURL', d)
    # escape raw values before constructing the markdown message
    #for k in d:
    #    d[k] = escape_markdown_special_chars(d[k])
    # add urls
    if event_arn_url:
        d['eventArnUrl'] = '[{}]({})'.format(d['eventArn'], event_arn_url)
    else:
        d['eventArnUrl'] = '{}'.format(d['eventArn'])
    if account_url:
        d['accountUrl'] = '[{}]({})'.format(d['account'], account_url)
    else:
        d['accountUrl'] = '{}'.format(d['account'])
    # construct the message
    message = '''/md
{description}
* ARN: {eventArnUrl}
* Account: {accountUrl}
* Region: {region}
* Service: {service}
* Event type code: `{eventTypeCode}`
* Event type category: {eventTypeCategory}
* Start time: {startTime}
* End time: {endTime}
* Resources: {resources}
    '''.format(**d)
    chime_message = {'Content': message}
    logger.info(str(chime_message))
    if detail['eventTypeCategory'] == 'investigation':
        webhookurl = str(os.environ['CHIMEWEBHOOKINVESTIGATIONEVENTS'])
    else:
        webhookurl = str(os.environ['CHIMEWEBHOOKOTHEREVENTS'])
    req = Request(webhookurl, data=json.dumps(chime_message).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        response = urlopen(req)
        response.read()
    except HTTPError as e:
        logger.error('Request failed : %d %s', e.code, e.reason)
    except URLError as e:
        logger.error('Server connection failed: %s', e.reason)