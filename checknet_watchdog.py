#!/usr/local/bin/python3.6

"""
    internet connection monitor and alert script

    used to watch internet connection status and send pushover notifications
"""
import os
import sys
import logging

import subprocess

sys.path.insert(0, '/root/galaxymodules')
import proctools

__author__ = "Ian Perry"
__copyright__ = "Copyright 2018, Galaxy Media"
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "Ian Perry"
__email__ = "ianperry99@gmail.com"

log = logging.getLogger('watchdog')

lockfile = '/var/tmp/checknet.lock'


def main():
    log.setLevel(logging.DEBUG)
    log_format = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')

    log_handler = logging.StreamHandler()
    log_handler = logging.FileHandler('/root/connection.log')
    log_handler.setFormatter(log_format)
    log.addHandler(log_handler)

    if os.path.isfile(lockfile):
        lock_handle = open(lockfile, 'r')
        filepid = lock_handle.read()
        if filepid != None: 
            if True: #proctools.ispid_running(int(filepid)):
                exit(0)
           
            else:
                log.warning('checknet script is not running.  restarting script')
                try:
                    subprocess.Popen(['/root/andromedatools/checknet.py', '--daemon',
                                  '-f', '/root/connection.log'], shell=False)
                except:
                    log.error('Error trying to execute checknet script')
                    exit(1)
                else:
                    exit(0)
        else:
            log.warning('checknet script is not running.  restarting script')
            try:
                subprocess.Popen(['/root/andromedatools/checknet.py', '--daemon',
                                  '-f', '/root/connection.log'], shell=False)
            except:
                log.error('Error trying to execute checknet script')
                exit(1)
            else:
                exit(0)


if __name__ == '__main__':
    main()
