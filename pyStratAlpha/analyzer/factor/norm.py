# -*- coding: utf-8 -*-
# ref: https://uqer.io/community/share/55ff6ce9f9f06c597265ef04
import numpy as np
import pandas as pd
from PyFin.Utilities import pyFinWarning
from sklearn.linear_model import LinearRegression


def winsorize(factors, nb_std_or_quantile=3):
    """
    :param factors: pd.Series, 原始截面因子
    :param nb_std_or_quantile: int or list, optional, 如果是int, 则代表number of std, 如果是list[0.025,0.975] 则使用quantile作为极值判断的标准
    :return: pd.Series, 去极值化后的因子
    """

    factors = factors.copy()
    if isinstance(nb_std_or_quantile, int):
        median = factors.median()
        std = factors.std()
        factors[factors < median - nb_std_or_quantile * std] = median - nb_std_or_quantile * std
        factors[factors > median + nb_std_or_quantile * std] = median + nb_std_or_quantile * std
    elif isinstance(nb_std_or_quantile, list) and len(nb_std_or_quantile) == 2:
        q = factors.quantile(nb_std_or_quantile)
        factors[factors < q.iloc[0]] = q.iloc[0]
        factors[factors > q.iloc[1]] = q.iloc[1]
    else:
        raise ValueError('nb_std_or_quantile should be list or int type')
    return factors


def standardize(factors):
    """
    :param factors: pd.Series, 原始截面因子
    :return: pd.Series, 标准化后的因子  (x - mean)/std

    """
    factors = factors.copy()
    mean = factors.mean()
    std = factors.std()
    ret = factors.apply(lambda x: (x - mean) / std)
    return ret


def get_industry_matrix(industries, mkt_cap=None):
    """
    :param industries: pd.Series, index = secID, value = 行业名称
    :param mkt_cap: pd.Series, index = secID, value = 市值
    :return: numpy.matrix, 行业虚拟矩阵，see alphaNote
    """
    sec_ids = industries.index.tolist()
    nb_sec_id = len(sec_ids)
    unique_industry = industries.unique()
    nb_unique_industry = len(unique_industry)
    ret = np.zeros((nb_sec_id, nb_unique_industry))
    for i in range(len(sec_ids)):
        col_index = np.where(unique_industry == industries[i])[0]
        ret[i][col_index] = 1.0

    if mkt_cap is not None:
        array_cap = mkt_cap.values.reshape(mkt_cap.values.shape[0], 1)
        # 合并两个矩阵构成大矩阵
        ret = np.hstack((ret, array_cap))

    return ret


def neutralize(factors, industries, caps=None):
    """
    :param factors: pd.Series, 原始截面因子
    :param industries: pd.Series, value = 行业名称
    :param caps: optional, pd.Series, value = caps value
    :return: 中性化后的因子
    """
    # 通过concat把数据对齐
    pyFinWarning(factors.size == industries.size, Warning, "size of factors does not equal to that of industries")
    if caps is None:
        data = pd.concat([factors, industries], join_axes=[factors.index], axis=1)
        lcap = None
    else:
        pyFinWarning(factors.size == caps.size, Warning, "size of factors does not equal to that of caps")
        data = pd.concat([factors, industries, caps], join_axes=[factors.index], axis=1)
        lcap = np.log(data[data.columns[2]])

    factors = data[data.columns[0]]
    industries = data[data.columns[1]]

    # 把没有行业对应的变成'other'
    industries = industries.fillna('other')
    # 把没有市值的设置成均值
    if lcap is not None:
        lcap = lcap.fillna(lcap.median())

    linreg = LinearRegression(fit_intercept=False)
    y = factors
    x = get_industry_matrix(industries, lcap)
    model = linreg.fit(x, y)
    coef = np.mat(linreg.coef_)
    a = np.dot(x, coef.T)
    residues = y.values - a.A1
    ret = pd.Series(residues, index=factors.index, name=factors.name).dropna()
    return ret


def normalize(factors, industries=None, caps=None):
    """
    :param factors:  pd.Series, 原始截面因子
    :param industries: pd.Series, value = 行业名称
    :param caps: optional, pd.Series, value = caps value
    :return: 去极值、标准化、中性化的因子
    """
    x = winsorize(factors)
    y = standardize(x)
    ret = neutralize(y, industries, caps)
    return ret


if __name__ == "__main__":
    index = ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ', '000006.SZ', '000007.SZ', '000008.SZ',
             '000009.SZ', '000010.SZ']
    factor = [10, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
              20.0]
    industry = ['801190.SI', '801190.SI', '801200.SI', '801200.SI', '801200.SI', '801200.SI', '801200.SI', '801200.SI',
                '801200.SI', '801200.SI', '801201.SI']
    cap = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    factor = pd.Series(factor, index=index)
    industry = pd.Series(industry, index=['000001.SZ', '000002.SZ', '100003.SZ', '000004.SZ', '000005.SZ', '000006.SZ',
                                          '000007.SZ', '000008.SZ', '000009.SZ', '000010.SZ', '000011.SZ'])
    cap = pd.Series(cap, index=index)
    print normalize(factor, industry, cap)
