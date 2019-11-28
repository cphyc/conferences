import bs4
import requests
import dateparser
from tinydb import TinyDB, Query, where
from tinydb_serialization import SerializationMiddleware, Serializer

import sys
import os
from datetime import datetime
import argparse
import re

NOW = datetime.now()

# Serialize/deserialize dates
class DateTimeSerializer(Serializer):
    OBJ_CLASS = datetime  # The class this serializer handles

    def encode(self, obj):
        return obj.strftime('%Y-%m-%dT%H:%M:%S')

    def decode(self, s):
        return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')

serialization = SerializationMiddleware()
serialization.register_serializer(DateTimeSerializer(), 'TinyDate')

# Parse input arguments as dates
class DateArgAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs):
        super(DateArgAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        s = ' '.join(values)
        date = dateparser.parse(s)
        setattr(namespace, self.dest, date)

# Cut long strings around words
def cut_long_str(s, maxlen=40):
    # This matches up to maxlen caracters, splitting at the last non-whitespace
    WORD_RE = re.compile('(.{,%d}\S)\s+.*$' % (maxlen-2))
    s = s.strip()

    if len(s) < maxlen:
        return s
    else:
        return WORD_RE.match(s).group(1) + '…'


def print_boxed(header):
    rows, columns = (int(_) for _ in os.popen('stty size', 'r').read().split())
    N = len(header)
    nspace = (columns - N - 2) // 2
    header = '║' + ' '*nspace + header + ' '*nspace + '║'
    print('╔' + '═'*(len(header)-2) + '╗')
    print(header)
    print('╚' + '═'*(len(header)-2) + '╝')


def get_and_update():
    # Request conference list
    print('Getting conference data from conference-service.com')
    r = requests.get('https://www.conference-service.com/conferences/gravitation-and-cosmology.html')
    r.encoding = r.apparent_encoding
    if not r.ok:
        sys.exit(1)

    # Parse HTML
    print('Extracting conferences metadata')
    soup = bs4.BeautifulSoup(r.text, 'lxml')
    evnt_list = soup.find('div', class_='evnt_list')

    # Extract conferences
    conferences = []
    for evnt in evnt_list.find_all('div', class_='evnt'):
        title = evnt.find(class_='sub_title').text.strip()
        timeloc = evnt.find(class_='dates_location').find(class_='conflist_value').text
        time, loc = (_.strip() for _ in timeloc.split('•'))
        abstract_label = evnt.find(text='Abstract:')
        if abstract_label is not None:
            abstract = abstract_label.find_next(class_='conflist_value').text.strip()
        else:
            abstract = ''
        id = int(evnt.find(text='Event listing ID:').find_next(class_='conflist_inline').text)
        url = evnt.find(text='Event website:').find_next('a').href

        if ' - ' in time:
            start, end = time.split(' - ')
        else:
            start, end = time, time

        start, end = (dateparser.parse(_) for _ in (start, end))

        conf = dict(
            title=title,
            abstract=abstract,
            loc=loc,
            start=start,
            end=end,
            online_id=id,
            url=url
        )

        conferences.append(conf)

    # Open database
    print('Storing in local database')
    db = TinyDB('conferences_db.json', storage=serialization)

    # Store in database
    Conf = Query()
    new_conferences = []
    for conf in conferences:
        q = Conf.online_id == conf['online_id']
        if len(db.search(q)) == 0:
            new_conferences.append(conf)
            conf['date_added'] = NOW
            db.insert(conf)
        else:
            db.update(conf, q)

    header = '%s NEW CONFERENCES ADDED' % len(new_conferences)
    print_boxed(header)
    
    print_conferences(new_conferences)


def list_conferences(start=None, end=None):
    """Print all conferences.
    
    Arguments:
    ----------
    start, end : datetime object | None
        start and end date for query.
    """
    db = TinyDB('conferences_db.json', storage=serialization)

    Conf = Query()
    
    q = Conf
    if start is not None:
        q &= Conf.end >= start
    if end is not None:
        q &= Conf.start <= end

    now = datetime.now()
    conferences = sorted(db.search(q), key=lambda c: now-c['start'])
    print_conferences(conferences)

def print_conferences(conferences):
    new_addition = []
    dtmax = 3600*24  # 1 week
    for conf in conferences:
        new_addition.append((NOW - conf['date_added']).total_seconds() < dtmax)

    def print_helper(conf):
        conf['title'] = cut_long_str(conf['title'])
        conf['start'] = conf['start'].strftime('%d/%m')
        conf['end'] = conf['end'].strftime('%d/%m/%Y')
        conf['notify'] = '  ' if (NOW - conf['date_added']).total_seconds() > dtmax else '* '
        print('{notify}{title:40s}: {start} to {end} @ {loc}'.format(**conf))
    
    for new, conf in zip(new_addition, conferences):
        if not new:
            print_helper(conf)
    print()
    print('NEW ADDITIONS:')
    for new, conf in zip(new_addition, conferences):
        if new:
            print_helper(conf)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Interact with conferences from conference-service.com')
    parser.add_argument('-u', '--update', action='store_true', help='Update database.')

    parser.add_argument('-f', '--from', dest='start', action=DateArgAction, nargs='+', default=NOW, 
                        help='Earliest date when printing (default: now).')
    parser.add_argument('-t', '--to', dest='end', action=DateArgAction, nargs='+', default=None,
                        help='Latest date when printing.')
    parser.add_argument('-s', '--silent', action='store_true', help='Do not print conferences.')

    args = parser.parse_args()

    if args.update:
        get_and_update()

    if not args.silent and not args.update:
        list_conferences(args.start, args.end)