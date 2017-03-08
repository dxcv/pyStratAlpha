# -*- coding: utf-8 -*-
# ref 动态情景多因子Alpha模型----因子选股系列研究之八，朱剑涛
# ref https://uqer.io/community/share/57ff3f9e228e5b3658fac3ed

from math import e

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as st
from PyFin.DateUtilities import Date
from PyFin.Utilities import pyFinAssert
from matplotlib.ticker import MultipleLocator, FormatStrFormatter

from pyAlphaStrat.analyzer.factor.cleanData import get_multi_index_data
from pyAlphaStrat.enums import FactorWeightType


class DCAMAnalyzer(object):
    def __init__(self,
                 layer_factor,
                 alpha_factor,
                 sec_return,
                 tiaocang_date,
                 tiaocang_date_window_size=12,
                 save_sec_score=True,
                 factor_weight_type=FactorWeightType.ICWeight,
                 alpha_factor_sign=None):
        self._layerFactor = layer_factor
        self._layerFactorNames = [layer_factor.name for layer_factor in self._layerFactor]
        self._alphaFactor = alpha_factor
        self._alphaFactorNames = [alpha_factor.name for alpha_factor in self._alphaFactor]
        self._secReturn = sec_return
        self._tiaoCangDate = tiaocang_date
        self._startDate = str(Date.fromDateTime(self._tiaoCangDate[0]))
        self._endDate = str(Date.fromDateTime(self._tiaoCangDate[-1]))
        self._tiaoCangDateWindowSize = tiaocang_date_window_size
        pyFinAssert(len(self._tiaoCangDate) > self._tiaoCangDateWindowSize,
                    ValueError,
                    "length of tiaoCangDate must be larger than moving window size")
        self._saveSecScore = save_sec_score
        self._factorWeightType = factor_weight_type
        self._alphaFactorSign = alpha_factor_sign
        if self._factorWeightType == FactorWeightType.EqualWeight:
            pyFinAssert(len(self._alphaFactorSign) == len(self._alphaFactor), ValueError,
                        "length of alpha_factor_sign({0}), does not equal to that of alpha factor({1})".format(
                            len(self._alphaFactorSign), len(self._alphaFactor)))

    @staticmethod
    def get_sec_group(layer_factor, date):
        """
        :param date: datetime, 调仓日
        :param layer_factor: multi index pd.Series, 情景分层因子
        :return: list
        给定某一时间，按分层因子layerFactor把股票分为数量相同的两组（大/小）
        """
        data = get_multi_index_data(layer_factor, 'tiaoCangDate', date)
        # 按分层因子值从小到大排序
        data.sort_values(ascending=True, inplace=True)
        sec_ids = data.index.get_level_values('secID').tolist()
        # 分组,因子值小的哪一组股票为low,高的为high
        group_low = sec_ids[:np.round(len(data)) / 2]
        group_high = sec_ids[np.round(len(data)) / 2:]
        return group_low, group_high

    def get_sec_return(self, sec_ids, date):
        """
        :param sec_ids: list of sec ids
        :param date: datetime, 调仓日
        :return: pd.Series, index = sec ID
        给定某一时间和股票代码列表, 返回前一个调仓日至当前调仓日的股票收益
        """
        data = get_multi_index_data(self._secReturn, 'tiaoCangDate', date, 'secID', sec_ids)
        data = data.reset_index().drop('tiaoCangDate', axis=1)
        data = data.set_index('secID')
        return data

    def get_alpha_factor(self, sec_ids, date):
        """
        :param sec_ids: list of sec ids
        :param date: datetime, 调仓日
        :return: pd.DataFrame, index = sec_ids, col = [alpha factor]
        给定某一时间, 和股票代码列表, 返回alpha因子列表
        """
        ret = pd.DataFrame()
        for i in range(len(self._alphaFactor)):
            data = get_multi_index_data(self._alphaFactor[i], 'tiaoCangDate', date, 'secID', sec_ids)
            data = data.reset_index().drop('tiaoCangDate', axis=1)
            data = data.set_index('secID')
            ret = pd.concat([ret, data], axis=1)
        ret.columns = self._alphaFactorNames
        return ret

    def calc_rank_ic(self, layer_factor):
        """
        :param layer_factor: pd.Series, 分层因子
        :return: pd.DataFrame, index = tiaoCangDate, col = [alpha factor names]
        给定分层因子，计算每个调仓日对应的alpha因子IC
        """
        low = pd.DataFrame(index=self._tiaoCangDate, columns=[self._alphaFactorNames])
        high = pd.DataFrame(index=self._tiaoCangDate, columns=[self._alphaFactorNames])

        for j in range(0, len(self._tiaoCangDate) - 1):  # 对时间做循环，得到每个时间点的rankIC
            date = self._tiaoCangDate[j]
            next_date = self._tiaoCangDate[j + 1]
            group_low, group_high = self.get_sec_group(layer_factor, date)  # 分组
            return_low = self.get_sec_return(group_low, next_date)
            return_high = self.get_sec_return(group_high, next_date)  # 得到下期收益序列
            factor_low = self.get_alpha_factor(group_low, date)
            factor_high = self.get_alpha_factor(group_high, date)  # 得到当期因子序列
            table_low = pd.concat([return_low, factor_low], axis=1)
            table_high = pd.concat([return_high, factor_high], axis=1)
            for k in self._alphaFactorNames:
                tmplow, _ = st.spearmanr(table_low['RETURN'], table_low[k])
                tmphigh, _ = st.spearmanr(table_high['RETURN'], table_high[k])
                low[k][j] = tmplow
                high[k][j] = tmphigh
        low = low.dropna()
        high = high.dropna()
        return low, high

    def get_analysis(self, layer_factor_name=None, save_file=False):
        """
        :param layer_factor_name str, 分层因子名称
        :param save_file,bool save file or not
        :return:  对给定情景因子分层后的股票组合进行的统计分析
        """
        if layer_factor_name is None:
            layer_factor = self._layerFactor[0]
        else:
            layer_factor = self._layerFactor[self._layerFactorNames.index(layer_factor_name)]
        low, high = self.calc_rank_ic(layer_factor)
        result = pd.DataFrame(columns=self._alphaFactorNames, index=np.arange(12))
        for i in self._alphaFactorNames:
            mean_low = np.array(low[i]).mean()
            mean_high = np.array(high[i]).mean()
            std_low = np.array(low[i]).std()
            std_high = np.array(high[i]).std()
            # 均值的t检验, 原假设为两个独立样本的均值相同
            t, p_t = st.ttest_ind(low[i], high[i], equal_var=False)
            # 方差的F检验，原假设为两个独立样本的方差相同
            f, p_f = st.levene(low[i], high[i])
            # 分布的K-S检验，原假设为两个独立样本是否来自同一个连续分布
            ks, p_ks = st.ks_2samp(low[i], high[i])
            result[i] = [mean_low, mean_high, std_low, std_high,
                         mean_low / std_low, mean_high / std_high, t, p_t, f, p_f, ks, p_ks]

        result = result.T
        np.arrays = [['mean', 'mean', 'std', 'std', 'IR', 'IR', 'Two sample t test', 'Two sample t test', 'levene test',
                      'levene test', 'K-S test',
                      'K-S test'],
                     ['low', 'high', 'low', 'high', 'low', 'high', 't', 'p_value', 'f', 'p_value', 'KS', 'p_value']]
        result.columns = pd.MultiIndex.from_tuples(zip(*np.arrays))
        ret = pd.concat([result], axis=1,
                        keys=[layer_factor.name + '分层后因子表现     时间：' + self._startDate + ' -- ' + self._endDate])
        if save_file:
            ret.to_csv('analysis.csv')
        return ret

    @staticmethod
    def calc_layer_factor_distance(percentile):
        """
        :param percentile: float, 个股在分层因子下的分位数, [0,1]
        :return: float, 个股的分层因子上的属性量化分数
        """
        return sigmoid_modif(percentile)

    def calc_layer_factor_quantile_on_date(self, date):
        """
        :param date: datetime, 调仓日
        :return: pd.DataFrame, index=secid, col = layerFactorNames
        """
        ret = pd.DataFrame()
        for layerFactor in self._layerFactor:
            data = get_multi_index_data(layerFactor, 'tiaoCangDate', date)
            sec_ids = data.index.get_level_values('secID').tolist()
            # 由低至高排序
            rank = data.rank(ascending=True)
            rank = rank.divide(len(sec_ids))
            ret = pd.concat([ret, pd.Series(rank.values, index=sec_ids)], axis=1)
        ret.columns = self._layerFactorNames
        return ret

    def calc_alpha_factor_weight_on_date(self, date):
        """
        :param date: datetime, 调仓日
        :return:  pd.DataFrame,  index = [layerFactor], cols= [alpha factor name]
        给定调仓日，计算alpha因子的加权矩阵
        """
        if isinstance(date, basestring):
            date = Date.strptime(date).toDateTime()

        ret_low = pd.DataFrame(columns=self._alphaFactorNames)
        ret_high = pd.DataFrame(columns=self._alphaFactorNames)

        tiao_cang_date_range = self._tiaoCangDate[
                               self._tiaoCangDate.index(date) - self._tiaoCangDateWindowSize: self._tiaoCangDate.index(
                                   date)]

        for layerFactor in self._layerFactor:
            if self._factorWeightType == FactorWeightType.EqualWeight:
                ret_low.loc[layerFactor.name] = self._alphaFactorSign
                ret_high.loc[layerFactor.name] = self._alphaFactorSign
            else:
                low, high = self.calc_rank_ic(layerFactor)
                low_to_use = low.loc[tiao_cang_date_range]
                high_to_use = high.loc[tiao_cang_date_range]
                weight_low = low_to_use.mean(axis=0) / low_to_use.std(axis=0)
                weight_high = high_to_use.mean(axis=0) / high_to_use.std(axis=0)
                ret_low.loc[layerFactor.name] = weight_low.values
                ret_high.loc[layerFactor.name] = weight_high.values

        return ret_low, ret_high

    def calc_alpha_factor_rank_on_date(self, date, factor_low_weight, factor_high_weight):
        """
        :param date, str/datetime, tiaoCangDate
        :param factor_low_weight, pd.DataFrame, see calc_alpha_factor_weight_on_date
        :param factor_high_weight, pd.DataFrame,
        :return:  pd.DataFrame,  index = [layerFactor, secID, low/high], index = layerfactor, col = alpha factor
        给定调仓日，计算secIDs的alpha因子的排位
        """
        ret = pd.DataFrame()
        if isinstance(date, basestring):
            date = Date.strptime(date).toDateTime()
        for layerFactor in self._layerFactor:
            # 分层因子下股票分为两组
            group_low, group_high = self.get_sec_group(layerFactor, date)
            # TODO check why length of factorLow <> group_low
            factor_low = self.get_alpha_factor(group_low, date)
            factor_high = self.get_alpha_factor(group_high, date)
            # 排序的顺序由权重决定
            # 如果权重为正，那么从低到高排序
            # 如果权重为负，那么从高到底排序
            # 加权的时候权重使用绝对值
            factor_low_rank = pd.DataFrame()
            factor_high_rank = pd.DataFrame()
            for alphaFactorName in self._alphaFactorNames:
                flag_low = True if factor_low_weight[alphaFactorName][layerFactor.name] >= 0 else False
                flag_high = True if factor_high_weight[alphaFactorName][layerFactor.name] >= 0 else False
                factor_low_rank_col = factor_low[alphaFactorName].rank(ascending=flag_low, axis=0)
                factor_high_rank_col = factor_high[alphaFactorName].rank(ascending=flag_high, axis=0)
                factor_low_rank = pd.concat([factor_low_rank, factor_low_rank_col], axis=1)
                factor_high_rank = pd.concat([factor_high_rank, factor_high_rank_col], axis=1)
            # multi index DataFrame
            sec_id_index = np.append(factor_low_rank.index, factor_high_rank.index)
            layer_factor_index = [layerFactor.name] * len(sec_id_index)
            high_low_index = ['low'] * len(factor_low_rank.index) + ['high'] * len(factor_high_rank.index)
            factor_rank_array = pd.concat([factor_low_rank, factor_high_rank], axis=0).values
            index = pd.MultiIndex.from_arrays([sec_id_index, layer_factor_index, high_low_index],
                                              names=['secID', 'layerFactor', 'low_high'])
            alpha_factor_rank = pd.DataFrame(factor_rank_array, index=index, columns=self._alphaFactorNames)
            # merge
            ret = pd.concat([ret, alpha_factor_rank], axis=0)
        ret.fillna(ret.median(), inplace=True)
        return ret

    def calc_sec_score_on_date(self, date):
        """
        :param date: datetime, tiaoCangDate
        :return: pd.Series, index = secID, cols = score, industry
        给定调仓日, 返回股票打分列表
        """
        alpha_weight_low, alpha_weight_high = self.calc_alpha_factor_weight_on_date(date)
        alpha_factor_rank = self.calc_alpha_factor_rank_on_date(date, alpha_weight_low, alpha_weight_high)
        layer_factor_quantile = self.calc_layer_factor_quantile_on_date(date)
        sec_ids = layer_factor_quantile.index.tolist()
        ret = pd.Series(index=sec_ids, name=date)
        for secID in sec_ids:
            # 提取secID对应的alphaFactorRank DataFrame, index = [layerFactor, high/low], col = alphaFactor
            factor_rank_matrix = get_multi_index_data(alpha_factor_rank, 'secID', secID)
            weighted_rank = 0.0
            for layerFactor in factor_rank_matrix.index.get_level_values('layerFactor'):
                factor_rank_on_layer_factor = factor_rank_matrix.loc[
                    factor_rank_matrix.index.get_level_values('layerFactor') == layerFactor]
                rank = factor_rank_on_layer_factor.values.flatten()
                low_high = factor_rank_on_layer_factor.index.get_level_values('low_high')
                # 权重取绝对值
                weight = abs(alpha_weight_low.loc[layerFactor].values) if low_high == 'low' else abs(
                    alpha_weight_high.loc[layerFactor].values)
                # normalize
                # weight = [i / weight.sum() for i in weight]
                layer_factor_quantile_to_use = layer_factor_quantile[layerFactor][secID]
                weighted_rank += np.dot(weight, rank) * abs(
                    self.calc_layer_factor_distance(layer_factor_quantile_to_use))
            ret[secID] = weighted_rank

        return ret

    def calc_sec_score(self):
        """
        :param self:
        :return: pd.Series, index = [tiaoCangDate, secID], value = score
        返回所有调仓日的股票打分列表
        """
        date_index = []
        sec_id_index = []
        sec_score_value = []
        for date in self._tiaoCangDate[self._tiaoCangDateWindowSize:]:
            sec_score = self.calc_sec_score_on_date(date)
            date_index += [date] * len(sec_score.values)
            sec_id_index += sec_score.index.tolist()
            sec_score_value += sec_score.values.tolist()

        index = pd.MultiIndex.from_arrays([date_index, sec_id_index], names=['tiaoCangDate', 'secID'])
        ret = pd.Series(sec_score_value, index=index, name='score')
        if self._saveSecScore:
            ret.reset_index().to_csv('sec_score.csv', date_format='%Y-%m-%d')
        return ret


def sigmoid_modif(x):
    """
    :param x: float
    :return: modified sigmoid value given x
    """
    return 10 * (1 / (1 + e ** (-(10 * (x - 0.5)))) - 0.5)


def plot_layer_factor_distance():
    """
    :return: 对calcLayerFactorDistance函数绘图
    """
    x_major_locator = MultipleLocator(0.1)  # 将x主刻度标签设置为 的倍数
    x_major_formatter = FormatStrFormatter('%1.1f')  # 设置x轴标签文本的格式
    y_major_locator = MultipleLocator(1)  # 将y轴主刻度标签设置为 的倍数
    y_major_formatter = FormatStrFormatter('%1.1f')  # 设置y轴标签文本的格式

    x = np.linspace(0, 1, 100)
    y = [sigmoid_modif(i) for i in x]
    plt.plot(x, y)
    plt.title('Layer Factor Scoring Function')
    plt.grid()
    ax = plt.gca()
    ax.xaxis.set_major_locator(x_major_locator)
    ax.xaxis.set_major_formatter(x_major_formatter)
    ax.yaxis.set_major_locator(y_major_locator)
    ax.yaxis.set_major_formatter(y_major_formatter)
    plt.show()


if __name__ == "__main__":
    plot_layer_factor_distance()
