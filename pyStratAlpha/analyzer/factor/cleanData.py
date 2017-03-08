# -*- coding: utf-8 -*-
import datetime

import pandas as pd
from PyFin.DateUtilities import Calendar
from PyFin.DateUtilities import Date
from PyFin.Enums import BizDayConventions

from pyAlphaStrat.utils import dateutils


def get_report_date(act_date, return_biz_day=True):
    """
    :param act_date: str/datetime.datetime, 任意日期
    :param return_biz_day: bool, 是否返回交易日
    :return: datetime, 对应应使用的报告日期， 从wind数据库中爬取
    此函数的目的是要找到，任意时刻可使用最新的季报数据的日期，比如2-20日可使用的最新季报是去年的三季报（对应日期为9-30），

    """

    if isinstance(act_date, str):
        act_date = Date.strptime(act_date)
    elif isinstance(act_date, datetime.datetime):
        act_date = Date.fromDateTime(act_date)
    act_month = act_date.month()
    act_year = act_date.year()
    if 1 <= act_month <= 3:  # 第一季度使用去年三季报的数据
        year = act_year - 1
        month = 9
        day = 30
    elif 4 <= act_month <= 7:  # 第二季度使用当年一季报
        year = act_year
        month = 3
        day = 31
    elif 8 <= act_month <= 9:  # 第三季度使用当年中报
        year = act_year
        month = 6
        day = 30
    else:
        year = act_year  # 第四季度使用当年三季报
        month = 9
        day = 30
    if return_biz_day:
        date_adj = Calendar('China.SSE').adjustDate(Date(year, month, day), BizDayConventions.Preceding)
        ret = date_adj.toDateTime()
    else:
        ret = datetime.datetime(year, month, day)
    return ret


def get_universe_single_factor(file_path, index_name=['tradeDate', 'secID'], return_biz_day=True, factor_name=None,
                               date_format='%Y%m%d'):
    """
    :param file_path: str, file_path of csv file, col =[datetime, secid, factor]
    :param index_name: multi index name to be set
    :param return_biz_day: bool, 是否返回交易日
    :param factor_name: str, 因子名称
    :param date_format: str， 日期格式
    :return: pd.Series, multiindex =[datetime, secid] value = factor
    """

    factor = pd.read_csv(file_path)
    if factor_name is not None:
        factor_col = factor.columns.tolist().index(factor_name)
        factor = factor.iloc[:, [0, 1, factor_col]]
    else:
        factor = factor[factor.columns[:2]]
    factor.columns = ['tradeDate', 'secID', 'factor']
    factor['tradeDate'] = pd.to_datetime(factor['tradeDate'], format=date_format)
    factor = factor.dropna()
    factor = factor[factor['secID'].str.contains(r'^[^<A>]+$$')]  # 去除类似AXXXX的代码(IPO终止)
    if return_biz_day:
        biz_day = dateutils.map_to_biz_day(factor['tradeDate'])
    index = pd.MultiIndex.from_arrays([biz_day.values, factor['secID'].values], names=index_name)
    ret = pd.Series(factor['factor'].values, index=index, name='factor')
    return ret


def adjust_factor_date(factor_raw, start_date, end_date, freq='m'):
    """
    :param factor_raw: pd.DataFrame, multiindex =['tradeDate','secID']
    :param start_date: str/datetime.datetime, start date of factor data
    :param end_date: str/datetime.datetime, end date of factor data
    :param freq: str, optional, tiaocang frequency
    :return: pd.Series, multiindex =[datetime, secid] / pd.DataFrame
    此函数的主要目的是 把原始以报告日为对应日期的因子数据 改成 调仓日为日期（读取对应报告日数据）
    """

    ret = pd.Series()

    # 获取调仓日日期
    tiaocang_date = dateutils.get_pos_adj_date(start_date, end_date, freq=freq)
    report_date = [get_report_date(date, return_biz_day=True) for date in tiaocang_date]

    for i in range(len(tiaocang_date)):
        query = factor_raw.loc[factor_raw.index.get_level_values('tradeDate') == report_date[i]]
        query = query.reset_index().drop('tradeDate', axis=1)
        query['tiaoCangDate'] = [tiaocang_date[i]] * query['secID'].count()
        ret = pd.concat([ret, query], axis=0)
    ret = ret[['tiaoCangDate', 'secID', 'factor']]  # 清理列

    index = pd.MultiIndex.from_arrays([ret['tiaoCangDate'].values, ret['secID'].values],
                                      names=['tiaoCangDate', 'secID'])
    ret = pd.Series(ret['factor'].values, index=index, name='factor')

    return ret


def get_multi_index_data(multi_idx_data, first_idx_name, first_idx_val, sec_idx_name=None, sec_idx_val=None):
    """
    :param multi_idx_data: pd.Series, multi-index =[first_idx_name, sec_idx_name]
    :param first_idx_name: str, first index name of multiIndex series
    :param first_idx_val: str/list/datetime.date, selected value of first index
    :param sec_idx_name: str, second index name of multiIndex series
    :param sec_idx_val: str/list/datetime.date, selected valuer of second index
    :return: pd.Series, selected value with multi-index = [first_idx_name, sec_idx_name]
    """

    if isinstance(first_idx_val, basestring) or isinstance(first_idx_val, datetime.datetime):
        first_idx_val = [first_idx_val]

    data = multi_idx_data.loc[multi_idx_data.index.get_level_values(first_idx_name).isin(first_idx_val)]
    if sec_idx_name is not None:
        if isinstance(sec_idx_val, basestring) or isinstance(sec_idx_val, datetime.date):
            sec_idx_val = [sec_idx_val]
        data = data.loc[data.index.get_level_values(sec_idx_name).isin(sec_idx_val)]
    return data


if __name__ == "__main__":
    path = '..//..//data//return//monthlyReturn.csv'
    factorRaw = get_universe_single_factor(path)
    print adjust_factor_date(factorRaw, '2015-01-05', '2015-12-01')
