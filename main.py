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
import multiprocess as mp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

handler = logging.FileHandler('sb_notif.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

mongo_client = MongoClient()

smtp_server = smtplib.SMTP()


def email_connect(user, pw):
    def dec(func):
        def wrapper(*args, **kwargs):
            smtp_server.connect('smtp.gmail.com', 587)
            smtp_server.starttls()
            smtp_server.login(user, pw)
            func(*args, **kwargs)
            smtp_server.quit()

        return wrapper

    return dec


def get_threads():
    threads = mongo_client['sb_notif_data']['threads']
    info = threads.find()
    return info


def get_email(user):
    mongo_client2 = MongoClient()
    users = mongo_client2['sb_notif_data']['users']
    filt = {
        'name': user
    }
    info = users.find_one(filt)
    return info.get('email')


def update_thread(thread, new_url):
    mongo_client2 = MongoClient()
    threads = mongo_client2['sb_notif_data']['threads']
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
        new_url = sub_elems[len(sub_elems) - 1].values()[0]
        full_url = join_url(url, new_url)
        return full_url
    except:
        return url


def get_latest(url):
    try:
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
    except:
        log_stack_trace()


def join_url(orig_url, new_url):
    base = orig_url[:len(orig_url) - len(new_url)]
    return base + new_url


def is_latest(url):
    return url == get_latest(url)


@email_connect(USER, PW)
def process_thread(thread):
    thread_name = thread.get('thread')
    thread_url = thread.get('url')
    logger.info("Checking for latest on %s" % thread_name)
    latest = get_latest(thread_url)
    if latest != thread_url:
        logger.info("Found new thread for %s: %s" % (thread_name, latest))

        emails = [email_user_update(user, thread_name, latest) for user in thread.get('users')]

        if all(emails):
            update_thread(thread, latest)


def check_threads():
    threads = list(get_threads())
    with mp.Pool(len(threads)) as p:
        p.map(process_thread, threads)


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
        logger.info("Attempt #%s" % (i,))
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


def wide_msg(s, wanted_length=80):
    padded_str = '|: %s :|' % s
    s_len = len(padded_str)
    left_over = wanted_length - s_len
    l_side_len = int(left_over / 2)
    r_side_len = left_over - l_side_len
    l_side = '=' * l_side_len
    r_side = '=' * r_side_len
    return l_side + padded_str + r_side


if __name__ == "__main__":
    while True:
        try:
            logger.info(wide_msg('Starting Check'))
            check_threads()
            logger.info(wide_msg('Finished Check'))
            logger.info('')
        except Exception as err:
            log_stack_trace()

        time_to_sleep = 60 * 60
        time.sleep(time_to_sleep)
