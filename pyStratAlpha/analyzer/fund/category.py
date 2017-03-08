# -*- coding: utf-8 -*-

import pandas as pd
import tushare as ts

from pyAlphaStrat.utils.misc import pickle_dump_data
from pyAlphaStrat.utils.misc import pickle_load_data

_indexUnd = ['50', '100', '300', '500', '800', '1000']
_indexIncludeKeyWord = [u'指数', u'增强']
_indexExcludeKeyWord = [u'ETF联接']

_quantIncludeKeyWord = [u'量化', u'阿尔法', u'多策略']
_quantExcludeKeyWord = [u'增强']  # 去除指数增强

_pklIndexFundNAV = 'indexFundNav.pkl'
_pklQuantFundNAV = 'quantFundNav.pkl'
_pkl_index_fund_id = 'indexFundID.pkl'
_pkl_quant_fund_id = 'quantFundID.pkl'


def map_to_index_und(fund_name):
    """
    :param fund_name: str, name of the fund
    :return: str, 跟踪指数标的
    """
    switcher = {
        '50': u'上证50',
        '100': u'中证100',
        '300': u'沪深300',
        '500': u'中证500',
        '800': u'中证800',
        '1000': u'中证1000'
    }
    return switcher.get(file(str.isdigit, fund_name), u'其他')


# 所有指数以及指数增强基金列表
def get_index_open_fund(pkl_file=None):
    """
    :param pkl_file:
    :return: pd.DataFrame index= fundID, col = [fundName, indexUnd]
    """
    equity_fund = ts.get_nav_open(fund_type='equity')
    equity_fund = equity_fund[['symbol', 'sname']]
    index_fund = equity_fund[equity_fund['sname'].str.contains(_indexIncludeKeyWord[0]) |
                             equity_fund['sname'].str.contains(_indexIncludeKeyWord[1])]

    # 去除A类
    index_fund = index_fund[~index_fund['sname'].str.endswith('A')]
    # 去除ETF链接
    index_fund = index_fund[~index_fund['sname'].str.contains(_indexExcludeKeyWord[0])]
    # 添加跟踪标的
    index_fund['sname'] = index_fund['sname'].apply(lambda x: x.encode('utf-8'))
    index_fund['indexUnd'] = index_fund['sname'].apply(map_to_index_und)
    index_fund.columns = ['fundID', 'fundName', 'indexUnd']
    index_fund = index_fund.set_index('fundID')

    if pkl_file is not None:
        pickle_dump_data(index_fund, pkl_file)

    return index_fund


# 所有量化主动基金
def get_quant_open_fund(pkl_file=None):
    """
    :param pkl_file:
    :return: pd.DataFrame [fundID, fundName, indexUnd]
    """
    equity_fund = ts.get_nav_open(fund_type='equity')
    equity_fund = equity_fund[['symbol', 'sname']]
    quant_equity_fund = equity_fund[equity_fund['sname'].str.contains(_quantIncludeKeyWord[0]) |
                                    equity_fund['sname'].str.contains(_quantIncludeKeyWord[1]) |
                                    equity_fund['sname'].str.contains(_quantIncludeKeyWord[2])]

    mix_fund = ts.get_nav_open(fund_type='mix')
    mix_fund = mix_fund[['symbol', 'sname']]
    quant_mix_fund = mix_fund[mix_fund['sname'].str.contains(_quantIncludeKeyWord[0]) |
                              mix_fund['sname'].str.contains(_quantIncludeKeyWord[1]) |
                              mix_fund['sname'].str.contains(_quantIncludeKeyWord[2])]

    quant_fund = pd.concat([quant_equity_fund, quant_mix_fund], axis=0)
    # 去除A类
    quant_fund = quant_fund[~quant_fund['sname'].str.endswith('A')]
    quant_fund = quant_fund[~quant_fund['sname'].str.contains(_quantExcludeKeyWord[0])]
    quant_fund['sname'] = quant_fund['sname'].apply(lambda x: x.encode('utf-8'))
    quant_fund.columns = ['fundID', 'fundName']
    quant_fund = quant_fund.set_index(['fundID'])

    if pkl_file is not None:
        pickle_dump_data(quant_fund, pkl_file)

    return quant_fund


def get_fund_nav(fund_id, start_date, end_date, pkl_file=None):
    """
    :param fund_id: list
    :param start_date: str, start date of query
    :param end_date: str, end date of query
    :param pkl_file:
    :return:  pd.DataFrame, index = date, col = fund_id, values = cumul NAV
    """
    ret = pd.DataFrame()
    for fund in fund_id:
        fund_nav = ts.get_nav_history(fund, start_date, end_date)
        # 取累计净值数据
        if fund_nav is not None:
            fund_nav = fund_nav['total']
            fund_nav.name = fund
            ret = pd.concat([ret, fund_nav], axis=1)
        else:
            continue

    if pkl_file is not None:
        pickle_dump_data(ret, pkl_file)

    return ret


def get_index_and_quant_fund_nav_main(start_date,
                                      end_date,
                                      update_index_fund_id=False,
                                      update_quant_fund_id=False):
    index_fund_id = get_index_open_fund(pkl_file=_pkl_index_fund_id) if update_index_fund_id else pickle_load_data(
        _pkl_index_fund_id)
    quant_fund_id = get_quant_open_fund(pkl_file=_pkl_quant_fund_id) if update_quant_fund_id else pickle_load_data(
        _pkl_quant_fund_id)

    index_fund_nav = get_fund_nav(index_fund_id.index.tolist(), start_date, end_date, pkl_file=_pklIndexFundNAV)
    quant_fund_nav = get_fund_nav(quant_fund_id.index.tolist(), start_date, end_date, pkl_file=_pklQuantFundNAV)

    return index_fund_nav, quant_fund_nav


if __name__ == "__main__":
    print get_index_and_quant_fund_nav_main(start_date='2015-01-01',
                                            end_date='2017-01-01',
                                            update_index_fund_id=True,
                                            update_quant_fund_id=True)
