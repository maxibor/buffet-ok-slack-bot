import argparse
from slackclient import SlackClient
import datetime
from dateutil.parser import parse
import requests
import pandas as pd
from googletrans import Translator
import time
from bs4 import BeautifulSoup
import requests


def _get_args():
    '''This function parses and return arguments passed in'''
    parser = argparse.ArgumentParser()
    parser.add_argument('bot_token', help="Bot User OAuth Access Token")
    args = parser.parse_args()
    token = args.bot_token
    return(token)


def is_date(string):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        thedate = parse(string, dayfirst=True).strftime("%d.%m.%Y")
        return(thedate)
    except:
        return False


def get_menu_dict(url):
    food = {}
    try:
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        choices = soup.find_all('fieldset')
        for day in choices[1:]:
            theday = day.select('legend')
            labels = day.select('label')
            thisday = theday[0].string.split()[1]
            food[thisday] = []

            for label in labels:
                thefood = label.string
                foodtype = thefood.split()[0]
                theprice = thefood.split()[1]
                thewhat = thefood.split("-")[1]
                try:
                    food[thisday].append(
                        {'type': foodtype, 'price': theprice, 'what': thewhat})
                except:
                    continue
        return(food)
    except:
        return(food)


def date_of_day():
    return(str(datetime.datetime.today().date().strftime('%d.%m.%Y')))


def get_food_day(menu_dict, theday, lang='en'):
    if theday in menu_dict.keys():
        res = f"Menu for the {theday}:\n"
        for i in range(0, 2):
            if lang == 'de':
                res += f"- {menu_dict[theday][i]['type']}: {menu_dict[theday][i]['what']} - {menu_dict[theday][i]['price']}\n"
            elif lang == 'en':
                res += f"- {translate(menu_dict[theday][i]['type'])}: {translate(menu_dict[theday][i]['what'])} - {menu_dict[theday][i]['price']}\n"
        return(res)
    else:
        return(f'No menu available for the {theday}')


def translate(de_text):
    translator = Translator()
    tr = translator.translate(de_text, src='de')
    return(tr.text.capitalize())


def post_annotation(token, text=None, channel='bot', response_to=''):
    """
    Post a message into a channel.
    :param token: Slack API token
    :param text: text to post. If None, the text is the information about the annotations
    :param channel: channel where the bot post the message
    :param reponse_to: if we want to mention some one
    """
    # connection
    slack_client = SlackClient(token)
    # Mention someone (need an user ID, not an username)
    if response_to != '':
        response_to = '<@%s>' % response_to
    # Pre-defined message
    if not text:
        text = f"""
To get the menu of the day, please call me: @buffet-ok menu
To get the menu of the day in English: @buffet-ok menu english
To get the menu for a specific date: @buffet-ok menu dd.mm.yyyy
        """

    # Post message
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=text)


def parse_bot_commands(slack_events):
    """
    Handling the posts and answer to them
    : param slack_events: slack_client.rtm_read()
    """

    help_text = f"""
To get the menu of the day: @buffetok menu
To get the menu of the day in English: @buffet-ok menu english
To get the menu for a specific date: @buffet-ok menu dd.mm.yyyy
        """
    channel = 'buffet-ok'
    URL1 = "https://www.buffet-ok.de/mittagessen-bestellen/mittagessen-bestellen-1.html"
    URL2 = "https://www.buffet-ok.de/mittagessen-bestellen/mittagessen-bestellen-2.html"

    for event in slack_events:
        # only message from users
        if event['type'] == 'message' and not 'subtype' in event:
            # get the user_id and the text of the post
            user_id, text_received, channel = event['user'], event['text'], event['channel']
            text_received = text_received.split(" ")
            # the bot is activated only if we mention it
            if f"<@{buffetbot_id}>" in text_received:
                print(
                    f"user_id: {user_id}, channel: {channel}, text: {text_received}")
                # Activate help if 'help' or 'sos' in the post
                if any([k in text_received for k in ['help', 'sos']]):
                    post_annotation(TOKEN, text=help_text, channel=channel)

                elif 'menu' in text_received:
                    menu_week1 = get_menu_dict(URL1)
                    menu_week2 = get_menu_dict(URL2)
                    menu = {**menu_week1, **menu_week2}
                    if any([w in text_received for w in ['en', 'english']]):
                        for i in text_received:
                            if is_date(i):
                                thedate = is_date(i)
                                break
                            else:
                                thedate = date_of_day()
                        menu_text = get_food_day(menu, thedate, 'en')
                    else:
                        for i in text_received:
                            if is_date(i):
                                thedate = is_date(i)
                                break
                            else:
                                thedate = date_of_day()
                        menu_text = get_food_day(menu, thedate, 'de')
                    post_annotation(TOKEN, text=menu_text, channel=channel)

                # Else help menu
                else:
                    post_annotation(TOKEN, channel=channel)


if __name__ == '__main__':
    TOKEN = _get_args()

    slack_client = SlackClient(TOKEN)
    if slack_client.rtm_connect(auto_reconnect=True):
        print("Starter Bot connected and running!")
        buffetbot_id = slack_client.api_call('auth.test')['user_id']
        print(buffetbot_id)
        while True:
            try:
                parse_bot_commands(slack_client.rtm_read())
                time.sleep(1)
            except:
                time.sleep(10)
    else:
        print("Connection failed. Exception traceback printed above.")
