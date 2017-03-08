# -*- coding: utf-8 -*-

# 对净值曲线做分析
import empyrical
import matplotlib.pyplot as plt
import pandas as pd
from PyFin.Utilities import pyFinAssert
from empyrical import cum_returns
from pyfolio import utils

from pyAlphaStrat.enums import FreqType
from pyAlphaStrat.enums import ReturnType
from pyAlphaStrat.utils import convert_to_non_cumul_return
from pyAlphaStrat.utils import fig_style

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

_DictSimpleStatFuncs = {
    empyrical.annual_return: 1,
    empyrical.max_drawdown: -1,
    empyrical.calmar_ratio: 1,
    empyrical.sharpe_ratio: 1,

}

_DictBenchmarkStatFuncs = {
    empyrical.information_ratio: 1,
    empyrical.alpha: 1,
    empyrical.beta: 1,
}


def regroup_by_re_balance_freq(data, re_balance_freq=FreqType.EOM):
    """
    :param data: pd.DataFrame, index = dates
    :param re_balance_freq: str, optional, rebalance frequncy = daily/monthly/yearly
    :return: pd.group object
    """
    if isinstance(data, pd.Series):
        data = pd.DataFrame(data)
    if re_balance_freq == FreqType.EOD:
        ret = data.groupby([lambda x: x.year, lambda x: x.month, lambda x: x.day])
    elif re_balance_freq == FreqType.EOM:
        ret = data.groupby(pd.TimeGrouper(freq='M'))
    elif re_balance_freq == FreqType.EOY:
        ret = data.groupby(pd.TimeGrouper(freq='A'))
    else:
        raise ValueError('regroup_by_re_balance_freq: no-recognize re-balance frequency')
    return ret


def ptf_re_balance(return_dict, margin_prop=0.0, re_balance_freq=FreqType.EOM):
    """
    :param return_dict: dict, returnName: [returnData, ReturnType]
    :param margin_prop: float, optional, proportion of the init ptf that is allocated to futures account
    :param re_balance_freq: str, optional, rebalance frequncy = daily/monthly/yearly
    :return: pd.Series, daily cumul returns of hedged ptf
    """
    strat_return = return_dict['stratReturn'][0]
    strat_return_type = return_dict['stratReturn'][1]
    benchmark_return = return_dict['benchmarkReturn'][0]
    benchmark_return_type = return_dict['benchmarkReturn'][1]

    strat_return = empyrical.cum_returns(strat_return,
                                         starting_value=1.0) if strat_return_type == ReturnType.NonCumul \
        else strat_return
    benchmark_return = empyrical.cum_returns(benchmark_return,
                                             starting_value=1.0) if benchmark_return_type == ReturnType.NonCumul \
        else benchmark_return

    pyFinAssert(0 <= margin_prop <= 1.0, ValueError, " margin prop must be between 0 and 1")
    hedged_ptf_return = pd.Series()
    # merge strat and index returns together
    return_data = pd.concat([strat_return, benchmark_return], axis=1, join_axes=[strat_return.index])
    return_data.columns = ['strategy', 'benchmark']
    return_data.index = pd.to_datetime(return_data.index)
    pyFinAssert(return_data.isnull().values.any() == False, ValueError, " returnData has NaN values")
    regroup_total_return = regroup_by_re_balance_freq(return_data, re_balance_freq)

    # first date is a balance date
    re_balance_base_nav = 1.0
    norm_base_return = return_data.iloc[0]
    for name, group in regroup_total_return:
        # compute the hedged return
        norm_strat_return = group['strategy'] / norm_base_return['strategy']
        norm_benchmark_return = group['benchmark'] / norm_base_return['benchmark']
        hedged_return = (1 + (norm_strat_return - norm_benchmark_return) * (1 - margin_prop)) * re_balance_base_nav

        # update the re_balance base NPV
        re_balance_base_nav = hedged_return.iloc[-1]

        # update norm base return
        norm_base_return = group.iloc[-1]

        # merge into ptfValue
        hedged_ptf_return = pd.concat([hedged_ptf_return, hedged_return], axis=0)

    hedged_ptf_return.name = 'hedgedPtfReturn'

    return hedged_ptf_return


def print_perf_stat_by_year(ptf_return, ptf_return_type):
    """
    :param ptf_return: daily cumul/non-cumul returns of ptf
    :param ptf_return_type:
    :return: perf_stat by years
    """
    # convert cumul return into daily return
    # it is a bit stupid because empyrical only accept non-cumul return
    daily_return = convert_to_non_cumul_return(ptf_return) if ptf_return_type == ReturnType.Cumul else ptf_return

    # regroup the data into years
    daily_return_by_year = regroup_by_re_balance_freq(daily_return, re_balance_freq=FreqType.EOY)

    perf_stats = pd.Series()
    for name, group in daily_return_by_year:
        stat, stat_sign = perf_stat(group[group.columns[0]])
        stat.name = name.year
        perf_stats = pd.concat([perf_stats, stat], axis=1)

    return perf_stats.dropna(axis=1)


def perf_stat(strat_return, benchmark_return=None):
    stat = pd.Series()
    stat_sign = pd.Series()

    for stat_func in _DictSimpleStatFuncs.keys():
        stat[stat_func.__name__] = stat_func(strat_return)
        stat_sign[stat_func.__name__] = _DictSimpleStatFuncs[stat_func]

    if benchmark_return is not None:
        for stat_func in _DictBenchmarkStatFuncs.keys():
            stat[stat_func.__name__] = stat_func(strat_return,
                                                 benchmark_return)
            stat_sign[stat_func.__name__] = _DictBenchmarkStatFuncs[stat_func]
    return stat, stat_sign


def plot_alpha_curve(return_dict):
    """
    :param return_dict: dict, returnName: [returnData, ReturnType]
    :return:
    """

    strat_return = return_dict['stratReturn'][0]
    strat_return_type = return_dict['stratReturn'][1]
    benchmark_return = return_dict['benchmarkReturn'][0]
    benchmark_return_type = return_dict['benchmarkReturn'][1]
    ptf_return = return_dict['ptfReturn'][0]
    ptf_return_type = return_dict['ptfReturn'][1]

    strat_return = cum_returns(strat_return,
                               starting_value=1.0) if strat_return_type == ReturnType.NonCumul else strat_return
    benchmark_return = cum_returns(benchmark_return,
                                   starting_value=1.0) if benchmark_return_type == ReturnType.NonCumul \
        else benchmark_return
    ptf_return = cum_returns(ptf_return, starting_value=1.0) if ptf_return_type == ReturnType.NonCumul else ptf_return

    data = pd.concat([ptf_return, strat_return, benchmark_return], join_axes=[strat_return.index], axis=1)
    # 如果缺失起始数据, 设置为1.0 （起始净值）
    data = data.fillna(1.0)
    data.columns = [u'策略对冲收益', u'策略未对冲收益', u'指数收益']
    ax = data.plot(figsize=(16, 6), title=u'策略收益演示图')
    fig_style(ax, [u'策略对冲净值', u'策略未对冲净值', u'指数收益'], x_label=u'交易日', y_label=u'净值',
              legend_loc='upper left')
    plt.show()


def strat_evaluation(return_dict,
                     re_balance_freq=FreqType.EOM,
                     margin_prop=0.0,
                     need_plot=True):
    """
    :param return_dict: dict, returnName: [returnData, ReturnType]
    :param margin_prop:
    :param re_balance_freq: str, optional, rebalance frequncy = daily/monthly/yearly
    :param need_plot: bool, optional, whether to plot the strategy/benchmark/hedged ptf npv
    :return: print out the perf stat table by years
    """

    ptf_return = ptf_re_balance(return_dict=return_dict, margin_prop=margin_prop, re_balance_freq=re_balance_freq)
    perf_stats = print_perf_stat_by_year(ptf_return, ReturnType.Cumul)

    utils.print_table(perf_stats, name='Performance statistics for hedged portfolio',
                      fmt='{0:.4f}')

    perf_stats_strat = print_perf_stat_by_year(return_dict['stratReturn'][0], return_dict['stratReturn'][1])
    utils.print_table(perf_stats_strat, name='Performance statistics for unhedged portfolio',
                      fmt='{0:.4f}')

    ptf_return_dict = {'ptfReturn': [ptf_return, ReturnType.Cumul]}
    return_dict = dict(return_dict, **ptf_return_dict)
    if need_plot:
        plot_alpha_curve(return_dict=return_dict)
    return
