# coding=utf-8
import datetime

import pandas as pd
from PyFin.DateUtilities import Calendar
from PyFin.DateUtilities import Date
from PyFin.DateUtilities import Period
from PyFin.DateUtilities import Schedule
from PyFin.Enums import BizDayConventions
from PyFin.Enums import TimeUnits
from PyFin.Enums.Weekdays import Weekdays

_freqDict = {'d': TimeUnits.Days,
             'b': TimeUnits.BDays,
             'w': TimeUnits.Weeks,
             'm': TimeUnits.Months,
             'y': TimeUnits.Years}


def map_to_biz_day(date_series, calendar='China.SSE', convention=BizDayConventions.Preceding):
    """
    :param date_series: pd.Sereis, datetime.datetime
    :param calendar: str, optional, name of the calendar to use in dates math
    :param convention: str, optional, pyFin date conventions
    :return: pd.Series, datetime.datetime
    用更快的方式计算, 避免对每个日期进行循环
    """
    unique_date_list = sorted(set(date_series))
    py_date_list = [Date.fromDateTime(date) for date in unique_date_list]
    py_date_list = [Calendar(calendar).adjustDate(date, convention) for date in py_date_list]
    biz_day_list = [Date.toDateTime(date) for date in py_date_list]
    dict_date_map = dict(zip(unique_date_list, biz_day_list))
    ret = date_series.map(dict_date_map)
    return ret


def get_pos_adj_date(start_date, end_date, formats="%Y-%m-%d", calendar='China.SSE', freq='m'):
    """
    :param start_date: str/datetime.datetime, start date of strategy
    :param end_date: str/datetime.datetime, end date of strat egy
    :param formats: optional, formats of the string date
    :param calendar: str, optional, name of the calendar to use in dates math
    :param freq: str, optional, the frequency of data
    :return: list of datetime.datetime, pos adjust dates
    """
    if isinstance(start_date, str) and isinstance(end_date, str):
        d_start_date = Date.strptime(start_date, formats)
        d_end_date = Date.strptime(end_date, formats)
    elif isinstance(start_date, datetime.datetime) and isinstance(end_date, datetime.datetime):
        d_start_date = Date.fromDateTime(start_date)
        d_end_date = Date.fromDateTime(end_date)

    cal = Calendar(calendar)
    pos_adjust_date = Schedule(d_start_date,
                               d_end_date,
                               Period(length=1, units=_freqDict[freq]),
                               cal,
                               BizDayConventions.Unadjusted)
    # it fails if setting dStartDate to be first adjustment date, then use Schedule to compute the others
    # so i first compute dates list in each period, then compute the last date of each period
    # last day of that period(month) is the pos adjustment date
    if _freqDict[freq] == TimeUnits.Weeks:
        pos_adjust_date = [Date.toDateTime(Date.nextWeekday(date, Weekdays.Friday)) for date in pos_adjust_date[:-1]]
    elif _freqDict[freq] == TimeUnits.Months:
        pos_adjust_date = [Date.toDateTime(cal.endOfMonth(date)) for date in pos_adjust_date[:-1]]
    elif _freqDict[freq] == TimeUnits.Years:
        pos_adjust_date = [Date.toDateTime(Date(date.year(), 12, 31)) for date in pos_adjust_date[:-1]]

    pos_adjust_date = [date for date in pos_adjust_date if date <= d_end_date.toDateTime()]
    return pos_adjust_date


if __name__ == "__main__":
    print get_pos_adj_date('2013-5-20', '2016-12-20', freq='y')
    print get_pos_adj_date(datetime.datetime(2013, 5, 20), datetime.datetime(2016, 12, 20), freq='y')
    print map_to_biz_day(pd.Series([datetime.datetime(2015, 01, 30, 0, 0), datetime.datetime(2015, 02, 28, 0, 0)]))
