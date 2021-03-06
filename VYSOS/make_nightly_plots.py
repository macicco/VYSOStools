import sys
import os
from argparse import ArgumentParser
import time
from datetime import datetime as dt
from datetime import timedelta as tdelta
import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, MinuteLocator, DateFormatter
plt.style.use('classic')
import pymongo

import ephem
from astropy.io import ascii
import astropy.units as u
from astropy.table import Table, Column, Row

from VYSOS import Telescope, weather_limits


def query_mongo(db, collection, query):
    if collection == 'weather':
        names=('date', 'temp', 'clouds')
        dtype=(dt, np.float, np.float)
    elif collection == 'V20status':
        names=('date', 'focuser_temperature', 'primary_temperature',
                          'secondary_temperature', 'truss_temperature')
        dtype=(dt, np.float, np.float, np.float, np.float)
    elif collection == 'images':
        names=('date')
        dtype=(dt)

    result = Table(names=names, dtype=dtype)
    for entry in db[collection].find(query):
        insert = {}
        for name in names:
            if name in entry.keys():
                insert[name] = entry[name]
        result.add_row(insert)
    return result


def make_plots(date_string, telescope, logger, recent=False):
    logger.info(f"Making Nightly Plots for {telescope} on {date_string}")
    telname = {'V20':'VYSOS-20', 'V5':'VYSOS-5'}

    hours = HourLocator(byhour=range(24), interval=1)
    mins = MinuteLocator(range(0,60,15))
    if recent is False:
        start = dt.strptime(date_string, '%Y%m%dUT')
        end = start + tdelta(1)
        night_plot_file_name = '{}_{}.png'.format(date_string, telescope)
        hours_fmt = DateFormatter('%H')
    else:
        end = dt.utcnow()
        start = end - tdelta(0,7200)
        night_plot_file_name = 'recent_{}.png'.format(telescope)
        hours_fmt = DateFormatter('%H:%M')


    ##------------------------------------------------------------------------
    ## Set up pathnames and filenames
    ##------------------------------------------------------------------------
    tel = Telescope(telescope)
    destination_path = os.path.abspath('/var/www/nights/')
    night_plot_file = os.path.join(destination_path, night_plot_file_name)

    ##------------------------------------------------------------------------
    ## Use pyephem determine sunrise and sunset times
    ##------------------------------------------------------------------------
    Observatory = ephem.Observer()
    Observatory.lon = "-155:34:33.9"
    Observatory.lat = "+19:32:09.66"
    Observatory.elevation = 3400.0
    Observatory.temp = 10.0
    Observatory.pressure = 680.0
    Observatory.date = start.strftime('%Y/%m/%d 10:00:00')

    Observatory.horizon = '0.0'
    sunset  = Observatory.previous_setting(ephem.Sun()).datetime()
    sunrise = Observatory.next_rising(ephem.Sun()).datetime()
    Observatory.horizon = '-6.0'
    evening_civil_twilight = Observatory.previous_setting(ephem.Sun(), use_center=True).datetime()
    morning_civil_twilight = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()
    Observatory.horizon = '-12.0'
    evening_nautical_twilight = Observatory.previous_setting(ephem.Sun(), use_center=True).datetime()
    morning_nautical_twilight = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()
    Observatory.horizon = '-18.0'
    evening_astronomical_twilight = Observatory.previous_setting(ephem.Sun(), use_center=True).datetime()
    morning_astronomical_twilight = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()

    if recent is False:
        plot_start = sunset - tdelta(0, 1800)
        plot_end = sunrise + tdelta(0, 1800)
    else:
        plot_start = start
        plot_end = end


    ##------------------------------------------------------------------------
    ## Get weather, telescope status, and image data from database
    ##------------------------------------------------------------------------
    client = pymongo.MongoClient(tel.mongo_address, tel.mongo_port)
    db = client[tel.mongo_db]
    
#     logger.info(f"Querying database for images")
#     images = query_mongo(db, 'images', {'date': {'$gt':start, '$lt':end}, 'telescope':telescope } )
#     logger.info(f"  Found {len(images)} image entries")
    
    logger.info(f"Querying database for V20status")
    status = query_mongo(db, 'V20status', {'date': {'$gt':start, '$lt':end} } )
    logger.info(f"  Found {len(status)} status entries")
    
    logger.info(f"Querying database for weather")
    weather = query_mongo(db, 'weather', {'date': {'$gt':start, '$lt':end} } )
    logger.info(f"  Found {len(weather)} weather entries")


    ##------------------------------------------------------------------------
    ## Make Nightly Sumamry Plot (show only night time)
    ##------------------------------------------------------------------------
    time_ticks_values = np.arange(sunset.hour,sunrise.hour+1)
    
    if telescope == "V20":
        if recent:
            plot_positions = [ ( [0.000, 0.485, 0.460, 0.515], None                         ),
                               ( None                        , None                         ),
                               ( None                        , None                         ),
                               ( [0.540, 0.845, 0.460, 0.155], None                         ),
                               ( [0.540, 0.665, 0.460, 0.155], None                         ),
                               ( [0.540, 0.485, 0.460, 0.155], None                         ) ]
        else:
            plot_positions = [ ( [0.000, 0.760, 0.465, 0.240], [0.535, 0.760, 0.465, 0.240] ),
                               ( None                        , [0.535, 0.495, 0.465, 0.240] ),
                               ( None                        , [0.535, 0.245, 0.465, 0.240] ),
                               ( [0.000, 0.495, 0.465, 0.240], [0.535, 0.000, 0.465, 0.235] ),
                               ( [0.000, 0.245, 0.465, 0.240], None                         ),
                               ( [0.000, 0.000, 0.465, 0.235], None                         ) ]
#         if recent:
#             plot_positions = [ ( [0.000, 0.600, 0.460, 0.400], None                         ),
#                                ( None                        , None                         ),
#                                ( [0.000, 0.485, 0.460, 0.085], None                         ),
#                                ( [0.540, 0.845, 0.460, 0.155], None                         ),
#                                ( [0.540, 0.665, 0.460, 0.155], None                         ),
#                                ( [0.540, 0.485, 0.460, 0.155], None                         ) ]
#         else:
#             plot_positions = [ ( [0.000, 0.760, 0.465, 0.240], [0.535, 0.760, 0.465, 0.240] ),
#                                ( [0.000, 0.580, 0.465, 0.155], [0.535, 0.495, 0.465, 0.240] ),
#                                ( [0.000, 0.495, 0.465, 0.075], [0.535, 0.245, 0.465, 0.240] ),
#                                ( [0.000, 0.330, 0.465, 0.155], [0.535, 0.000, 0.465, 0.235] ),
#                                ( [0.000, 0.165, 0.465, 0.155], None                         ),
#                                ( [0.000, 0.000, 0.465, 0.155], None                         ) ]
    if telescope == "V5":
        if recent:
            plot_positions = [ ( [0.000, 0.485, 0.460, 0.515], None                         ),
                               ( None                        , None                         ),
                               ( None                        , None                         ),
                               ( [0.540, 0.845, 0.460, 0.155], None                         ),
                               ( [0.540, 0.665, 0.460, 0.155], None                         ),
                               ( [0.540, 0.485, 0.460, 0.155], None                         ) ]
        else:
            plot_positions = [ ( [0.000, 0.760, 0.465, 0.240], [0.535, 0.760, 0.465, 0.240] ),
                               ( None                        , [0.535, 0.495, 0.465, 0.240] ),
                               ( None                        , [0.535, 0.245, 0.465, 0.240] ),
                               ( [0.000, 0.495, 0.465, 0.240], [0.535, 0.000, 0.465, 0.235] ),
                               ( [0.000, 0.245, 0.465, 0.240], None                         ),
                               ( [0.000, 0.000, 0.465, 0.235], None                         ) ]


    logger.info("Writing Output File: {}".format(night_plot_file_name))
    if recent:
        dpi=72
        Figure = plt.figure(figsize=(12,8), dpi=dpi)
    else:
        dpi=100
        Figure = plt.figure(figsize=(13,9.5), dpi=dpi)

    ##------------------------------------------------------------------------
    ## Temperatures
    ##------------------------------------------------------------------------
    t_axes = plt.axes(plot_positions[0][0])
    if recent:
        plt.title("Recent Weather for {}".format(telescope))
    else:
        plt.title("Weather for {} on the Night of {}".format(telescope, date_string))
    logger.info('Adding temperature plot')

    logger.debug('  Adding ambient temp to plot')
    t_axes.plot_date(weather['date'], weather['temp']*9/5+32, 'ko',
                     markersize=2, markeredgewidth=0, drawstyle="default",
                     label="Outside Temp")

    logger.debug('  Adding focuser temp to plot')
    t_axes.plot_date(status['date'], status['focuser_temperature']*9/5+32, 'ro',
                     markersize=2, markeredgewidth=0,
                     label="Focuser Temp")

    logger.debug('  Adding primary temp to plot')
    t_axes.plot_date(status['date'], status['primary_temperature']*9/5+32, 'bo',
                     markersize=2, markeredgewidth=0,
                     label="Primary Temp")

    logger.debug('  Adding secondary temp to plot')
    t_axes.plot_date(status['date'], status['secondary_temperature']*9/5+32, 'go',
                     markersize=2, markeredgewidth=0,
                     label="Secondary Temp")

    logger.debug('  Adding truss temp to plot')
    t_axes.plot_date(status['date'], status['truss_temperature']*9/5+32, 'ko',
                     alpha=0.5,
                     markersize=2, markeredgewidth=0,
                     label="Truss Temp")


    t_axes.xaxis.set_major_locator(hours)
    if recent: t_axes.xaxis.set_minor_locator(mins)
    t_axes.xaxis.set_major_formatter(hours_fmt)

    ## Overplot Twilights
    plt.axvspan(sunset, evening_civil_twilight, ymin=0, ymax=1, color='blue', alpha=0.1)
    plt.axvspan(evening_civil_twilight, evening_nautical_twilight, ymin=0, ymax=1, color='blue', alpha=0.2)
    plt.axvspan(evening_nautical_twilight, evening_astronomical_twilight, ymin=0, ymax=1, color='blue', alpha=0.3)
    plt.axvspan(evening_astronomical_twilight, morning_astronomical_twilight, ymin=0, ymax=1, color='blue', alpha=0.5)
    plt.axvspan(morning_astronomical_twilight, morning_nautical_twilight, ymin=0, ymax=1, color='blue', alpha=0.3)
    plt.axvspan(morning_nautical_twilight, morning_civil_twilight, ymin=0, ymax=1, color='blue', alpha=0.2)
    plt.axvspan(morning_civil_twilight, sunrise, ymin=0, ymax=1, color='blue', alpha=0.1)

    plt.legend(loc='best', prop={'size':10})
    plt.ylabel("Temperature (F)")
    plt.xlim(plot_start, plot_end)
    plt.ylim(28,87)
    plt.grid(which='major', color='k')
    if recent:
        plt.grid(which='minor', color='k', alpha=0.8)
        plt.xlabel("UT Time")

    ## Overplot Moon Up Time
    TheMoon = ephem.Moon()
    moon_alts = []
    moon_phases = []
    moon_time_list = []
    moon_time = plot_start
    while moon_time <= plot_end:
        Observatory.date = moon_time
        TheMoon.compute(Observatory)
        moon_time_list.append(moon_time)
        moon_alts.append(TheMoon.alt * 180. / ephem.pi)
        moon_phases.append(TheMoon.phase)
        moon_time += tdelta(0, 60*5)
    moon_phase = max(moon_phases)
    moon_fill = moon_phase/100.*0.5+0.05

    m_axes = t_axes.twinx()
    m_axes.set_ylabel('Moon Alt (%.0f%% full)' % moon_phase, color='y')
    m_axes.plot_date(moon_time_list, moon_alts, 'y-')
    m_axes.xaxis.set_major_locator(hours)
    m_axes.xaxis.set_major_formatter(hours_fmt)
    plt.ylim(0,100)
    plt.yticks([10,30,50,70,90], color='y')
    plt.xlim(plot_start, plot_end)
    plt.fill_between(moon_time_list, 0, moon_alts, where=np.array(moon_alts)>0, color='yellow', alpha=moon_fill)        
    plt.ylabel('')



    ##------------------------------------------------------------------------
    ## Cloudiness
    ##------------------------------------------------------------------------
    logger.info('Adding cloudiness plot')
    c_axes = plt.axes(plot_positions[3][0])
    if recent: plt.title('(plot generated at {})'.format(now.strftime("%Y%m%d %H:%M:%S UT")))

    logger.debug('  Adding sky temp to plot')
    print(weather['clouds']*9/5+32)
    t_axes.plot_date(weather['date'], weather['clouds']*9/5+32, 'bo',
                     markersize=2, markeredgewidth=0,
                     label="Sky Temp")
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']<weather_limits['Cloudiness (C)'][0],
#                      color='green', alpha=0.5)
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']<weather_limits['Cloudiness (C)'][1],
#                      color='yellow', alpha=0.8)
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']>weather_limits['Cloudiness (C)'][1],
#                      color='red', alpha=0.8)


    c_axes.xaxis.set_major_locator(hours)
    if recent: c_axes.xaxis.set_minor_locator(mins)
    c_axes.xaxis.set_major_formatter(hours_fmt)
    c_axes.xaxis.set_ticklabels([])
    plt.ylabel("Cloudiness (F)")
    plt.xlim(plot_start, plot_end)
    if telescope == 'V5':
        plt.ylim(-130,10)
    elif telescope == 'V20':
        plt.ylim(-130,10)
    plt.grid(which='major', color='k')
    if recent: plt.grid(which='minor', color='k', alpha=0.8)



    if False:





        ##------------------------------------------------------------------------
        ## Temperature Differences (V20 Only)
        ##------------------------------------------------------------------------
        if telescope == "V20" and not recent:
            logger.info('Adding temperature difference plot')
            tdiff_axes = plt.axes(plot_positions[1][0])
            status_list = [entry for entry in\
                           status.find({'$or':[ {'UT date':date_string_yesterday},\
                                                {'UT date':date_string}],\
                                        'UT time':{'$exists':True},\
                                        'RCOS temperature (primary)':{'$exists':True},\
                                        'RCOS temperature (truss)':{'$exists':True},\
                                        'boltwood ambient temp':{'$exists':True},\
                                       }) ]
            logger.debug("  Found {} lines for temperature differences".format(len(status_list)))
            if len(status_list) > 1:
                time = [dt.strptime('{} {}'.format(entry['UT date'],\
                                                   entry['UT time']),\
                                                   '%Y%m%dUT %H:%M:%S')
                        for entry in status_list]
                primary_temp_diff = [float(x['RCOS temperature (primary)']) - \
                                     float(x['boltwood ambient temp'])\
                                     for x in status_list]
                truss_temp_diff = [float(x['RCOS temperature (truss)']) - \
                                   float(x['boltwood ambient temp'])\
                                   for x in status_list]
                logger.debug('  Adding priamry mirror temp diff to plot')
                tdiff_axes.plot_date(time, primary_temp_diff, 'ro', \
                                     markersize=2, markeredgewidth=0, drawstyle="default", \
                                     label="Mirror Temp")
                logger.debug('  Adding truss temp diff to plot')
                tdiff_axes.plot_date(time, truss_temp_diff, 'go', \
                                     markersize=2, markeredgewidth=0, drawstyle="default", \
                                     label="Truss Temp")
                tdiff_axes.plot_date([plot_start, plot_end], [0,0], 'k-')
            tdiff_axes.xaxis.set_major_locator(hours)
            if recent: tdiff_axes.xaxis.set_minor_locator(mins)
            tdiff_axes.xaxis.set_major_formatter(hours_fmt)
            tdiff_axes.xaxis.set_ticklabels([])
            plt.xlim(plot_start, plot_end)
            plt.ylim(-2.25,4.5)
            plt.ylabel("Difference (F)")
            plt.grid(which='major', color='k')
            if recent: plt.grid(which='minor', color='k', alpha=0.8)


        ##------------------------------------------------------------------------
        ## Fan State/Power (V20 Only)
        ##------------------------------------------------------------------------
        if telescope == "V20":
            logger.info('Adding fan state/power plot')
            fan_axes = plt.axes(plot_positions[2][0])
            ##------------------------------------------------------------------------
            ## V20 Dome Fan On
            status_list = [entry for entry in\
                           status.find({'$or':[ {'UT date':date_string_yesterday},\
                                                {'UT date':date_string}],\
                                        'UT time':{'$exists':True},\
                                        'CBW fan state':{'$exists':True},\
                                       }) ]
            logger.debug("  Found {} lines for dome fan state".format(len(status_list)))
            if len(status_list) > 1:
                time = [dt.strptime('{} {}'.format(entry['UT date'],\
                                                   entry['UT time']),\
                                                   '%Y%m%dUT %H:%M:%S')
                        for entry in status_list]
                dome_fan = [int(x['CBW fan state'])*100 for x in status_list]
                logger.debug('  Adding dome fan state to plot')
                fan_axes.plot_date(time, dome_fan, 'co', \
                                     markersize=2, markeredgewidth=0, drawstyle="default", \
                                     label="Dome Fan")

            ##------------------------------------------------------------------------
            ## RCOS Fan Power
            status_list = [entry for entry in\
                           status.find({'$or':[ {'UT date':date_string_yesterday},\
                                                {'UT date':date_string}],\
                                        'UT time':{'$exists':True},\
                                        'RCOS fan speed':{'$exists':True},\
                                       }) ]
            logger.debug("  Found {} lines for RCOS fan speed".format(len(status_list)))
            if len(status_list) > 1:
                time = [dt.strptime('{} {}'.format(entry['UT date'],\
                                                   entry['UT time']),\
                                                   '%Y%m%dUT %H:%M:%S')
                        for entry in status_list]
                RCOS_fan = [x['RCOS fan speed'] for x in status_list]
                logger.debug('  Adding RCOS fan speed to plot')
                fan_axes.plot_date(time, RCOS_fan, 'bo', \
                                     markersize=2, markeredgewidth=0, drawstyle="default", \
                                     label="Mirror Temp")
            fan_axes.xaxis.set_major_locator(hours)
            if recent: fan_axes.xaxis.set_minor_locator(mins)
            fan_axes.xaxis.set_major_formatter(hours_fmt)
            if not recent: fan_axes.xaxis.set_ticklabels([])

            plt.xlim(plot_start, plot_end)
            plt.ylim(-10,110)
            plt.yticks(np.linspace(0,100,3,endpoint=True))
            plt.ylabel('Pwr (%)')
            plt.grid(which='major', color='k')
            if recent:
                plt.grid(which='minor', color='k', alpha=0.8)
                plt.xlabel("UT Time")




        ##------------------------------------------------------------------------
        ## Humidity, Wetness, Rain
        ##------------------------------------------------------------------------
        logger.info('Adding humidity, wetness, rain plot')
        h_axes = plt.axes(plot_positions[4][0])
        status_list = [entry for entry in\
                       status.find({'$or':[ {'UT date':date_string_yesterday},\
                                            {'UT date':date_string}],\
                                    'boltwood time':{'$exists':True},\
                                    'boltwood date':{'$exists':True},\
                                    'boltwood humidity':{'$exists':True},\
                                    'boltwood rain condition':{'$exists':True},\
                                   }) \
                       if not 'current' in entry.keys()\
                       or not entry['current']]
        logger.debug("  Found {} lines for boltwood humidity".format(len(status_list)))
        if len(status_list) > 1:
            time = [dt.strptime('{} {}'.format(entry['boltwood date'],\
                                               entry['boltwood time'][:-3]),\
                                               '%Y-%m-%d %H:%M:%S') + \
                    + tdelta(0, 10*60*60)\
                    for entry in status_list]
            humidity = [x['boltwood humidity'] for x in status_list]
            rain_condition = [x['boltwood rain condition'] for x in status_list]
            logger.debug('  Adding Boltwood humidity to plot')
            h_axes.plot_date(time, humidity, 'bo', \
                             markersize=2, markeredgewidth=0, drawstyle="default", \
                             label="Sky Temp")
            plt.fill_between(time, -140, humidity, where=np.array(rain_condition)==1,\
                             color='green', alpha=0.5)
            plt.fill_between(time, -140, humidity, where=np.array(rain_condition)==2,\
                             color='yellow', alpha=0.8)
            plt.fill_between(time, -140, humidity, where=np.array(rain_condition)==3,\
                             color='red', alpha=0.8)
        h_axes.xaxis.set_major_locator(hours)
        if recent: h_axes.xaxis.set_minor_locator(mins)
        h_axes.xaxis.set_major_formatter(hours_fmt)
        h_axes.xaxis.set_ticklabels([])
        plt.ylabel("Humidity (%)")
        plt.xlim(plot_start, plot_end)
        plt.ylim(-5,105)
        plt.grid(which='major', color='k')
        if recent: plt.grid(which='minor', color='k', alpha=0.8)

        ##------------------------------------------------------------------------
        ## Wind Speed
        ##------------------------------------------------------------------------
        logger.info('Adding wind speed plot')
        w_axes = plt.axes(plot_positions[5][0])

        status_list = [entry for entry in\
                       status.find({'$or':[ {'UT date':date_string_yesterday},\
                                            {'UT date':date_string}],\
                                    'boltwood time':{'$exists':True},\
                                    'boltwood date':{'$exists':True},\
                                    'boltwood wind speed':{'$exists':True},\
                                    'boltwood wind condition':{'$exists':True},\
                                   }) \
                       if not 'current' in entry.keys()\
                       or not entry['current']]
        logger.debug("  Found {} lines for boltwood wind speed".format(len(status_list)))
        if len(status_list) > 1:
            time = [dt.strptime('{} {}'.format(entry['boltwood date'],\
                                               entry['boltwood time'][:-3]),\
                                               '%Y-%m-%d %H:%M:%S') + \
                    + tdelta(0, 10*60*60)\
                    for entry in status_list]
            wind_speed = [x['boltwood wind speed'] for x in status_list]
            wind_condition = [x['boltwood wind condition'] for x in status_list]
            logger.debug('  Adding Boltwood wind speed to plot')
            w_axes.plot_date(time, wind_speed, 'bo', \
                             markersize=2, markeredgewidth=0, drawstyle="default", \
                             label="Wind Speed")
            plt.fill_between(time, -140, wind_speed, where=np.array(wind_condition)==1,\
                             color='green', alpha=0.5)
            plt.fill_between(time, -140, wind_speed, where=np.array(wind_condition)==2,\
                             color='yellow', alpha=0.8)
            plt.fill_between(time, -140, wind_speed, where=np.array(wind_condition)==3,\
                             color='red', alpha=0.8)

        w_axes.xaxis.set_major_locator(hours)
        if recent: w_axes.xaxis.set_minor_locator(mins)
        w_axes.xaxis.set_major_formatter(hours_fmt)

        plt.ylabel("Wind (mph)")
        plt.xlim(plot_start, plot_end)
        plt.ylim(0,85)
        plt.grid(which='major', color='k')
        if recent: plt.grid(which='minor', color='k', alpha=0.8)

        plt.xlabel("UT Time")

        if not recent:
            ##------------------------------------------------------------------------
            ## FWHM
            ##------------------------------------------------------------------------
            logger.info('Adding FWHM plot')
            f_axes = plt.axes(plot_positions[0][1])
            plt.title("IQMon Results for {} on the Night of {}".format(telescope, date_string))

            if tel.config['units_for_FWHM'] == 'arcsec':
                scaling_factor = 206.265*float(tel.config['pixel_size'])/float(tel.config['focal_length'])
            else:
                scaling_factor = 1.0

            image_list = [entry for entry in\
                          images.find({'date':date_string,\
                                       'exposure start':{'$exists':True},\
                                       'FWHM pix':{'$exists':True},\
                                      }) ]
            logger.debug("  Found {} lines for FWHM".format(len(image_list)))
            ymax = {'V5': 4, 'V20': 6.5}[telescope]
            if len(image_list) > 0:
                time = [x['exposure start'] for x in image_list]
                fwhm = [x['FWHM pix']*scaling_factor for x in image_list]
                time_above_plot = [x['exposure start'] for x in image_list if x['FWHM pix']*scaling_factor > ymax]
                fwhm_above_plot = [x['FWHM pix']*scaling_factor for x in image_list if x['FWHM pix']*scaling_factor > ymax]
                logger.debug('  Adding FWHM to plot')
                f_axes.plot_date(time, fwhm, 'ko', \
                                 markersize=4, markeredgewidth=0, drawstyle="default", \
                                 label="FWHM (pix)")
                f_axes.plot_date(time_above_plot, fwhm_above_plot, 'r^', \
                                 markersize=5, markeredgewidth=0)
                f_axes.plot_date([plot_start, plot_end],\
                                 [tel.config['threshold_FWHM']*scaling_factor, tel.config['threshold_FWHM']*scaling_factor],\
                                 'r-')

            ## Overplot Twilights
            plt.axvspan(sunset, evening_civil_twilight, ymin=0, ymax=1, color='blue', alpha=0.1)
            plt.axvspan(evening_civil_twilight, evening_nautical_twilight, ymin=0, ymax=1, color='blue', alpha=0.2)
            plt.axvspan(evening_nautical_twilight, evening_astronomical_twilight, ymin=0, ymax=1, color='blue', alpha=0.3)
            plt.axvspan(evening_astronomical_twilight, morning_astronomical_twilight, ymin=0, ymax=1, color='blue', alpha=0.5)
            plt.axvspan(morning_astronomical_twilight, morning_nautical_twilight, ymin=0, ymax=1, color='blue', alpha=0.3)
            plt.axvspan(morning_nautical_twilight, morning_civil_twilight, ymin=0, ymax=1, color='blue', alpha=0.2)
            plt.axvspan(morning_civil_twilight, sunrise, ymin=0, ymax=1, color='blue', alpha=0.1)

            f_axes.xaxis.set_major_locator(hours)
            f_axes.xaxis.set_major_formatter(hours_fmt)

            plt.ylabel("FWHM ({})".format(tel.config['units_for_FWHM']))
            plt.yticks(range(0,20))
            plt.xlim(plot_start, plot_end)
            plt.ylim(0,ymax)
            plt.grid(which='major', color='k')
            if recent: plt.grid(which='minor', color='k', alpha=0.8)

            ##------------------------------------------------------------------------
            ## Zero Point
            ##------------------------------------------------------------------------
            logger.info('Adding Zero Point plot')
            z_axes = plt.axes(plot_positions[1][1])

            image_list = [entry for entry in\
                          images.find({'date':date_string,\
                                       'exposure start':{'$exists':True},\
                                       'zero point':{'$exists':True},\
                                      }) ]
            logger.debug("  Found {} lines for zero point".format(len(image_list)))
            ymin = {'V5': 17.25, 'V20': 18.75}[telescope]
            ymax = {'V5': 19.25, 'V20': 20.75}[telescope]
            if len(image_list) > 0:
                time = [x['exposure start'] for x in image_list]
                zero_point = [x['zero point'] for x in image_list]
                time_below_plot = [x['exposure start'] for x in image_list if x['zero point'] < ymin]
                zero_point_below_plot = [x['zero point'] for x in image_list if x['zero point'] < ymin]
                time_above_plot = [x['exposure start'] for x in image_list if x['zero point'] > ymax]
                zero_point_above_plot = [x['zero point'] for x in image_list if x['zero point'] > ymax]
                logger.debug('  Adding zero point to plot')
                z_axes.plot_date(time, zero_point, 'ko', \
                                 markersize=4, markeredgewidth=0, drawstyle="default", \
                                 label="Zero Point")
                z_axes.plot_date(time_above_plot, zero_point_above_plot, 'r^', \
                                 markersize=5, markeredgewidth=0)
                z_axes.plot_date(time_below_plot, zero_point_below_plot, 'rv', \
                                 markersize=5, markeredgewidth=0)
                z_axes.plot_date([plot_start, plot_end],\
                                 [tel.config['threshold_zeropoint'], tel.config['threshold_zeropoint']],\
                                 'r-')
            z_axes.xaxis.set_major_locator(hours)
            z_axes.xaxis.set_major_formatter(hours_fmt)
            z_axes.xaxis.set_ticklabels([])

            plt.ylabel("Zero Point")
            plt.yticks(np.arange(10,30,0.5))
            plt.xlim(plot_start, plot_end)
            plt.ylim(ymin,ymax)
            plt.grid(which='major', color='k')
            if recent: plt.grid(which='minor', color='k', alpha=0.8)


            ##------------------------------------------------------------------------
            ## Ellipticity
            ##------------------------------------------------------------------------
            logger.info('Adding Ellipticity plot')
            e_axes = plt.axes(plot_positions[2][1])

            image_list = [entry for entry in\
                          images.find({'date':date_string,\
                                       'exposure start':{'$exists':True},\
                                       'ellipticity':{'$exists':True},\
                                      }) ]
            logger.debug("  Found {} lines for ellipticity".format(len(image_list)))
            ymax = {'V5': 4, 'V20': 6}[telescope]
            if len(image_list) > 0:
                time = [x['exposure start'] for x in image_list]
                ellipticity = [x['ellipticity'] for x in image_list]
                logger.debug('  Adding ellipticity to plot')
                e_axes.plot_date(time, ellipticity, 'ko', \
                                 markersize=4, markeredgewidth=0, drawstyle="default", \
                                 label="ellipticity")
                e_axes.plot_date([plot_start, plot_end],\
                                 [tel.config['threshold_ellipticity'], tel.config['threshold_ellipticity']],\
                                 'r-')
            e_axes.xaxis.set_major_locator(hours)
            e_axes.xaxis.set_major_formatter(hours_fmt)
            e_axes.xaxis.set_ticklabels([])

            plt.ylabel("Ellipticity")
            plt.yticks(np.arange(0,1.2,0.2))
            plt.xlim(plot_start, plot_end)
            plt.ylim(0,1)
            plt.grid(which='major', color='k')
            if recent: plt.grid(which='minor', color='k', alpha=0.8)


            ##------------------------------------------------------------------------
            ## Pointing Error
            ##------------------------------------------------------------------------
            logger.info('Adding Pointing Error plot')
            p_axes = plt.axes(plot_positions[3][1])

            image_list = [entry for entry in\
                          images.find({'date':date_string,\
                                       'exposure start':{'$exists':True},\
                                       'pointing error arcmin':{'$exists':True},\
                                      }) ]
            logger.debug("  Found {} lines for pointing error".format(len(image_list)))
            ymax = {'V5': 11, 'V20': 11}[telescope]
            if len(image_list) > 0:
                time = [x['exposure start'] for x in image_list]
                pointing_err = [x['pointing error arcmin'] for x in image_list]
                time_above_plot = [x['exposure start'] for x in image_list if x['pointing error arcmin'] > ymax]
                pointing_err_above_plot = [x['pointing error arcmin'] for x in image_list if x['pointing error arcmin'] > ymax]
                logger.debug('  Adding pointing error to plot')
                p_axes.plot_date(time, pointing_err, 'ko', \
                                 markersize=4, markeredgewidth=0, drawstyle="default", \
                                 label="ellipticity")
                p_axes.plot_date(time_above_plot, pointing_err_above_plot, 'r^', \
                                 markersize=5, markeredgewidth=0)
                p_axes.plot_date([plot_start, plot_end],\
                                 [tel.config['threshold_pointing_err'], tel.config['threshold_pointing_err']],\
                                 'r-')

            plt.ylabel("Pointing Error (arcmin)")
            plt.yticks(range(0,11,2))
            plt.xlim(plot_start, plot_end)
            plt.ylim(0,ymax)
            plt.grid(which='major', color='k')
            if recent: plt.grid(which='minor', color='k', alpha=0.8)
            plt.xlabel("UT Time")

            p_axes.xaxis.set_major_locator(hours)
            p_axes.xaxis.set_major_formatter(hours_fmt)







    logger.info('Saving figure: {}'.format(night_plot_file))
    plt.savefig(night_plot_file, dpi=dpi, bbox_inches='tight', pad_inches=0.10)
    logger.info('Done.')




def main():
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add flags
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    parser.add_argument("-l", "--loop",
        action="store_true", dest="loop",
        default=False, help="Make plots in continuous loop")
    ## add arguments
    parser.add_argument("-t", dest="telescope",
        required=False, type=str,
        help="Telescope which took the data ('V5' or 'V20')")
    parser.add_argument("-d", dest="date",
        required=False, type=str,
        help="Date of night to plot")
    args = parser.parse_args()

    recent = False
    if args.date is None:
        print('Setting recent True')
        args.date = dt.utcnow().strftime("%Y%m%dUT")
        recent = True

    ##-------------------------------------------------------------------------
    ## Create Logger Object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('make_nightly_plots')
    logger.setLevel(logging.DEBUG)
    ## Set up console output
    LogConsoleHandler = logging.StreamHandler()
    if args.verbose:
        LogConsoleHandler.setLevel(logging.DEBUG)
    else:
        LogConsoleHandler.setLevel(logging.INFO)
    LogFormat = logging.Formatter('%(asctime)23s %(levelname)8s: %(message)s')
    LogConsoleHandler.setFormatter(LogFormat)
    logger.addHandler(LogConsoleHandler)
    ## Set up file output
#     LogFilePath = os.path.join()
#     if not os.path.exists(LogFilePath):
#         os.mkdir(LogFilePath)
#     LogFile = os.path.join(LogFilePath, 'get_status.log')
#     LogFileHandler = logging.FileHandler(LogFile)
#     LogFileHandler.setLevel(logging.DEBUG)
#     LogFileHandler.setFormatter(LogFormat)
#     logger.addHandler(LogFileHandler)

    make_plots(args.date, args.telescope, logger, recent=recent)

#     if args.loop is True:
#         while True:
#             ## Set date to tonight
#             now = dt.utcnow()
#             date_string = now.strftime("%Y%m%dUT")
#             make_plots(date_string, 'V5', logger)
#             make_plots(date_string, 'V5', logger, recent=True)
#             make_plots(date_string, 'V20', logger)
#             make_plots(date_string, 'V20', logger, recent=True)
#             time.sleep(120)
#     else:
#         if args.telescope:
#             make_plots(args.date, args.telescope, logger, recent=recent)
#         else:
#             make_plots(args.date, 'V5', logger)
#             if recent:
#                 make_plots(args.date, 'V5', logger, recent=True)
#             make_plots(args.date, 'V20', logger)
#             if recent:
#                 make_plots(args.date, 'V20', logger, recent=True)


if __name__ == '__main__':
    main()