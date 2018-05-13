#!/usr/local/bin/python3.6

"""
    internet connection monitor and alert script

    used to watch internet connection status and send pushover notifications
"""

import os
import sys
import time
import fcntl
from datetime import datetime
import logging

import argparse

sys.path.insert(0, '/root/galaxymodules')
from gentools import *
from nettools import *

__author__ = "Ian Perry"
__copyright__ = "Copyright 2018, Galaxy Media"
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "Ian Perry"
__email__ = "ianperry99@gmail.com"

log = logging.getLogger()
configfile = '/etc/galaxymediatools.cfg'
config = ConfigParser()
config.read(configfile)

def main():
    parser = argparse.ArgumentParser(prog='checknet')
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(__version__))
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output (info)')
    parser.add_argument('-vv', '--debug', action='store_true', help='full verbose output (debug)')
    parser.add_argument('--daemon', action='store_true', help='daemonize')
    parser.add_argument('--host', default='1.1.1.1', help='host to check. default: 1.1.1.1')
    parser.add_argument('--latency', default=200, help='high latency threshold in ms. default: 200')
    parser.add_argument('--count', default=5, help='number of down counts before alerting. default: 5')
    parser.add_argument('--sleep', default=1, help='sleep time between checks in minutes. default: 1')
    parser.add_argument('-f', '--logfile', help='file to log output to. default: log to console (no file logging)')
    args = parser.parse_args()

    if args.debug is True:
        log.setLevel(logging.DEBUG)
    elif args.verbose is True:
        log.setLevel(logging.INFO)
    else:
        log.setLevel(logging.WARNING)

    log_format = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')

    if args.logfile is None:
        log_handler = logging.StreamHandler()
    else:
        log_handler = logging.FileHandler(args.logfile)
    log_handler.setFormatter(log_format)
    log.addHandler(log_handler)

    lockfile = '/var/tmp/checknet.lock'
    if not os.path.isfile(lockfile):
        os.mknod(lockfile, mode=0o600)
    lock_handle = open(lockfile, 'w')
    try:
        fcntl.lockf(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        log.warning('Process is already running. Can only run once. Exiting')
        exit(5)
    except:
        log.exception('General error trying to lock process to file {}. exiting.'.format(lockfile))
        exit(1)
    else:
        pid = str(os.getpid())
        log.info('Process has been locked to file {} with PID [{}]'.format(lockfile, pid))
        lock_handle.write(pid)
        lock_handle.flush()

    daemonize = args.daemon
    check_host = args.host
    pushover_app_key = config.get('pushover', 'connection_key')
    lagthreshold = args.latency
    downthreshold = args.count
    sleeptime = args.sleep

    log.debug('Checknet script starting, check host is: {}'.format(check_host))
    if args.daemon is True:
        log.info('Executed in daemon mode. Will continue forever.')

    losscount = 0
    lagcount = 0
    downcount = 0
    downalert = 0
    lossalert = 0
    lagalert = 0
    waitingrestore = 0
    dreason = 'None'

    while True:
        try:
            """ perform the ping check and determine results """
            presults = ping(check_host)
            if presults.ret_code == 0:
                if presults.packet_lost == 0:
                    if float(presults.avg_rtt) < lagthreshold:
                        losscount = 0
                        lagcount = 0
                        downcount = 0
                        if waitingrestore == 1:
                            elapsed = elapsedTime(downtime, datetime.now())
                            didsend = pushover(pushover_app_key, 'Network Restored',
                                               'Network connection was {} for {}'.format(dreason, elapsed))
                            if didsend is True:
                                waitingrestore = 0
                    elif float(presults.avg_rtt) >= lagthreshold:
                        lagcount += 1
                        log.warning('Lag threshold exceeded {} ms Count {}/{}'
                                    .format(presults.avg_rtt, lagcount, downthreshold))
                elif presults.packet_lost > 0:
                    losscount += 1
                    log.warning('Packet Loss Detected {} pkts Count {}/{}'
                                .format(presults.packet_lost, losscount, downthreshold))
            else:
                downcount += 1
                log.warning('Network Down Detected Count {}/{}'.format(downcount, downthreshold))
            """ process results (figure out if an alert is needed) """
            if downcount == downthreshold:
                downalert = 1
                downtime = datetime.now()
                dreason = 'Down'
                log.warning('Down count thresold reached, sending alert')
            elif losscount == downthreshold:
                lossalert = 1
                downtime = datetime.now()
                dreason = "Loosing Packets"
                log.warning('Packet loss count thresold reached, sending alert')
            elif lagcount == downthreshold:
                lagalert = 1
                downtime = datetime.now()
                dreason = "in High Latency"
                log.warning('High latency thresold reached, sending alert')
            """ process alerts """
            if downalert == 1:
                showtime = downtime.strftime('%I:%M %p %m-%d-%y')
                didsend = pushover(pushover_app_key, 'Network Connection Down',
                                   'The network reported DOWN at {}'.format(showtime))
                if didsend is True:
                    downalert = 0
                    waitingrestore = 1
            elif lossalert == 1:
                showtime = downtime.strftime('%I:%M %p %m-%d-%y')
                didsend = pushover(pushover_app_key, 'Packet Loss Detected.',
                                   'The network reported PACKET LOSS at {}'.format(showtime))
                if didsend is True:
                    lossalert = 0
                    waitingrestore = 1
            elif lagalert == 1:
                showtime = downtime.strftime('%I:%M %p %m-%d-%y')
                didsend = pushover(pushover_app_key, 'High Latency Detected.',
                                   'The network reported HIGH LATENCY at {}'.format(showtime))
                if didsend is True:
                    lagalert = 0
                    waitingrestore = 1
        except Exception as e:
            log.exception('Exception occured: %s' % str(e))
        if daemonize is False:
            log.info('Program exiting because was executed without --daemon')
            exit()
        log.info('Waiting {} minutes until next check...'.format(sleeptime))
        time.sleep(sleeptime * 60)


if __name__ == '__main__':
    main()
