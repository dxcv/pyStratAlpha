# coding=utf-8

import numpy as np
from PyFin.Utilities import pyFinAssert


def eig_val_pct(eig_values, pct):
    """
    :param eig_values: np.array/list, 所有特征值组成的向量
    :param pct: 阈值
    :return: 给定百分比阈值,返回需要降低到多少维度
    """
    pyFinAssert(0.0 <= pct <= 1.0, ValueError, "pct ({0:f}) must be between 0.0 and 1.0".format(pct))
    sort_eig_values = np.sort(eig_values)
    sort_eig_values = sort_eig_values[-1::-1]  # 特征值从大到小排列
    eig_values_sum = sum(sort_eig_values)
    cum_sum = sort_eig_values.cumsum()
    marginal_eig_val = next(x for x in cum_sum if x / eig_values_sum >= pct)
    index = np.where(cum_sum == marginal_eig_val)[0][0]
    return index + 1


def pca_decomp(data_mat, pct=0.9):
    """
    :param data_mat: np.maths, 数据矩阵, 列向量为特征向量
    :param pct: 阈值, 降维后需要达到的方差占比
    :return: 降维后的数据集, 和 重构数据
    """

    mean_values = np.mean(data_mat, axis=0)  # 对每一列求均值
    mean_removed = data_mat - mean_values
    cov_mat = np.cov(mean_removed, rowvar=0)
    eig_values, eig_vectors = np.linalg.eig(np.mat(cov_mat))
    k = eig_val_pct(eig_values, pct)
    eig_val_ind = np.argsort(eig_values)
    eig_val_ind = eig_val_ind[:-(k + 1):-1]
    red_eig_vectors = eig_vectors[:, eig_val_ind]  # 返回排序后特征值对应的特征向量redEigVects（主成分）
    low_d_data_mat = mean_removed * red_eig_vectors  # 将原始数据投影到主成分上得到新的低维数据lowDDataMat
    recon_mat = low_d_data_mat * red_eig_vectors.T + mean_values  # 得到重构数据reconMat
    return low_d_data_mat, recon_mat


if __name__ == "__main__":
    eig_val_pct([1, 2, 3], 0.9)
