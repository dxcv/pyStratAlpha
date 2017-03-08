# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import pandas as pd
from PyFin.DateUtilities import Calendar
from PyFin.DateUtilities import Date
from PyFin.api.DateUtilities import bizDatesList
from matplotlib.pyplot import *

from pyAlphaStrat.analyzer.factor import get_multi_index_data
from pyAlphaStrat.analyzer.performance import strat_evaluation
from pyAlphaStrat.enums import DataSource
from pyAlphaStrat.enums import FreqType
from pyAlphaStrat.enums import ReturnType
from pyAlphaStrat.utils import WindMarketDataHandler

plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


class Portfolio(object):
    """
    用以处理alpha选股后的净值计算和绘图等问题
    等Algo-Trading package有动态universe功能后,此类便可以退休了
    """

    def __init__(self,
                 sec_selected,
                 end_date,
                 initial_capital=1000000000.0,
                 filter_return_on_tiaocang_date=0.09,
                 data_source=DataSource.WIND,
                 benchmark_sec_id='000300.SH',
                 re_balance_freq=FreqType.EOM):
        """
        :param sec_selected: pd.DataFrame, multi index = [tiaoCangDate, secID] value=[weight, industry]
        :param end_date: last evaludation date after last tiaoCangDate
        :param initial_capital: float, init cash to invest
        :param filter_return_on_tiaocang_date: float, return threshhold, sec id with return higher than it on tiaocang
        date will be filtered out
        :param data_source: enum, source to read price data
        :param benchmark_sec_id: str, benchmakr sec id used to compute alpha return
        :return:
        """
        self._secSelected = sec_selected
        self._initialCapital = initial_capital
        self._tiaoCangDate = sorted(set(self._secSelected.index.get_level_values('tiaoCangDate')))
        self._tiaoCangDate.append(end_date)
        self._tiaoCangDate = pd.to_datetime(self._tiaoCangDate)
        self._filterReturnOnTiaoCangDate = filter_return_on_tiaocang_date
        self._dataSource = data_source
        self._benchmarkSecID = benchmark_sec_id
        self._rebalanceFreq = re_balance_freq

    def _get_sec_price_between_tiaocang_date(self, tiaocang_start_date, tiaocang_end_date):
        tiaocang_data = get_multi_index_data(self._secSelected, 'tiaoCangDate', tiaocang_start_date)
        sec_ids = tiaocang_data.index.get_level_values('secID').tolist()
        date = bizDatesList('China.SSE', tiaocang_start_date, tiaocang_end_date)
        if self._dataSource == DataSource.WIND:
            price_data = WindMarketDataHandler.get_sec_price_on_date(start_date=date[0],
                                                                     end_date=date[-1],
                                                                     sec_ids=sec_ids)
        else:
            raise NotImplementedError
        return price_data

    @staticmethod
    def _get_sec_price_on_date(data, date):
        price = data.loc[date]
        price.name = 'price'
        return price

    def _get_weight_on_date(self, date):
        weight = get_multi_index_data(self._secSelected, 'tiaoCangDate', date)
        weight = weight.reset_index().set_index('secID')
        weight = weight.drop(['tiaoCangDate'], axis=1)
        filters = self._filter_sec_on_tiaocang_date(date, weight.index.tolist())
        filter_weight = self._update_weight_after_filter(weight, filters)
        return filter_weight

    def _filter_sec_on_tiaocang_date(self, tiaocang_date, sec_id):
        sse_cal = Calendar('China.SSE')
        tiaocang_date_prev = sse_cal.advanceDate(Date.strptime(str(tiaocang_date)[:10]), '-1b').toDateTime()
        tiaocang_date_prev2 = sse_cal.advanceDate(Date.strptime(str(tiaocang_date)[:10]), '-2b').toDateTime()
        price_data = WindMarketDataHandler.get_sec_price_on_date(start_date=tiaocang_date_prev2, end_date=tiaocang_date,
                                                                 sec_ids=sec_id)
        price_data = price_data.transpose()
        price_data.index.name = 'sec_id'
        # 去除涨幅过大可能买不到的
        price_data['returnFilter'] = price_data[tiaocang_date] / price_data[
            tiaocang_date_prev] > 1 + self._filterReturnOnTiaoCangDate
        # 去除有NaN的， 新股
        price_data['ipoFilter'] = pd.isnull(
            price_data[tiaocang_date] * price_data[tiaocang_date_prev] * price_data[tiaocang_date_prev2])
        # 去除停牌的，此处判断标准就是连续三天收盘价格一样
        price_data['tingpaiFilter'] = ((price_data[tiaocang_date] == price_data[tiaocang_date_prev]) & (
            price_data[tiaocang_date_prev] == price_data[tiaocang_date_prev2]))

        price_data['filters'] = 1 - (1 - price_data['returnFilter']) * (1 - price_data['ipoFilter']) * (
            1 - price_data['tingpaiFilter'])

        return price_data['filters']

    def _update_weight_after_filter(self, weight, filters):
        filter_weight = pd.concat([weight, filters], join_axes=[weight.index], axis=1)
        ret = pd.DataFrame()
        for name, group in filter_weight.groupby(self._secSelected.columns[1]):
            group = group.copy()
            total_weight = group['weight'].sum()
            total_sec = group['weight'].count()
            nb_sec_filtered = group['filters'].sum()
            if nb_sec_filtered == 0:
                ret = pd.concat([ret, group], axis=0)
                continue
            else:
                adj_weight = total_weight / (total_sec - nb_sec_filtered) if total_sec > nb_sec_filtered else 0
                group.loc[group['filters'] == 1, 'weight'] = 0.0
                group.loc[group['filters'] == 0, 'weight'] = adj_weight
                ret = pd.concat([ret, group], axis=0)

        return ret

    @staticmethod
    def _get_quantity(init_ptf_value, weight, price):
        # concat weight and price
        ret = pd.concat([weight, price], join_axes=[weight.index], axis=1)
        ret.loc[ret['weight'] > 0, 'quantity'] = init_ptf_value * ret['weight'] / ret['price']
        ret.loc[ret['weight'] == 0, 'quantity'] = 0
        ret['quantity'] = ret['quantity'].apply(int)
        return ret['quantity']

    def _calc_ptf_value_between_tiaocang_date(self, init_ptf_value, tiaocang_start_date, tiaocang_end_date):
        # get price date table between tiaoCangDate
        price_data = self._get_sec_price_between_tiaocang_date(tiaocang_start_date, tiaocang_end_date)

        # get price table at tiaoCangDate
        price = self._get_sec_price_on_date(price_data, tiaocang_start_date)

        # get quantity series at tiaoCangDate
        weight = self._get_weight_on_date(tiaocang_start_date)
        # weight.to_csv('weight.csv', encoding='gbk')
        quantity = self._get_quantity(init_ptf_value, weight, price)

        # loop over all trade dates to calc ptf value
        trade_date_list = price_data.index.get_level_values('tradeDate').tolist()
        ret = pd.Series(index=trade_date_list)
        ret.loc[trade_date_list[0]] = init_ptf_value
        for date in trade_date_list[1:]:
            price = self._get_sec_price_on_date(price_data, date)
            ret[date] = np.sum(quantity * price)

        return ret

    def calc_ptf_value_curve(self):
        ret = pd.Series()
        for i in range(len(self._tiaoCangDate) - 1):
            tiaocang_start_date = self._tiaoCangDate[i]
            tiaocang_end_date = self._tiaoCangDate[i + 1]
            init_ptf_value = self._initialCapital if i == 0 else ret.values[-1]
            ptf_curve = self._calc_ptf_value_between_tiaocang_date(init_ptf_value, tiaocang_start_date,
                                                                   tiaocang_end_date)
            ret = pd.concat([ret, ptf_curve], axis=0)

        # normalize
        ret = ret.drop_duplicates()
        ret = ret / ret[0]
        ret.index = pd.to_datetime(ret.index)
        return ret

    def evaluate_ptf_return(self):
        strat_return = self.calc_ptf_value_curve()
        benchmark_return = WindMarketDataHandler.get_sec_return_on_date(sec_ids=[self._benchmarkSecID],
                                                                        start_date=strat_return.index.tolist()[0],
                                                                        end_date=strat_return.index.tolist()[-1],
                                                                        is_cumul=True)
        benchmark_return = benchmark_return[self._benchmarkSecID]
        benchmark_return.index = pd.to_datetime(benchmark_return.index)
        strat_evaluation(return_dict={'stratReturn': [strat_return, ReturnType.Cumul],
                                      'benchmarkReturn': [benchmark_return, ReturnType.Cumul]},
                         re_balance_freq=self._rebalanceFreq)

        return
