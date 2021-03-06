from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
from datetime import datetime as dt
from datetime import timedelta as tdelta
import re
import glob
from time import sleep

import pymongo

from tornado.web import RequestHandler, Application, url, StaticFileHandler
import tornado.log as tlog

from astropy import units as u
from astropy.coordinates import SkyCoord
import ephem

import IQMon
from VYSOS import weather_limits


##-------------------------------------------------------------------------
## Get Telescope Status
##-------------------------------------------------------------------------
def get_status(telescope, db):
    collection = db[f'{telescope}status']
    two_min_ago = dt.utcnow() - tdelta(0, 2*60)
    values = [x for x in
              collection.find( {'date': {'$gt': two_min_ago}} ).sort('date')]
    try:
        current = status_values[-1]
    except:
        current = None
    return current


##-------------------------------------------------------------------------
## Check for Images
##-------------------------------------------------------------------------
def get_image_list(telescope, date):
#     path = os.path.join('/Volumes/Data_{}/Images/{}'.format(telescope, date))
    path = os.path.join('/', 'Users', 'vysosuser', f'{telescope}Data', 'Images', f'{date}')
    image_list = glob.glob(os.path.join(path, '{}*fts'.format(telescope)))
    return image_list

##-------------------------------------------------------------------------
## Check for Flats
##-------------------------------------------------------------------------
def get_flat_list(telescope, date):
#     path = os.path.join('/Volumes/Data_{}/Images/{}/AutoFlat'.format(telescope, date))
    path = os.path.join('/', 'Users', 'vysosuser', f'{telescope}Data', 'Images', f'{date}', 'AutoFlat')
    image_list = glob.glob(os.path.join(path, 'AutoFlat*fts'))
    return image_list


##-------------------------------------------------------------------------
## Check Free Space on Drive
##-------------------------------------------------------------------------
def free_space(path):
    statvfs = os.statvfs(path)
    size = statvfs.f_frsize * statvfs.f_blocks * u.byte
    avail = statvfs.f_frsize * statvfs.f_bfree * u.byte

    if re.search('\/Volumes\/DataCopy', path):
        print('Correcting for 4.97 TB disk capacity')
        capacity = (4.97*u.TB).to(u.byte)
        correction = size - capacity
        size -= correction
        avail -= correction
    elif re.search('\/Volumes\/MLOData', path):
        print('Correcting for 16 TB disk capacity')
        capacity = (16.89*u.TB).to(u.byte)
        correction = size - capacity
        size -= correction
        avail -= correction
        if capacity > 16*u.TB:
            correction2 = (capacity - 16*u.TB).to(u.byte)
            size -= correction2
    used = (size - avail)/size

    return (size.to(u.GB).value, avail.to(u.GB).value, used.to(u.percent).value)


##-----------------------------------------------------------------------------
## Handler for Status Page
##-----------------------------------------------------------------------------
class Status(RequestHandler):
    def get(self, input):
        tlog.app_log.info('Get request for Status "{}" recieved'.format(input))
        nowut = dt.utcnow()
        now = nowut - tdelta(0,10*60*60)

        client = pymongo.MongoClient('192.168.1.101', 27017)
        db = client['vysos']

        ##------------------------------------------------------------------------
        ## Use pyephem determine sunrise and sunset times
        ##------------------------------------------------------------------------
        Observatory = ephem.Observer()
        Observatory.lon = "-155:34:33.9"
        Observatory.lat = "+19:32:09.66"
        Observatory.elevation = 3400.0
        Observatory.temp = 10.0
        Observatory.pressure = 680.0
        Observatory.horizon = '0.0'

        Observatory.date = nowut
        TheSun = ephem.Sun()
        TheSun.compute(Observatory)
        sun = {}
        sun['alt'] = float(TheSun.alt) * 180. / ephem.pi
        sun['set'] = Observatory.next_setting(TheSun).datetime()
        sun['rise'] = Observatory.next_rising(TheSun).datetime()
        if sun['alt'] <= -18:
            sun['now'] = 'night'
        elif sun['alt'] > -18 and sun['alt'] <= -12:
            sun['now'] = 'astronomical twilight'
        elif sun['alt'] > -12 and sun['alt'] <= -6:
            sun['now'] = 'nautical twilight'
        elif sun['alt'] > -6 and sun['alt'] <= 0:
            sun['now'] = 'civil twilight'
        elif sun['alt'] > 0:
            sun['now'] = 'day'

        TheMoon = ephem.Moon()
        Observatory.date = nowut
        TheMoon.compute(Observatory)
        moon = {}
        moon['phase'] = TheMoon.phase
        moon['alt'] = TheMoon.alt * 180. / ephem.pi
        moon['set'] = Observatory.next_setting(TheMoon).datetime()
        moon['rise'] = Observatory.next_rising(TheMoon).datetime()
        if moon['alt'] > 0:
            moon['now'] = 'up'
        else:
            moon['now'] = 'down'

        tlog.app_log.info('  Ephem data calculated')

        ##---------------------------------------------------------------------
        ## Get disk use info
        ##---------------------------------------------------------------------
        paths = {'Drobo': os.path.join('/', 'Volumes', 'DataCopy'),\
                 'macOS': os.path.expanduser('~'),\
                 'DroboPro': os.path.join('/', 'Volumes', 'MLOData'),\
                }

        disks = {}
        for disk in paths.keys():
            if os.path.exists(paths[disk]):
                size_GB, avail_GB, pcnt_used = free_space(paths[disk])
                disks[disk] = [size_GB, avail_GB, pcnt_used]

        tlog.app_log.info('  Disk use data determined')

        ##---------------------------------------------------------------------
        ## Get Telescope Status
        ##---------------------------------------------------------------------
        telstatus = {}
        tlog.app_log.info(f"Getting telescope status records from mongo")
        for telescope in ['V20', 'V5']:
            try:
                telstatus[telescope] = (db[f'{telescope}status'].find(limit=1, sort=[('date', pymongo.DESCENDING)])).next()
                if 'RA' in telstatus[telescope] and 'DEC' in telstatus[telescope]:
                    coord = SkyCoord(telstatus[telescope]['RA'],
                                     telstatus[telescope]['DEC'], unit=u.deg)
                    telstatus[telescope]['RA'], telstatus[telescope]['DEC'] = coord.to_string('hmsdms', sep=':', precision=0).split()
                tlog.app_log.info(f"  Got telescope status record for {telescope}")
            except StopIteration:
                telstatus[telescope] = {'date': dt.utcnow()-tdelta(365),
                                        'connected': False}
                tlog.app_log.info(f"  No telescope status records for {telescope}.")
                tlog.app_log.info(f"  Filling in blank data for {telescope}.")
        
        
        ##---------------------------------------------------------------------
        ## Get Current Weather
        ##---------------------------------------------------------------------
        tlog.app_log.info(f"Getting weather records from mongo")
        weather = client.vysos['weather']
        if weather.count() > 0:
            cw = weather.find(limit=1, sort=[('date', pymongo.DESCENDING)]).next()
        else:
            cw = None
        tlog.app_log.info(f"  Done")
        
        ##---------------------------------------------------------------------
        ## Render
        ##---------------------------------------------------------------------
        if nowut.hour < 6 and sun['now'] == 'day' and (sun['set']-nowut).total_seconds() >= 60.*60.:
            link_date_string = (nowut - tdelta(1,0)).strftime('%Y%m%dUT')
            files_string = "Last Night's Files"
        elif sun['now'] != 'day':
            link_date_string = nowut.strftime('%Y%m%dUT')
            files_string = "Tonight's Files"
        else:
            link_date_string = nowut.strftime('%Y%m%dUT')
            files_string = "Last Night's Files"

        tlog.app_log.info('  Rendering Status')
        cctv = False
        if input.lower() in ["cctv", "cctv.html"]:
            cctv = True
        self.render("status.html", title="VYSOS Status",
                    now = (now, nowut),
                    disks = disks,
                    link_date_string = link_date_string,
                    moon = moon,
                    sun = sun,
                    telstatus=telstatus,
                    files_string = files_string,\
                    v5_images = get_image_list('V5', link_date_string),\
                    v20_images = get_image_list('V20', link_date_string),\
                    v5_flats = get_flat_list('V5', link_date_string),\
                    v20_flats = get_flat_list('V20', link_date_string),\
                    cctv=cctv,
                    currentweather=cw,
                    weather_limits=weather_limits,
                    )
        tlog.app_log.info('  Done')




