from pyquery import PyQuery as pq
import smtplib
from email.message import EmailMessage
from pymongo import MongoClient
import time
from user_info import USER, PW
import re
import logging
import datetime
import traceback
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

handler = logging.FileHandler('sb_notif.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

mongo_client = MongoClient()

smtp_server = smtplib.SMTP('smtp.gmail.com', 587)


def get_threads():
    threads = mongo_client['sb_notif_data']['threads']
    info = threads.find()
    return info


def get_email(user):
    users = mongo_client['sb_notif_data']['users']
    filt = {
        'name': user
    }
    info = users.find_one(filt)
    return info.get('email')


def update_thread(thread, new_url):
    threads = mongo_client['sb_notif_data']['threads']
    thread['url'] = new_url
    thread['last_updated'] = datetime.datetime.now()
    threads.save(thread)


def check_is_vote(url):
    doc = pq(url=url)
    next_elem = doc('.label')[0]
    elem_text_list = next_elem.itertext()
    reg = re.compile('[Vv]ote')
    for text in elem_text_list:
        matched = re.search(reg, text)
        if matched is not None:
            return True
    return False


def get_next(url):
    try:
        doc = pq(url=url)
        next_elem = doc('.next')
        sub_elems = next_elem.children()
        new_url = sub_elems[0].values()[0]
        full_url = join_url(url, new_url)
        return full_url
    except:
        return url


def get_latest(url):
    second_last = ''
    last_url = url
    next_url = get_next(url)
    while next_url != last_url:
        second_last = last_url
        last_url = next_url
        next_url = get_next(next_url)

    if check_is_vote(next_url):
        return second_last
    else:
        return next_url


def join_url(orig_url, new_url):
    base = orig_url[:len(orig_url) - len(new_url)]
    return base + new_url


def is_latest(url):
    return url == get_latest(url)


def check_threads():
    threads = get_threads()
    for thread in threads:
        thread_name = thread.get('thread')
        thread_url = thread.get('url')
        logger.info("Checking for latest on %s" % thread_name)
        latest = get_latest(thread_url)
        if latest != thread_url:
            logger.info("Found new thread for %s: %s" % (thread_name, latest))
            smtp_server.starttls()
            smtp_server.login(USER, PW)
            emails = [email_user_update(user, thread_name, latest) for user in thread.get('users')]
            smtp_server.quit()

            if all(emails):
                update_thread(thread, latest)


def email_user_update(user, thread_name, new_thread_url, attempts=10):
    with open('email_template', 'r') as fp:
        template = fp.read()

    user_name = user
    msg = EmailMessage()
    msg.set_content(template % (user_name, thread_name, new_thread_url))
    msg['Subject'] = "New Update for %s" % thread_name
    msg['To'] = get_email(user)
    msg['From'] = "%s@gmail.com" % USER
    for i in range(1, attempts + 1):
        logger.info("Attempt #%s" % (i, ))
        try:
            smtp_server.send_message(msg)
            logger.info("Sent message:\n%s" % msg)

            return True
        except Exception as e:
            log_stack_trace()
    return False


def get_users():
    users = mongo_client['sb_notif_data']['users']
    info = users.find()
    return info


def log_stack_trace():
    logger.warning(traceback.format_exc())


if __name__ == "__main__":
    while True:
        try:
            check_threads()
            time_to_sleep = 60 * 60
            time.sleep(time_to_sleep)
        except Exception as err:
            log_stack_trace()
