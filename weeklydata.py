import sys
from time import time
from datetime import datetime
import math
import itertools
import re

import matplotlib.pyplot as plt
from pandas.core.frame import DataFrame
# from sklearn.feature_selection import chi2
# from sklearn.model_selection import cross_val_score
import numpy
import pandas
# from sklearn.metrics import confusion_matrix
# # import seaborn as sns
from scipy.sparse import dok_matrix

# # from sklearn.externals import joblib
# from joblib import dump, load

##### models for finding outliers
# from sklearn.ensemble import IsolationForest
# from pyod.models.cblof import CBLOF
# from pyod.models.abod import ABOD
# from pyod.models.knn import KNN


#testrun below will test the model against testing data if set to true

# calculate difference in times accounting for crossing midnight ...
def clockdiff( tm1, tm2 ):
    # find the difference - determine whether it is greater than allowed
    diff = tm2 - tm1
    if abs(diff) > 12.0 :
        # convert to other half of clock
        if diff < 0.0:
            diff += 24.0
        else:
            diff -= 24.0

    return diff

#  tod = "time of day" -- prior average
# combine time of day info to keep a running average
def clockadd( tod, lhour, lcount ):
    if lcount < 1.5 :      # easy case, no averaging required
        if lhour == 0.0:
            lhour = .016666667     # add one minute ...
        return lhour

    # find the difference - determine whether addition is complicated
    diff = lhour - tod
    if abs(diff) > 12.0 :
        diff = 24.0 - abs(diff)     # convert to other half of clock
        adjust = diff / lcount       # amount to move (averaged)
        # adjust time of day in proper direction
        if tod < 12.0 :
            newtod = tod - adjust
        else :
            newtod = tod + adjust
        if newtod < 0.0 :
            newtod += 24.0
        if newtod > 24.0 :
            newtod -= 24.0
    else :
        # simple average
        newtod = (tod*(lcount-1) + lhour) / lcount

    #  avoid exact 0.0 values ... they mess with the logic
    if newtod == 0.0:
        newtod = .016666667     # add one minute ...
    return newtod


# This would probably be better as an object ... something to do later!
# create a new record (data dictionary) for storing
def new_record(uname):
    mrec = { 'user': uname, 'ltime': [], 'tod': 0, 'count': 0, 'comp': [],
        'remov': 0, 'exec': 0, 'execrem': 0, 'after': 0,
        'afterrem': 0, 'ftod': 0, 'fcount': 0, 'ftime': [],
        'mcount': 0, 'mnorm': 0, 'mnormtod': 0, 'match': 0, 'matchtod': 0, 'msize': 0,
        }
    return mrec


def new_userrecord(uname,pweek):
    urec = { 'user': uname, 'logs': []}

    # could be one or more missing if a user had no activity for a given month
    while len(urec['logs']) < (pweek+1):
        urec['logs'].append(new_record(uname))
    return urec

def update_userrecord(urec,pweek):
    # could be one or more missing if a user had no activity for a given month
    while len(urec['logs']) < (pweek+1):
        urec['logs'].append(new_record(urec['user']))
    return urec

# first attempt to retrieve records with a binary search
#   - do the numbers show that it's necessary?  not sure yet
def getbin_logrecord(logdata,uname,pweek):
    # print('getbin_logrecord(%s) len = %d, pweek = %d'%(uname,len(logdata),pweek))
    if len(logdata) == 0:
        logdata.append(new_userrecord('AAA0000',pweek))
        lcount = new_userrecord(uname,pweek)
        logdata.append(lcount)
        logdata.append(new_userrecord('ZZZ9999',pweek))
        return lcount

    # binary search for username
    # XXX this version hangs ... not sure if it's the insert or the search
    lo = 0
    limit = len(logdata)-1
    hi = limit
    diff = hi-lo
    idx = 0
    count = 0
    while diff > 1:
        count += 1
        if count > limit:
            print( 'ERROR count = %d, limit = %d'%(count, limit))
            return None     # break it!
        mid = lo + int(diff/2)
        # print( 'lo/hi/mid = %d/%d/%d'%(lo,hi, mid))
        if uname == logdata[mid]['user']:
            return update_userrecord(logdata[mid],pweek)
        if uname > logdata[mid]['user']:
            lo = mid
            idx = hi
        else:
            hi = mid
            idx = mid
        # print( 'lo/hi/mid = %d/%d/%d'%(lo,hi, mid))
        diff = hi-lo
        # print( '  diff = %d'%(diff))

    # print( '   creating new record for %s'%(uname))
    lcount = new_userrecord(uname,pweek)
    logdata.insert(idx,lcount)
    return lcount

# def get_filecopy(filecopy,uname,pmonth):
#     return get_logrecord(filecopy,uname,pmonth)

# link to binary search version
def getbin_filecopy(filecopy,uname,pweek):
    # use binary search to get logon record ...
    return getbin_logrecord(filecopy,uname,pweek)


def addcomp( complist, pc ):
    for comp in complist:
        if comp == pc:
            return
    complist.append( pc )

def addtime( timelist, ltime ):
    timelist.append( ltime )


def writecsv( logrecord, prefix, pmonth ):
    log_data = create_dataframe( logrecord )
    # print('\nTime of Day (description)')
    # print(log_data['tavg'].describe())

    fname = "./"+prefix+str(pmonth)+".csv"
    log_data.to_csv(fname, sep=',', na_rep='', header=True, errors='strict')

# calculate min, max, avg, std  logon timing for each user
def calclogtimes( logrecord ):
    # loop through records for each user
    ucount = 0
    maxweek = 0
    for ur in logrecord:
        # loop through records for each month of activity
        ucount = 0
        # maxweek = max(maxweek,len(ur['logs']))
        # if len(ur['logs']) < maxweek:
        #     print( 'calctimes(): user %s has %d weeks (max = %d)'
        #             % (ur['user'],len(ur['logs']),maxweek))
        for lr in ur['logs']:
            tavg = lr['tod']
            tsumsq = 0.0
            tmax = 0.0
            tmin = 36.0
            nsamples = 0
            ucount += 1

            # check whether to shift clock for calculating min and max times
            if tavg < 6.0 or tavg > 18.0 :
                for tm in lr['ltime']:
                    tmval = tm
                    if tmval < 12.0:
                        tmval += 24.0  # shift forward to make min/max useful
                    if tmval < tmin:
                        tmin = tmval
                    if tmval > tmax:
                        tmax = tmval
                    tdiff = clockdiff( tavg, tm)
                    tsumsq += tdiff*tdiff
                    nsamples += 1
                if tmax > 24.0:
                    # print("^^^ shifting range = [%.4f,%.4f]"%(tmin,tmax))
                    tmax -= 24.0        # shift back for recording
                if tmin > 24.0:
                    # print(",,, shifting range = [%.4f,%.4f]"%(tmin,tmax))
                    tmin -= 24.0        # shift back for recording
            else:
                for tm in lr['ltime']:
                    if tm < tmin:
                        tmin = tm
                    if tm > tmax:
                        tmax = tm
                    tdiff = clockdiff( tavg, tm)
                    tsumsq += tdiff*tdiff
                    nsamples += 1

            # record values for this user ... 
            lr['tmax'] = tmax
            lr['tmin'] = tmin
            if nsamples > 1:
                lr['tsdev'] = math.sqrt( tsumsq / (nsamples-1) )
            else:
                # for one sample case ...
                # use 'range rule' SD estimator:  one quarter of an eight hour day
                lr['tsdev'] = 2.0
                # print( ' One sample >> [%.4f,%.4f], avg = %.4f +- %.4f' % (tmin, tmax, tavg, lr['tsdev']))

        # if ucount < 11:
        #     print( ' range = [%.4f,%.4f], avg = %.4f +- %.4f' % (tmin, tmax, tavg, lr['tsdev']))

# calculate min, max, avg, std  logon timing for each user
def calcfiletimes( filerecord ):
    # loop through records for each user
    ucount = 0
    dummyct = 0
    for ur in filerecord:
        # loop through records for each month of activity
        ucount = 0
        for fr in ur['logs']:
            # check for file copy data ...
            if not 'ftod' in fr:
                # if none, create dummy data based on login time and move on
                #   TODO: better would be to represent no activity somehow ...
                tavg = fr['ftod'] = fr['tod']
                tmax = tmin = tavg
                nsamples = 1
                dummyct += 1
            else:
                tavg = fr['ftod']
                tsumsq = 0.0
                tmax = 0.0
                tmin = 24.0
                nsamples = 0
                ucount += 1

                # check whether to shift clock for calculating min and max times
                if tavg < 6.0 or tavg > 18.0 :
                    tmin = 36.0
                    for tm in fr['ftime']:
                        tmval = tm
                        if tmval < 12.0:
                            tmval += 24.0  # shift forward to make min/max useful
                        if tmval < tmin:
                            tmin = tmval
                        if tmval > tmax:
                            tmax = tmval
                        tdiff = clockdiff( tavg, tm)
                        tsumsq += tdiff*tdiff
                        nsamples += 1
                    if tmax > 24.0:
                        # print("^^^ shifting range = [%.4f,%.4f]"%(tmin,tmax))
                        tmax -= 24.0        # shift back for recording
                    if tmin > 24.0:
                        # print(",,, shifting range = [%.4f,%.4f]"%(tmin,tmax))
                        tmin -= 24.0        # shift back for recording
                else:
                    for tm in fr['ftime']:
                        if tm < tmin:
                            tmin = tm
                        if tm > tmax:
                            tmax = tm
                        tdiff = clockdiff( tavg, tm)
                        tsumsq += tdiff*tdiff
                        nsamples += 1

            # record values for this user ... 
            fr['ftmax'] = tmax
            fr['ftmin'] = tmin
            if nsamples > 1:
                fr['ftsdev'] = math.sqrt( tsumsq / (nsamples-1) )
            else:
                # for one sample case ...
                # use 'range rule' SD estimator:  one quarter of an eight hour day
                fr['ftsdev'] = 0.0
                # print( ' One sample >> [%.4f,%.4f], avg = %.4f +- %.4f' % (tmin, tmax, tavg, fr['ftsdev']))

            # if ucount < 11:
            #     print( ' range = [%.4f,%.4f], avg = %.4f +- %.4f' % (tmin, tmax, tavg, lr['tsdev']))
    print( '  dummy data count = %d (no file copies)' % (dummyct))

#######################################
# Evaluate user logon records
def explore_logon(datadoc,pmonth):
    # logon.csv columns:
    # id,date,user,pc,activity
    # device.csv columns:
    # id,date,user,pc,file_tree,activity
    # file.csv
    # id,date,user,pc,filename,activity,to_removable_media,from_removable_media,content
    # email.csv
    # id,date,user,pc,to,cc,bcc,from,activity,size,attachments,content
    print('\nexplore_logon():')

    t0 = time()
    logon = pandas.read_csv(datadoc)
    print( "time to read logon data = %.3f secs" % (time()-t0))
    print("number of rows = ", len(logon))

    count = 0
    maxweek = 0

    # print( "\nYear %d, Month %d" % (pyear,rmonth))
    # print("first row = ",features[0])
    #  create matrix to count user/pc pairings
    # >>> for i in range(5):
    # ...     for j in range(5):
    # ...         S[i, j] = i + j    # Update element
    count = 0
    countlogon = 0
    countlogoff = 0
    logrecord = []
    t0 = time()

    for x in logon.itertuples(index=False):
        dtobj = datetime.strptime(x[1], "%m/%d/%Y %H:%M:%S")
        # for development ... only look at first month
        # if dtobj.year < pyear or dtobj.month < pmonth :
        #     continue
        # if dtobj.year == pyear and dtobj.month > pmonth :
        #     break
        lhour = dtobj.hour + dtobj.minute/60.
        rmonth = dtobj.month
        # for development ... stop after N months of data
        if rmonth > pmonth:
            break
        # datetime.date(2010, 6, 16).isocalendar().week
        isoyear, rweek, isomonth  = dtobj.isocalendar()
        if isoyear == 2009:
            rweek = 0   # 2009 ends on 53rd week, so adjust accordingly
        if dtobj.year == 2011:
            rmonth += 12
            if rweek < 52:      # sanity check
                rweek += 52
        
        maxweek = max(rweek,maxweek)

        # print( 'year (isoyear), month, week = %d (%d), %d, %d'%(dtobj.year, isoyear, rmonth, rweek))
        # if count < 5 :
        #     print(x)
            # print(x[4])
        #     # print("dt object = ", dtobj)
        #     print("    hour = ", lhour)
        count += 1
        # if x[4] == 'Logon' and dtobj.month == pmonth:
        uname = x[2]
        pc = x[3]
            # print("filecopy length = ",len(filecopy))
        if x[4] == 'Logon':
            countlogon += 1
            # ucount = get_logrecord(logrecord,uname,rweek)
            ucount = getbin_logrecord(logrecord,uname,rweek)
            lcount = ucount['logs'][rweek]

            # lcount = { 'user': uname, 'tod': 0, 'count': 0, 'comp': []}
            addtime( lcount['ltime'], lhour)

            lcount['count'] += 1
            lcount['tod'] = clockadd( lcount['tod'], lhour, lcount['count'] )

            addcomp( lcount['comp'], pc )

        if x[4] == 'Logoff':
            countlogoff += 1
        # xval.append( idx )    # this will go away
        # yval.append( jdx )      # this will go away

    tta = time() - t0   # time to analyze
    print( "  time to analyze logons = %.3f secs" % (tta))
    global analytical_time
    analytical_time += tta
    print( "counted %d logon and %d logoff events" % (countlogon, countlogoff))

    print( "Number of Users with logon events = ",len(logrecord))

    # calctimes( logrecord )

            # lcount = { 'user': uname, 'tod': 0, 'count': 0, 'comp': []}
    tcomp = 0
    maxcomp = 0
    mincomp = 1000000
    numonths = 0        # number of user months
    for uc in logrecord:
        for lc in uc['logs']:
            numonths +=1
            ncomp = len(lc['comp'])
            tcomp += ncomp
            if ncomp > maxcomp:
                maxcomp = ncomp
            if ncomp < mincomp:
                mincomp = ncomp
    avcomp = tcomp / numonths
    print( "  Number computers, min = %d, max = %d" % (mincomp, maxcomp))

    cumdiff = 0
    for uc in logrecord:
        for lc in uc['logs']:
            ncomp = len(lc['comp'])
            diff = avcomp - ncomp
            cumdiff += (diff*diff)
    variance = cumdiff / (len(logrecord)-1)     # div by N-1 provides unbiased estimator
    stddev = math.sqrt( variance )
    print( "  Number computers, mean = %.4f, sdev = %.4f" % (avcomp, stddev))

    count = 0
    latenight = 0
    manycomp = 0
    dblcount = 0
    evecnt = midcnt = precnt = 0
    for uc in logrecord:
        for lc in uc['logs']:
            # print(fc)
            # if count > 20:
            #     break
            count += 1
            anomalies = 0
            if lc['tod'] < 6.0 or lc['tod'] > 18.0:
                # print('removable: ',fc)
                anomalies += 1
                latenight += 1
                tm = lc['tod']
                if tm > 18.0 and tm <= 22.0:
                    evecnt += 1
                if tm > 22.0 or tm <= 2.0:
                    midcnt += 1
                if tm > 2.0 and tm < 6.0:
                    precnt += 1
            if len(lc['comp']) > (avcomp+(2*stddev)):
                anomalies += 1
                manycomp += 1
            if anomalies > 1:
                dblcount += 1
                # if tplcount < 20:
                #     print('triple:',fc)

    print( "  maximum week found =  ",maxweek)
    print( "Number \"Double Threat\" Users: ",dblcount)
    print( "Number \"Late Night Logon\" Users: ",latenight)
    print( "Number \"Many Computer\" Users: ",manycomp)
    print( "evening = %d / midnight = %d / predawn = %d" % (evecnt, midcnt, precnt))


    return logrecord
    # plotxvy(xval,yval,"")

def to_removable(rec):
    #  NOTE:  python interprets the string in the file, result is boolean, NOT a string
    removable = rec[6]
    if removable:
        return True

    return False

def copy_exec(rec):
    fname = rec[4]
    ## if name matches *.exe
    match = re.search('\.exe$', fname)
    #  method .start() provides starting index
    if match:       # non-null return means it found a match ...
        # print('\nExecutable: ',fname)
        # print(match)
        return True

    return False

def copy_exec_rem(rec):
    fname = rec[4]
    ## if name matches *.exe
    match = re.search('\.exe$', fname)
    removable = rec[7]          # from removable media
    if match and removable:       # non-null return means it found a match ...
        return True

    return False

# This could be smarter:
#   - we should compare time of day to the normal login activity for the user
# This could benefit from a fuzzy boundary rather than crisp cutoffs
def after_hours(tod):
    if tod < 6. or tod > 18.:
        return True

    return False

#######################################
# Evaluate File transfer records
def explore_files(urecord,datadoc,pmonth):
    # logon.csv columns:
    # id,date,user,pc,activity
    # device.csv columns:
    # id,date,user,pc,file_tree,activity
    # file.csv
    # id,date,user,pc,filename,activity,to_removable_media,from_removable_media,content
    # email.csv
    # id,date,user,pc,to,cc,bcc,from,activity,size,attachments,content
    print('\nexplore_files():')

    # features is what the model will train on

    t0 = time()
    logon = pandas.read_csv(datadoc)
    print( "time to read file data = %.3f secs" % (time()-t0))
    print("number of rows = ", len(logon))

    ##########################################################################
    # generate map with number file copies AND file copies to removable media
    # also copies from removable media if file extension is .exe
    ##########################################################################

    count = 0
    maxweek = 0

    # print( "\nMonth %d" % (pmonth))
    # >>> for i in range(5):
    # ...     for j in range(5):
    # ...         S[i, j] = i + j    # Update element
    count = 0
    countcopy = 0
    # filecopy = []
    t0 = time()
    

    for x in logon.itertuples(index=False):
        dtobj = datetime.strptime(x[1], "%m/%d/%Y %H:%M:%S")
        # for development ... only look at first month
        # if dtobj.year < pyear or dtobj.month < pmonth :
        #     continue
        # if dtobj.year == pyear and dtobj.month > pmonth :
        #     break
        # if dtobj.month < pmonth :
        #     continue
        # if dtobj.month > pmonth :
        #     break
        fhour = dtobj.hour + dtobj.minute/60.
        rmonth = dtobj.month
        # for development ... stop after N months of data
        if rmonth > pmonth:
            break

        isoyear, rweek, isomonth  = dtobj.isocalendar()
        if isoyear == 2009:
            rweek = 0   # 2009 ends on 53rd week, so adjust accordingly
        if dtobj.year == 2011:
            rmonth += 12
            if rweek < 52:      # sanity check
                rweek += 53     # 2009 has a 53rd week, so adjust accordingly

        maxweek = max(maxweek,rweek)

        # if count > 200 :
        #     break
        # if count < 5 :
        #     print(x)
        #     # print(x[4])

        count += 1
        if x[5] == 'File Copy' or x[5] == 'File Write':
            countcopy += 1
            uname = x[2]
            # print("filecopy length = ",len(filecopy))
            # mcount = get_filecopy(urecord,uname,rweek)
            mcount = getbin_filecopy(urecord,uname,rweek)
            ucount = mcount['logs'][rweek]

            # ucount = get_logrecord(urecord,uname)
            # if count < 20 :
            #     print('to removable = ',x[6])
            # to_remove = x[6] == 'True'
            # from_remove = x[7] == 'True'
            if to_removable(x):
                ucount['remov'] += 1
            if copy_exec(x):
                ucount['exec'] += 1
            if copy_exec_rem(x):
                ucount['execrem'] += 1
            if after_hours(fhour):
                ucount['after'] += 1
            if to_removable(x) and after_hours(fhour):
                ucount['afterrem'] += 1
            # record = fcopy(x[2],x[4],x[5],to_remove,from_remove)

            # collect time info for all copies (to find avg and stdev)
            addtime( ucount['ftime'], fhour)
            ucount['fcount'] += 1
            ucount['ftod'] = clockadd( ucount['ftod'], fhour, ucount['fcount'] )
            # if ucount['fcount'] == 1:
            #     ucount['ftod'] = fhour
            # else :
            #     newtod = clockadd( ucount['ftod'], fhour, ucount['fcount'] )
            #     ucount['ftod'] = newtod
            # if lcount > 1 :
            #     print( "avg tod %.3f + new tod %.3f for count = %.0f results in %.3f" % (logtime[idx, jdx], lhour, logcount[idx, jdx], newtod))

    tta = time() - t0   # time to analyze
    print( "  time to analyze files = %.3f secs" % (tta))
    global analytical_time
    analytical_time += tta
    print( "counted %d file and %d copy/write events" % (count, countcopy))
    print( "  maximum week found =  ",maxweek)

    print( "Number of Users with copy/write events = ",len(urecord))
    count = 0
    tplcount = 0
    latenight = 0
    for uc in urecord:
        for fc in uc['logs']:
            # print(fc)
            # if count > 20:
            #     break
            count += 1
            anomalies = 0
            if 'remov' in fc and fc['remov'] > 0:
                # print('removable: ',fc)
                anomalies += 1
            if 'exec' in fc and fc['exec'] > 0:
                anomalies += 1
            if 'execrem' in fc and fc['execrem'] > 0:
                anomalies += 1
            if 'after' in fc and fc['after'] > 0:
                anomalies += 1
            if 'afterrem' in fc and fc['afterrem'] > 0:
                latenight += 1
                # print('>>> after hours removable: ',fc)
            if anomalies > 2:
                tplcount += 1
                # if tplcount < 20:
                #     print('triple:',fc)

    # same thing done for logons ... now for file copies
    # calcfiletimes( urecord )

    print( "Number \"Triple Threat\" User-Weeks: ",tplcount)
    print( "Number \"Late Night Copy\" User-Weeks: ",latenight)

    return urecord

#######################################
# Evaluate email records
def explore_emails(urecord,datadoc,pmonth):
    # logon.csv columns:
    # id,date,user,pc,activity
    # device.csv columns:
    # id,date,user,pc,file_tree,activity
    # file.csv
    # id,date,user,pc,filename,activity,to_removable_media,from_removable_media,content
    # email.csv columns:
    # id,date,user,pc,to,cc,bcc,from,activity,size,attachments,content
    print('\nexplore_emails():')

    t0 = time()
    # note: keep_default_na=False argument treats empty fields (,,) as a zero-length string
    #    default is to treat it as a NaN
    #    needed to treat x[10] as a string
    emails = pandas.read_csv(datadoc,keep_default_na=False)
    print( "time to read file data = %.3f secs" % (time()-t0))
    print("number of rows = ", len(emails))

    ##########################################################################
    # generate map with number emails with attachments AND average size of
    #   attachments
    ##########################################################################

    count = 0
    maxweek = 0

    # print( "\nMonth %d" % (pmonth))
    # >>> for i in range(5):
    # ...     for j in range(5):
    # ...         S[i, j] = i + j    # Update element
    count = 0
    countatch = 0
    # filecopy = []
    t0 = time()

    for x in emails.itertuples(index=False):
        dtobj = datetime.strptime(x[1], "%m/%d/%Y %H:%M:%S")
        # if dtobj.year < pyear or dtobj.month < pmonth :
        #     continue
        # if dtobj.year == pyear and dtobj.month > pmonth :
        #     break
        # if dtobj.month < pmonth :
        #     continue
        # if dtobj.month > pmonth :
        #     break
        mhour = dtobj.hour + dtobj.minute/60.
        rmonth = dtobj.month
        # for development ... stop after N months of data
        if rmonth > pmonth:
            break

        isoyear, rweek, isomonth  = dtobj.isocalendar()
        if isoyear == 2009:
            rweek = 0   # 2009 ends on 53rd week, so adjust accordingly
        if dtobj.year == 2011:
            rmonth += 12
            if rweek < 52:      # sanity check
                rweek += 53     # 2010 has a 53rd week, so adjust accordingly
        maxweek = max(maxweek,rweek)

        uname = x[2]
        # mcount = get_filecopy(urecord,uname,rweek)
        mcount = getbin_filecopy(urecord,uname,rweek)
        ucount = mcount['logs'][rweek]

        count += 1
        ucount['mcount'] += 1

        # look for attachments and send time for attachments
        #    (compare with overall send time for emails)
        # print('  ATCH[%d] = "%s"'%(len(x[10]),x[10]))
        if len(x[10]) < 1:      # i.e. zero-length / no attachment
            # time info for normal emails (no attachments)
            ucount['mnorm'] += 1
            ucount['mnormtod'] = clockadd( ucount['mnormtod'], mhour, ucount['mnorm'] )
        else:
            countatch += 1
            ucount['match'] += 1
            # time info for emails with attachments
            ucount['matchtod'] = clockadd( ucount['matchtod'], mhour, ucount['match'] )

        # check size; look for unusually large emails
        if x[9] > 0:
            # XXX do other stuff ...
            ucount['msize'] += x[9]

    # could reasonably search for disparity between norm email time and attachment times
    #   (a big (define 'big') difference in average times is suspect ...)

    tta = time() - t0   # time to analyze
    print( "  time to analyze emails = %.3f secs" % (tta))
    global analytical_time
    analytical_time += tta
    print( "counted %d emails and %d attachments" % (count, countatch))
    print( "  maximum week found =  ",maxweek)

    return urecord


def check_v_norm( val, vlist, uname, title ):
    if len(vlist) < 2:
        return False
    vmin = 1000000
    vmax = -1000000
    vavg = 0.0
    vstd = 0.0
    exceed = False
    for v in vlist:
        vavg += v
        vmin = min(vmin,v)
        vmax = max(vmax,v)
    vavg /= len(vlist)
    sumsq = 0.0
    for v in vlist:
        sumsq += (vavg-v)*(vavg-v)
    vstd = math.sqrt( sumsq/(len(vlist)-1) )
    if val > (vavg+4*vstd):
        exceed = True
        # print( '  %s exceeds StdDev threshold for [%s]' % (uname,title))
    # if val > (1.25*vmax):
    #     exceed = True
    #     # print( '  %s exceeds Max threshold for [%s]' % (uname,title))
    return exceed

def verify_rec(uname,wk,urec):
    key_list = ['user', 'tmin', 'tmax', 'tod',
                'tsdev', 'count', 'comp', 'remov', 'exec',
                'execrem', 'after', 'afterrem', 'ftmin', 'ftmax',
                'ftod', 'ftsdev', 'mnorm', 'mnormtod', 'match',
                'matchtod', 'msize']
    for k in key_list:
        if not k in urec:
            print('\nERROR: user %s record for week %d missing key = %s'%(uname,wk,k))
            return False
    return True

def data_dict(uname, wk, xcd, tmin, tmax, tod, tsdev, lcount, ncomp, remov, exec,
                execrem, after, afterrem, ftmin, ftmax, ftod, ftsdev, mnorm,
                mnormtod, match, matchtod, msize
                ):
    dtdict = { 'user': uname, 'week': wk, 'excount': xcd, 'tmin': tmin, 'tmax': tmax, 'tod': tod,
            'tsdev': tsdev, 'lcount': lcount, 'ncomp': ncomp, 'remov':remov,
            'exec': exec, 'execrem': execrem, 'afterhrs': after, 'afterrem': afterrem,
            'ftmin': ftmin, 'ftmax': ftmax, 'ftod': ftod, 'ftsdev': ftsdev,
            'mnorm': mnorm, 'mnormtod': mnormtod, 'match': match,
            'matchtod': matchtod, 'msize': msize,
        }
    return dtdict

MAVG_WINDOW = 13

def check_individuals( userrecord ):
    # loop through all users ...
    ucount = 0
    limit = 2       # minimum threshold for console reporting
    uhist = []
    uwhist = []
    uexcess = []
    overcount = 0
    maxweeks = 0
    for i in range(20):
        uhist.append(0)
        uwhist.append(0)

    for ur in userrecord:
        ucount += 1
        maxxcd = 0
        # records for logon analysis
        userlist = []
        week = []
        tmin = []
        tmax = []
        tavg = []
        tsdv = []
        nlogs = []
        ncomp = []

        # records for file analysis
        remov = []
        exec = []
        execrem = []
        after = []
        afterrem = []
        ftmin = []
        ftmax = []
        ftavg = []
        ftsdv = []

        # records for email analysis
        # 'mcount': 0, 'mnorm': 0, 'mnormtod': 0, 'match': 0, 'matchtod': 0, 'msize': 0,
        mnorm = []
        mnormtod = []
        match = []
        matchtod = []
        msize = []
        # list of lists
        llist = [ tmin, tmax, tavg, tsdv, nlogs, ncomp, 
                remov, exec, execrem, after, afterrem, ftmin, ftmax, ftavg, ftsdv, 
                mnorm, mnormtod, match, matchtod, msize, ]
        # list of column names
        clist = [ 'tmin', 'tmax', 'tod', 'tsdev', 'count', 'comp', 
                'remov', 'exec', 'execrem', 'after', 'afterrem', 'ftmin', 'ftmax',
                'ftod', 'ftsdev',
                'mnorm', 'mnormtod', 'match', 'matchtod', 'msize', ]

        over = False
        maxweeks = max(maxweeks,len(ur['logs']))

        # loop through records for each month of activity (start index at '1')
        for i in range(1,(len(ur['logs']))):
            mr = ur['logs'][i]
            xcd = 0
            uname = mr['user']
            verify_rec(uname,i,mr)

            if i > 4:
                # this dictionary is used for writing a CSV file at the end of the
                #   function ...
                # for each value, check vs. norms for that user
                xcd += check_v_norm( mr['tmin'], tmin, uname, 'min logon time' )
                xcd += check_v_norm( mr['tmax'], tmax, uname, 'max logon time' )
                xcd += check_v_norm( mr['tod'], tavg, uname, 'average logon time' )
                xcd += check_v_norm( mr['tsdev'], tsdv, uname, 'std dev logon time' )
                xcd += check_v_norm( mr['count'], nlogs, uname, 'number logons' )
                xcd += check_v_norm( len(mr['comp']), ncomp, uname, 'number computers' )

                xcd += check_v_norm( mr['remov'], remov, uname, 'copy to removable media' )
                xcd += check_v_norm( mr['exec'], exec, uname, 'executable copy' )
                xcd += check_v_norm( mr['execrem'], execrem, uname, 'exec from removable' )
                xcd += check_v_norm( mr['after'], after, uname, 'after hours copy' )
                xcd += check_v_norm( mr['afterrem'], afterrem, uname, 'after hours removable' )
                xcd += check_v_norm( mr['ftmin'], ftmin, uname, 'file min access time' )
                xcd += check_v_norm( mr['ftmax'], ftmax, uname, 'file max access time' )
                xcd += check_v_norm( mr['ftod'], ftavg, uname, 'file avg logon time' )
                xcd += check_v_norm( mr['ftsdev'], ftsdv, uname, 'file sdev logon time' )

                xcd += check_v_norm( mr['mnorm'], mnorm, uname, 'normal emails' )
                xcd += check_v_norm( mr['mnormtod'], mnormtod, uname, 'normal email time' )
                xcd += check_v_norm( mr['match'], match, uname, 'emails w attachments' )
                xcd += check_v_norm( mr['matchtod'], matchtod, uname, 'email attachment time' )
                xcd += check_v_norm( mr['msize'], msize, uname, 'email size' )

            uwhist[xcd] += 1
            maxxcd = max(maxxcd,xcd)
            if xcd > limit:
                print( '%s exceeded %d bounds in week %d'%(uname,xcd,i))
                over = True

            # create and store data entries for each week where a user breaks out in
            #   more than one variable
            # this will be used to create a CSV file ...
            if xcd > 1:
                ddict = data_dict(mr['user'], i, xcd, mr['tmin'], mr['tmax'], mr['tod'],
                    mr['tsdev'], mr['count'], len(mr['comp']), mr['remov'], mr['exec'],
                    mr['execrem'], mr['after'], mr['afterrem'], mr['ftmin'], mr['ftmax'],
                    mr['ftod'], mr['ftsdev'], mr['mnorm'], mr['mnormtod'], mr['match'],
                    mr['matchtod'], mr['msize'] )
                uexcess.append( ddict )

            # store data in lists to generate moving averages ...
            userlist.append(mr['user'])   # not actually necessary if we're not writing to a file
            week.append(i)
            for ls, col in zip(llist, clist):
                if col == 'comp':
                    ls.append(len(mr[col]))
                else:
                    ls.append(mr[col])

            # delete last item in each list if length is greater than moving
            #   average window ...
            for ls in llist:
                if len(ls) > MAVG_WINDOW:
                    del ls[0]

        uhist[maxxcd] += 1
        if over:
            overcount += 1

    print( '\n%d out of %d users exceeded %d or more bounds'%(overcount,ucount,limit))
    print( '  maximum number of weeks found = %d'%(maxweeks))
    print('> user exceeds:')
    print(uhist)
    print('> user-week exceeds:')
    print(uwhist)

    ddf = pandas.DataFrame(uexcess)
    fname = "./weeklydata.csv"
    ddf.to_csv(fname, sep=',', na_rep='', header=True, errors='strict')
    return uhist




###############################################################################
##  main execution thread
###############################################################################
logdoc = "./logon.csv"        # default value
devdoc = "./device.csv"        # default value
emaildoc = "./email.csv"        # default value
filedoc = "./file.csv"        # default value

# if len(sys.argv) > 1 :
#     rootdoc = sys.argv[1]

# testdoc = "./full_test.csv"        # default value
# if len(sys.argv) > 2 :
#     testdoc = sys.argv[2]

analytical_time = 0.0

outliers = []
statiscore = []
pyear = 2010
pmonth = 24     # higher than in dataset ... include all data

# These function extract, organize and evaluate the raw data from the files
lrec = explore_logon(logdoc,pmonth)
lrec = explore_files(lrec,filedoc,pmonth)
lrec = explore_emails(lrec,emaildoc,pmonth)

# Calculate average and standard deviation for access times 
calclogtimes( lrec )
calcfiletimes( lrec )

# compute moving averages for all variables and coompare users' weekly activity
#   to their running totals ...
check_individuals(lrec)

# keep track of timing information to check where improvement needs to occur
print( "\nTotal Analytical Time = %.3f secs" % (analytical_time))
