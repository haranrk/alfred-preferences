#!/usr/bin/python
# encoding: utf-8
#
# Copyright (c) 2020 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2020-05-01
#

"""video-conferences.py [options] [<query>]

Alfred Script Filter to show ongoing and upcoming video conferences
extracted from your calendar events.

Usage:
    video-conferences.py [<query>]
    video-conferences.py -h
    video-conferences.py --reload [--notify]
    video-conferences.py --force-reload
    video-conferences.py --calendar <name> --event <id>

Options:
    --calendar=<name>   calendar event belongs to
    --event=<id>        event to show in Calendar.app
    --reload            refresh cached list of events
    --notify            show notification when refresh is complete
    --force-reload      force refresh cached list of events
    -h, --help          show this message and exit

"""

from __future__ import print_function, absolute_import


from datetime import datetime
import json
import os
import re
import sys

from docopt import docopt
from workflow import Workflow3, ICON_INFO, ICON_WARNING
from workflow.background import run_in_background, is_running
from workflow.util import run_command, run_trigger

from icons import Icons


# Configuration loaded from workflow/environment variables
MAX_CACHE_AGE = 600  # how long to cache events for
LOOKAHEAD_DAYS = 7  # how many days' events to load
ACCOUNTS = set()  # names of accounts to search
CALENDARS = set()  # names of calendars to search
REGEXES = []  # regular expressions matching video-conference URLs

log = None


def load_config():
    """Load workflow configuration from environment."""
    global MAX_CACHE_AGE, LOOKAHEAD_DAYS, ACCOUNTS, CALENDARS, REGEXES

    MAX_CACHE_AGE = int(os.getenv('max_cache_seconds') or MAX_CACHE_AGE)
    log.debug('max_cache_age=%r', MAX_CACHE_AGE)
    LOOKAHEAD_DAYS = int(os.getenv('lookahead_days') or LOOKAHEAD_DAYS)
    log.debug('lookahead_days=%r', LOOKAHEAD_DAYS)

    for k, v in os.environ.items():
        if k.startswith('account_') and v:
            ACCOUNTS.add(v)
            log.debug('account=%r', v)

        elif k.startswith('calendar_') and v:
            CALENDARS.add(v)
            log.debug('calendar=%r', v)

        elif k.startswith('regex_'):
            try:
                rx = re.compile(v, re.IGNORECASE)
                REGEXES.append(rx)
                log.debug('regex=%s', v)
            except Exception as err:
                log.error('invalid regex: %r: %s', v, err)
                continue


def parse_date(s):
    """Convert date string return from CalendarEvents.scpt to `datetime`.

    Args:
        s (unicode): Date string from CalendarEvents.scpt

    Returns:
        datetime.datetime: Parsed date in local time

    """
    return datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')


def load_events():
    """Retrieve events from Calendar database.

    Returns:
        dict: Parsed data from CalendarEvents.scpt

    """
    cmd = ['/usr/bin/osascript', 'CalendarEvents.scpt', LOOKAHEAD_DAYS]
    data = json.loads(run_command(cmd))
    if 'events' in data:
        for event in data['events']:
            event['start_date'] = parse_date(event['start_date'])
            event['end_date'] = parse_date(event['end_date'])
            log.debug('event=%r', event)

    return data


def generate_icons(events):
    """Save icons for events to cache."""
    icons = Icons(wf.cachefile('icons'))
    colours = set()
    for event in events:
        colours.add(tuple(event['colour']))

    for colour in colours:
        icons.create_icon(colour)


def event_filter(event):
    """Filter out unwanted events.

    Ignore event if it's finished, from an unwanted account or calendar,
    or doesn't contain a recognised video-conference URL.

    Args:
        event (dict): Event dictionary.

    Returns:
        Bool: `True` if event is wanted, `False` if not.

    """
    if event['end_date'] < datetime.now():
        return
    if ACCOUNTS and event['account'] not in ACCOUNTS:
        return
    if CALENDARS and event['calendar'] not in CALENDARS:
        return

    candidates = (event['url'], event['location'], event['notes'])
    for s in candidates:
        for rx in REGEXES:
            m = rx.search(s)
            if m:
                event['url'] = m.group(0)
                return True


def do_reload(notify):
    """Refresh events cache."""
    log.debug('[cache] fetching events from Calendars ...')
    data = load_events()
    wf.cache_data('events', data)

    if data.get('error'):
        log.error('[cache] failed to retrieve events: %s', data['error'])

    if data.get('events'):
        generate_icons(data['events'])

    if notify:
        run_trigger('notify')


def do_force_reload():
    """Run reload in background so Script Filter is aware it's running."""
    log.info('force reloading cache ...')
    if not is_running('reload'):
        run_in_background('reload', [sys.argv[0], '--reload', '--notify'])


def do_show_event(calendar_name, event_id):
    """Show specified event in Calendar.app.

    Args:
        calendar_name (unicode): Name of calendar
        event_id (unicode): UID of event

    """
    run_command(['/usr/bin/osascript', 'ShowEvent.scpt', calendar_name, event_id])


def main(wf):
    """Run script."""
    args = docopt(__doc__, argv=wf.args)
    log.debug('args=%r', args)
    load_config()

    # reveal an event in Calendar.app
    if args['--calendar']:
        return do_show_event(args['--calendar'], args['--event'])

    # reload events from Calendar database
    if args['--reload']:
        return do_reload(args['--notify'])

    # this is a "wrapper" command to ensure --reload is always run
    # as a background job the Script Filter knows about
    if args['--force-reload']:
        return do_force_reload()

    # search events
    query = args['<query>'] or u''

    # ensure Script Filter is executed again if cache is being updated
    reloading = is_running('reload')
    if not wf.cached_data_fresh('events', MAX_CACHE_AGE) and not reloading:
        run_in_background('reload', [sys.argv[0], '--reload'])
        reloading = True

    if reloading:
        wf.rerun = 0.2

    data = wf.cached_data('events', max_age=0)
    if not data:
        if reloading:
            wf.add_item(u'Loading Events…',
                        u'Results should appear momentarily',
                        icon=ICON_INFO)
        else:
            wf.add_item(u'No Data',
                        u'Workflow could not load calendar data',
                        icon=ICON_WARNING)
        wf.send_feedback()
        return

    # If CalendarEvents.scpt returned an error (typically because access
    # to user's calendars was denied), show it to user
    if data.get('error'):
        raise RuntimeError(data['error'])

    # Remove unwanted events
    events = filter(event_filter, data['events'])
    log.debug('%d/%d event(s) in specified accounts & calendars are '
              'video conferences', len(events), len(data['events']))

    if query:
        events = wf.filter(query, events, key=lambda d: d['title'])

    icons = Icons(wf.cachefile('icons'))
    for d in events:
        subtitle = u'{}–{} on {} // {} ({})'.format(
            d['start_date'].strftime('%H:%M'),
            d['end_date'].strftime('%H:%M'),
            d['start_date'].strftime('%Y-%m-%d'),
            d['calendar'], d['account'])

        it = wf.add_item(d['title'], subtitle, arg=d['url'], valid=True,
                         icon=icons.get_icon(d['colour']))
        it.setvar('calendar_name', d['calendar'])
        it.setvar('event_id', d['uid'])

    # add "reload" action if query matches 'reload'
    if len(query) > 1 and 'reload'.startswith(query):
        wf.add_item('Reload Events',
                    'Update cached events from Calendar database',
                    arg='reload',
                    icon='reload.png',
                    valid=True)

    warning = 'No Matching Events' if query else 'No Video Conferences'
    wf.warn_empty(warning)
    wf.send_feedback()


if __name__ == '__main__':
    wf = Workflow3()
    log = wf.logger
    wf.run(main)
