# -*- coding: utf-8 -*-

import datetime as dt
import pickle

import pandas as pd
from PyFin.Utilities import pyFinAssert
from matplotlib import font_manager


def top(df, column=None, n=5):
    """
    :param df: pd.DataFrame/Series
    :param column: str, col name to be sorted
    :param n: int, optional, top n element to be returned
    :return: pd.Series, larget n element in col
    """
    if isinstance(df, pd.Series):
        ret = df.sort_values(ascending=False)[:n]
    else:
        pyFinAssert(column is not None, "Specify the col name or use pandas Series type of data")
        ret = df.sort_values(by=column, ascending=False)[:n]

    return ret


def convert_to_non_cumul_return(returns):
    """
    :param returns: pd.Series, daily cumul returns
    :return: pd.Series, daily non-cumul returns
    """
    daily_returns = returns.pct_change()
    daily_returns.dropna(inplace=True)
    return daily_returns


def time_index_slicer(data, start_date, end_date):
    """
    :param data: pd.DataFrame, index = datetime.datetime
    :param start_date: str/datetime.datetime, start date of the horizon returned
    :param end_date: str/datetime.datetime, end date of the horizon returned
    :return: pd.DataFrame, time sliced data
    """

    ret = data.loc[data.index >= start_date]
    ret = ret.loc[ret.index <= end_date]
    return ret


def fig_style(ax, legend, x_label, y_label, legend_loc='upper right'):
    font = font_manager.FontProperties(family='SimHei', style='normal', size=16, weight='normal', stretch='normal')
    ax.legend(legend, prop={'size': 12}, loc=legend_loc)
    ax.title.set_font_properties(font)
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    ax.set_facecolor('white')
    ax.grid(color='gray', alpha=0.2, axis='y')
    return ax


def pickle_dump_data(data, pkl_name, protocol=-1):
    """
    :param data: any type
    :param pkl_name: str, *.pkl
    :param protocol: int, optional, protocol in saving pickle
    :return:
    """
    files = open(pkl_name, 'wb')
    pickle.dump(data, files, protocol)
    files.close()
    return "pickle file {s} saved".format(pkl_name)


def pickle_load_data(pkl_name):
    """
    :param pkl_name: *.pkl
    :return: data saved in *.pkl
    """

    files = open(pkl_name, 'rb')
    data = pickle.load(files)
    files.close()
    return data


def time_counter(func):
    def wrapper(*args, **kwargs):
        start_time = dt.datetime.now()
        print("Start: %s" % start_time)
        ret = func(*args, **kwargs)
        end_time = dt.datetime.now()
        print("End : %s" % end_time)
        print("Elapsed: %s" % (end_time - start_time))
        return ret

    return wrapper
