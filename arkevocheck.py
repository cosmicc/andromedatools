#!/usr/local/bin/python3.6

"""
    ark: survival evolved evolution event monitor

    checks for ark: survival evolved evolution events and sends pushover alerts
"""

import sys
import os
import logging
from shutil import copyfile
from configparser import ConfigParser

import urllib.request
import argparse

sys.path.insert(0, '/root/galaxymodules')
import gentools

__author__ = "Ian Perry"
__copyright__ = "Copyright 2018, Galaxy Media"
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "Ian Perry"
__email__ = "ianperry99@gmail.com"

configfile = '/etc/galaxymediatools.cfg'
config = ConfigParser()
config.read(configfile)
log = logging.getLogger()


def main():
        parser = argparse.ArgumentParser(prog='arkevocheck')
        parser.add_argument('--version', action='version', version='%(prog)s {}'.format(__version__))
        parser.add_argument('-v', '--verbose', action='store_true', help='verbose output (info)')
        parser.add_argument('-vv', '--debug', action='store_true', help='full verbose output (debug)')
        parser.add_argument('-p', '--path', default='/home/ark/', help='path to use, defaults to /home/ark/')
        parser.add_argument('-f', '--file', default='arkevoevent.dat', help='dat file to use, defaults to arkevoevent.dat')
        parser.add_argument('-l', '--logfile', help='file to log output to. default: log to console (no file logging)')
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

        global ARKPATH
        global OLDDATFILE
        global NEWDATFILE

        ARKPATH = args.path
        OLDDATFILE = '{}{}'.format(args.path, args.file)
        NEWDATFILE = '{}dynamicconfig.ini'.format(args.path)
        appkey = config.get('pushover', 'ark_key')

        log.info('Starting Ark Evolution Event Checker')

        if not os.path.exists(ARKPATH):
                log.warning('{} path does not exist. Creating it.'.format(ARKPATH))
                os.mkdir(ARKPATH)
        if not os.path.isfile(OLDDATFILE):
                log.warning('File {} does\'t exist. Nothing to compare to.'.format(OLDDATFILE))
                arkevoquery()
                new2old()
        else:
                log.debug('Existing File {} exists, will compare results'.format(OLDDATFILE))
                arkevoquery()
                newstats = arkparse(NEWDATFILE)
                oldstats = arkparse(OLDDATFILE)
                if newstats['TamingSpeedMultiplier'] > oldstats['TamingSpeedMultiplier'] or newstats['BabyMatureSpeedMultiplier'] > oldstats['BabyMatureSpeedMultiplier'] or \
                            newstats['HarvestAmountMultiplier'] > oldstats['HarvestAmountMultiplier'] or newstats['XPMultiplier'] > oldstats['XPMultiplier']:
                        log.info(f'Evolution Event Started. {newstats["TamingSpeedMultiplier"]}x Taming {newstats["BabyMatureSpeedMultiplier"]}x Breeding {newstats["HarvestAmountMultiplier"]}x Harvesting {newstats["XPMultiplier"]}x XP {newstats["CustomRecipeEffectivenessMultiplier"]}x Recipes')
                        gentools.pushover(appkey, 'Ark Evolution Event Started!', f'{newstats["TamingSpeedMultiplier"]}x Taming\n{newstats["BabyMatureSpeedMultiplier"]}x Breeding\n{newstats["HarvestAmountMultiplier"]}x Harvesting\n{newstats["HarvestAmountMultiplier"]}x Experience\n{newstats["CustomRecipeEffectivenessMultiplier"]}x Recipes')
                        new2old()
                elif newstats['TamingSpeedMultiplier'] < oldstats['TamingSpeedMultiplier'] or newstats['BabyMatureSpeedMultiplier'] < oldstats['BabyMatureSpeedMultiplier'] or \
                newstats['HarvestAmountMultiplier'] < oldstats['HarvestAmountMultiplier'] or newstats['XPMultiplier'] < oldstats['XPMultiplier']:
                        log.info('Evolution Event Ended.')
                        gentools.pushover(appkey, 'Ark Evolution Event has Ended', f'Multipliers have returned to {newstats["TamingSpeedMultiplier"]}x')
                        new2old()
                else:
                        log.info('No Change Detected. Multipliers remain')
        if os.path.isfile(NEWDATFILE):
                try:
                        os.remove(NEWDATFILE)
                        log.debug('Removing file {}'.format(NEWDATFILE))
                except:
                        log.exception('Error while removing file {}'.format(NEWDATFILE))
                        exit()

        log.info('Script Completed Successfully')


def arkevoquery():
    log.info('Sending GET request to http://arkdedicated.com/dynamicconfig.ini')
    try:
        evohttp = urllib.request.urlopen('http://arkdedicated.com/dynamicconfig.ini')
        evostats = evohttp.read()
        log.info('GET Query to http://arkdedicated.com/dynamicconfig.ini Successful.')
    except Exception:
        log.exception('Cannot contact URL http://arkdedicated.com/dynamicconfig.ini')
        exit()

    if os.path.isfile(NEWDATFILE):
        try:
            os.remove(NEWDATFILE)
            log.debug('Removing lingering file before write {}'.format(NEWDATFILE))
        except:
            log.exception('Error removing lingering file before write {}'.format(NEWDATFILE))
            exit()

    try:
        saveFile = open(NEWDATFILE, 'w')
        saveFile.write(str(evostats))
        saveFile.close()
        log.debug('File {} saved successfully'.format(NEWDATFILE))
    except:
        log.exception('Error saving file {}'.format(NEWDATFILE))
        exit()


def arkparse(wfile):
    log.debug('Starting file Parser on {}'.format(wfile))
    if not os.path.isfile(wfile):
        log.exception('Cannot Parse File. File does not exist {}'.format(wfile))
        exit()
    try:
        arkfile = open(wfile, 'r').read()
        arkfile = arkfile.rstrip()

    except:
        log.exception('Error reading {}'.format(wfile))
        exit()
    arkstats = arkfile.split('\\r\\n')
    arkstats[0] = arkstats[0][:0] + arkstats[0][2:]  # Sanitize output
    arkstats[5] = arkstats[5].rstrip("'")         # Sanitize Output
    arkdict = {k: v for k, v in (x.split('=') for x in arkstats)}
    log.debug('Stats from {} data found: {}'.format(wfile, arkdict))
    for i in arkdict:
        arkdict[i] = procmultip(arkdict[i])
    return(arkdict)


def procmultip(multiple):
    multiple = multiple.rstrip("'")
    if multiple.endswith('0'):
        multip = multiple.rstrip('.0')
        multip = int(multip)
    else:
        multip = float(multiple)
    return(multip)


def new2old():
    if os.path.isfile(OLDDATFILE):
        os.remove(OLDDATFILE)
        log.debug('Removing file {}'.format(OLDDATFILE))
    try:
        copyfile(NEWDATFILE, OLDDATFILE)
        log.debug('Copying {} to {}'.format(NEWDATFILE, OLDDATFILE))
    except:
        log.exception('Error while copying file {} to {}'.format(NEWDATFILE, OLDDATFILE))
        os.remove(NEWDATFILE)
        exit()
    try:
        os.remove(NEWDATFILE)
        log.debug('Deleted File {}'.format(NEWDATFILE))
    except:
        log.critical('Error Deleting File {}'.format(NEWDATFILE))
        exit()


if __name__ == '__main__':
    main()
