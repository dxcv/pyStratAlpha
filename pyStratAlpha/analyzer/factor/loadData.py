# -*- coding: utf-8 -*-
import os
import zipfile

import pandas as pd
from PyFin.Utilities import pyFinAssert

from pyAlphaStrat.analyzer.factor.cleanData import adjust_factor_date
from pyAlphaStrat.analyzer.factor.cleanData import get_multi_index_data
from pyAlphaStrat.analyzer.factor.cleanData import get_universe_single_factor
from pyAlphaStrat.analyzer.factor.norm import normalize
from pyAlphaStrat.enums.factor import FactorNormType
from pyAlphaStrat.utils.dateutils import get_pos_adj_date

_factorPathDict = {
    'MV': ['..//..//data//factor//FactorDataMonthly.csv', 'm'],  # 总市值, 月度频率 -- 分层因子
    'BP_LF': ['..//..//data//factor//FactorDataMonthly.csv', 'm'],  # 最近财报的净资产/总市值, 季度频率 -- 分层因子/alpha测试因子
    'EquityGrowth_YOY': ['..//..//data//factor//FactorDataQuarterly.csv', 'q'],  # 净资产同比增长率, 季度频率 -- 分层因子
    'ROE': ['..//..//data//factor//FactorDataQuarterly.csv', 'q'],  # 净资产收益率, 季度频率 -- 分层因子
    'STDQ': ['..//..//data//factor//FactorDataMonthly.csv', 'm'],  # 季度日均换手率, 月度频率 -- 分层因子

    'EP2_TTM': ['..//..//data//factor//FactorDataMonthly.csv', 'm'],  # 剔除非经常性损益的过去12 个月净利润/总市值, 季度频率 -- alpha测试因子
    'SP_TTM': ['..//..//data//factor//FactorDataMonthly.csv', 'm'],  # 过去12 个月总营业收入/总市值, 季度频率 -- alpha测试因子
    'GP2Asset': ['..//..//data//factor//FactorDataQuarterly.csv', 'q'],  # 销售毛利润/总资产, 季度频率 -- alpha测试因子
    'PEG': ['..//..//data//factor//FactorDataMonthly.csv', 'm'],  # TTM PE/预测未来2 年净利润复合增长率, 月度频率 -- alpha测试因子 朝阳永续数据
    'ProfitGrowth_Qr_YOY': ['..//..//data//factor//FactorDataQuarterly.csv', 'q'],  # 净利润增长率（季度同比）, 季度频率 - alpha测试因子
    'TO_adj': ['..//..//data//factor//FactorDataMonthly.csv', 'm'],  # 月度换手率, 月度频率 - alpha测试因子
    'PPReversal': ['..//..//data//factor//FactorDataMonthly.csv', 'm'],  # 5 日均价/60 日成交均价, 月度频率 - alpha测试因子

    'RETURN': ['..//..//data//return//monthlyReturn.csv', 'm'],  # 收益,月度频率
    'INDUSTRY': ['..//..//data//industry//codeSW.csv', 'm'],  # 申万行业分类,月度频率
    'IND_WGT': ['..//..//data//industry//IndustryWeight.csv', 'm']  # 中证500股票池内按照申万一级行业分类统计的行业权重,月度频率
}


@staticmethod
def get_data_div(save_csv_path, numerator='NAV', denominator='CAP', freq='m'):
    """
    :param save_csv_path: str, save path and name of divide result
    :param numerator: str, optional, name of the numerator factor
    :param denominator: str, optional, name of the denominator factor
    :param freq: str, optional, the frequency of the data
    :return: DataFrame, the divide result
    """

    def get_new_factor_series(data, freqs):
        rets = adjust_factor_date(data,
                                  data.index.levels[0][0],
                                  data.index.levels[0][-1],
                                  freqs)
        rets.index.names = ['tradeDate', 'secID']
        return rets

    numerator_data = get_universe_single_factor(_factorPathDict[numerator][0])
    denominator_data = get_universe_single_factor(_factorPathDict[denominator][0])

    if _factorPathDict[numerator][1] == freq:
        numerator_data_adj = numerator_data
    else:
        numerator_data_adj = get_new_factor_series(numerator_data, freq)

    if _factorPathDict[denominator][1] == freq:
        denominator_data_adj = denominator_data
    else:
        denominator_data_adj = get_new_factor_series(denominator_data, freq)

    returns = numerator_data_adj.divide(denominator_data_adj, axis='index')
    returns.to_csv(save_csv_path)
    return returns


class FactorLoader(object):
    def __init__(self,
                 start_date,
                 end_date,
                 factor_norm_dict,
                 freq='m',
                 zip_path="..//..//data",
                 factor_path_dict=_factorPathDict,
                 date_format='%Y%m%d'):
        """
        :param start_date: str/datetime.datetime, 提取因子数据的开始日期
        :param end_date: str/datetime.datetime, 提取因子数据的结束日期
        :param factor_norm_dict: dict, {factorName: factorNormType}
        :param freq: str, optional, 因子数据的频率
        :param zip_path: str, optional, 数据文件压缩包地址
        :param date_format: str, optional, 数据文件中时间格式
        :return: class， 存储清理后的因子数据
        """
        self._startDate = start_date
        self._endDate = end_date
        self._factorNormDict = factor_norm_dict
        self._factorNames = factor_norm_dict.keys()
        self._nbFactor = len(factor_norm_dict)
        self._freq = freq
        self._tiaocangDate = []
        # 由于因子csv文件较大,所以默认存储为压缩格式的文件, 第一次使用时自动解压缩
        self._unzip_csv_files(zip_path)
        self._factorPathDict = factor_path_dict
        self._dateFormat = date_format

    @staticmethod
    def _unzip_csv_files(zip_path):
        """
        :param zip_path: str, 因子数据压缩包路径
        :return:
        解压缩因子数据压缩包，压缩包中尚未解压到目标文件夹中的文件将被解压
        """
        zip_file = zipfile.ZipFile(os.path.join(zip_path, "data.zip"), "r")
        for name in zip_file.namelist():
            name = name.replace('\\', '/')
            # 检查文件夹是否存在,新建尚未存在的文件夹
            if name.endswith("/"):
                ext_dir = os.path.join(zip_path, name)
                if not os.path.exists(ext_dir):
                    os.mkdir(ext_dir)
            # 检查数据文件是否存在，新建尚未存在的数据文件
            else:
                ext_filename = os.path.join(zip_path, name)
                ext_dir = os.path.dirname(ext_filename)
                if not os.path.exists(ext_dir):
                    os.mkdir(ext_dir)
                if not os.path.exists(ext_filename):
                    outfile = open(ext_filename, 'wb')
                    outfile.write(zip_file.read(name))
                    outfile.close()
        return

    def get_tiaocang_date(self):
        return get_pos_adj_date(self._startDate, self._endDate, freq=self._freq)

    def get_factor_data(self):
        returns = pd.Series()
        for name in self._factorNames:
            path_to_use = self._factorPathDict[name][0]
            original_freq = self._factorPathDict[name][1]
            if original_freq != self._freq:
                factor_raw = get_universe_single_factor(path_to_use, factor_name=name, date_format=self._dateFormat)
                factors = adjust_factor_date(factor_raw, self._startDate, self._endDate, self._freq)
            else:
                factor_raw = get_universe_single_factor(path_to_use, index_name=['tiaoCangDate', 'secID'],
                                                        factor_name=name,
                                                        date_format=self._dateFormat)
                factor_raw = factor_raw.loc[factor_raw.index.get_level_values('tiaoCangDate') >= self._startDate]
                factors = factor_raw.loc[factor_raw.index.get_level_values('tiaoCangDate') <= self._endDate]
            factors.name = name
            returns[name] = factors
        return returns

    @staticmethod
    def normalize_single_factor_data(factors, industries=None, caps=None):
        """
        :param factors: pd.Series, multi index = [tiaoCangDate, secID], value = factors
        :param industries:
        :param caps:
        :return: 去极值、中性化、标准化的因子
        """
        returns = pd.Series(name=factors.name)
        tiaocang_date = sorted(set(factors.index.get_level_values('tiaoCangDate')))
        for date in tiaocang_date:
            factor_to_use = get_multi_index_data(factors, 'tiaoCangDate', date)
            industry_to_use = get_multi_index_data(industries, 'tiaoCangDate',
                                                   date) if industries is not None else None
            cap_to_use = get_multi_index_data(caps, 'tiaoCangDate', date) if caps is not None else None
            data_normed = normalize(factor_to_use, industry_to_use, cap_to_use)
            returns = returns.append(data_normed)

        # save in multi index format
        index = pd.MultiIndex.from_tuples(returns.index, names=['tiaoCangDate', 'secID'])
        returns = pd.Series(data=returns.values, index=index, name=factors.name)
        return returns

    def get_norm_factor_data(self):
        factor_data = self.get_factor_data()
        for name in self._factorNames:
            if self._factorNormDict[name][0] == FactorNormType.IndustryAndCapNeutral:
                pyFinAssert(('INDUSTRY' in self._factorNames and 'MV' in self._factorNames),
                            ValueError,
                            'Failed to neutralize because of missing industry and cap data')
                factor_data[name] = self.normalize_single_factor_data(factor_data[name],
                                                                      industries=factor_data['INDUSTRY'],
                                                                      caps=factor_data['MV'])
            elif self._factorNormDict[name][0] == FactorNormType.IndustryNeutral:
                pyFinAssert(('INDUSTRY' in self._factorNames),
                            ValueError,
                            'Failed to neutralize because of missing industry')
                factor_data[name] = self.normalize_single_factor_data(factor_data[name],
                                                                      industries=factor_data['INDUSTRY'])

        return factor_data


if __name__ == "__main__":
    factor = FactorLoader('2015-01-05',
                          '2015-12-30',
                          {'MV': FactorNormType.Null,
                           'INDUSTRY': FactorNormType.Null,
                           'ROE': FactorNormType.IndustryAndCapNeutral,
                           'RETURN': FactorNormType.IndustryAndCapNeutral})
    ret = factor.get_norm_factor_data()
    print ret['RETURN']
