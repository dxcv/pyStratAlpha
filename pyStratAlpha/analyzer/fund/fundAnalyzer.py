# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from pyAlphaStrat.analyzer.performance import perf_stat
from pyAlphaStrat.utils import time_index_slicer


class FundAnalyzer(object):
    def __init__(self, start_date, end_date, fund_return, benchmark_return, tiaocang_date):
        """
        :param start_date: str, start date of analyzer horizon
        :param end_date: str, end date of analyzer horizon
        :param fund_return: pd.DataFrame, index = date, col = fundName, values = non cumul return
        :param benchmark_return: pd.Series, index = date, values = non cumul return
        :param tiaoCangDate; list of str/datetime/pyFin.Date, tiaoCangDates, tiaoCangDate[1]
                                is the real first tiaoCangDate
        :return:
        """
        self._startDate = start_date
        self._endDate = end_date
        self._fundReturn = fund_return
        self._benchmarkReturn = benchmark_return
        self._tiaoCangDate = tiaocang_date

    @staticmethod
    def _calc_perf_stat(fund_return, benchmark_return):
        """
        :param fund_return: pd.DataFrame, index = date, col = fundID
        :param benchmark_return: pd.Series, index = date, value = return
        :return: pd.DataFrame, index = fundID, col = perf stat
        """
        ret = pd.DataFrame()
        perf_sign = pd.Series()
        for secID in fund_return.columns:
            perf, perf_sign = perf_stat(strat_return=fund_return[secID],
                                        benchmark_return=benchmark_return)
            ret = pd.concat([ret, perf], axis=1)

        return ret.transpose(), perf_sign

    @staticmethod
    def _rank_perf_stat(perf_stats, perf_sign):
        """
        :param perf_stats: pd.DataFrame, index = fundID, col = perf stat
        :param perf_sign: pd.Series, index = perfStatName, value = 1/-1
        :return: pd.DataFrame, index = fundID, col = perf stat, value = rank adjusted
        """

        ret = pd.DataFrame()
        for stat in perf_stats.columns:
            flag = True if perf_sign[stat] == 1 else False
            rank = perf_stats[stat].rank(ascending=flag, axis=0)
            ret = pd.concat([ret, rank], axis=1)
        ret.columns = perf_stats.columns
        return ret

    def calc_fund_score_on_date(self, tiaocang_start_date, tiaocang_end_date):
        """
        :param tiaocang_start_date: str, start date of holding period
        :param tiaocang_end_date: str, end date of holding period
        :return: pd.Series, index = fundID, value = score
        """
        fund_return = time_index_slicer(self._fundReturn, tiaocang_start_date, tiaocang_end_date)
        # TODO drop out nan cols
        benchmark_return = time_index_slicer(self._benchmarkReturn, tiaocang_start_date, tiaocang_end_date)

        fund_perf_stat, fund_perf_stat_sign = self._calc_perf_stat(fund_return=fund_return,
                                                                   benchmark_return=benchmark_return)

        rank = self._rank_perf_stat(fund_perf_stat, fund_perf_stat_sign)
        fund_score = rank.sum(axis=1)
        return fund_score

    def calc_fund_score(self):
        """
        :return: pd.Series,  Multiindex = [tiaoCangDate, fundID]
        """
        # TODO

        ret = pd.Series()

        for i in range(len(self._tiaoCangDate) - 1):
            tiaocang_start_date = self._tiaoCangDate[i]
            tiaocang_end_date = self._tiaoCangDate[i + 1]
            fund_score = self.calc_fund_score_on_date(tiaocang_start_date, tiaocang_end_date)
            np.arrays = [[tiaocang_end_date], fund_score.index.values]
            index = pd.MultiIndex.from_tuples(zip(*np.arrays), names=['tiaoCangDate', 'secID'])
            fund_score = pd.Series(fund_score, index=index)
            ret = pd.concat([ret, fund_score], axis=0)

        return ret
