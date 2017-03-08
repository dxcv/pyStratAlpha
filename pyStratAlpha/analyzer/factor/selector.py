# -*- coding: utf-8 -*-

import pandas as pd
from PyFin.Utilities import pyFinAssert

from pyAlphaStrat.analyzer.factor.cleanData import get_multi_index_data
from pyAlphaStrat.analyzer.indexComp.indexComp import IndexComp
from pyAlphaStrat.utils.misc import top


class Selector(object):
    def __init__(self,
                 sec_score,
                 industry=None,
                 nb_sec_selected_per_industry_min=5,
                 index_comp=None,
                 save_sec_selected=False,
                 use_industry_name=True,
                 nb_sec_selected_total=100,
                 ignore_zero_weight=False):
        """
        :param sec_score: pd.Series, index = [tiaoCangDate, secID], value = score
        :param industry: pd.Series, optional, index = [tiaoCangDate, secID], value = industry name
        :param nb_sec_selected_per_industry_min: int, optional, nb sec to be selected each industry minimum
        :param index_comp: index composition class object, optional
        :param save_sec_selected: bool, optional, save result to csv or not
        :param use_industry_name: bool, optional, whether to use name instead of code in return dataframe
        :return:
        """
        self._secScore = sec_score
        self._secScore.sort_values(ascending=False, inplace=True)
        self._industry = industry
        self._nbSecSelectedPerIndustryMin = nb_sec_selected_per_industry_min
        self._indexComp = index_comp
        self._saveSecSelected = save_sec_selected
        self._secSelectedFullInfo = None
        self._secSelected = None
        self._tiaoCangDate = pd.to_datetime(sorted(set(self._secScore.index.get_level_values('tiaoCangDate'))))
        self._industryNeutral = True
        self._useIndustryName = use_industry_name
        self._nbSecSelectedTotal = nb_sec_selected_total
        self._ignoreZeroWeight = ignore_zero_weight

    @property
    def sec_selected(self):
        return self._secSelected

    @property
    def sec_selected_full_info(self):
        return self._secSelectedFullInfo

    @property
    def industry_neutral(self):
        return self._industryNeutral

    @industry_neutral.setter
    def industry_neutral(self, flag):
        pyFinAssert(isinstance(flag, bool), TypeError, "flag must be bool type variable")
        self._industryNeutral = flag

    @staticmethod
    def _save_sec_selected_from_full_info(sec_selected_full_info):
        """
        :param sec_selected_full_info: pd.DataFrame, multi index =[tiaoCangDate, secID], value = score / industry
        :return: pd.Series, index = tiaoCangDate, value = list of secID selected
        """

        date_list = sec_selected_full_info.index.get_level_values('tiaoCangDate').tolist()
        ret = pd.Series()
        for date in date_list:
            sliced_data = get_multi_index_data(sec_selected_full_info, 'tiaoCangDate', date)
            sec_ids = sliced_data.index.get_level_values('secID').tolist()
            ret[date] = sec_ids

        return ret

    def sec_selection(self):
        if self._industry is not None:
            sec_score = pd.concat([self._secScore, self._industry], join_axes=[self._secScore.index], axis=1)
        else:
            sec_score = self._secScore
        ret = pd.DataFrame()
        for date in self._tiaoCangDate:
            sec_score_on_date = get_multi_index_data(sec_score, 'tiaoCangDate', date)
            sec_score_on_date = sec_score_on_date.copy()
            sec_score_on_date.sort_values(by='score', ascending=False, inplace=True)
            if self._industryNeutral:
                pyFinAssert(self._industry is not None, ValueError, "industry information missing ")
                sec_score_on_date[self._industry.name] = sec_score_on_date[self._industry.name].fillna('other')
                industry_weight = self._indexComp.get_industry_weight_on_date(date)
                for name, group in sec_score_on_date.groupby(self._industry.name):
                    if self._ignoreZeroWeight and industry_weight[name] == 0:
                        continue
                    else:
                        nb_sec_selected_per_industry = max(len(group) * 0.1,
                                                           self._nbSecSelectedPerIndustryMin)
                        nb_sec_selected_per_industry = int(nb_sec_selected_per_industry)
                        if len(group) > nb_sec_selected_per_industry:
                            single_sec_weight = industry_weight[name] / nb_sec_selected_per_industry / 100.0
                            largest_score = top(group, column='score', n=nb_sec_selected_per_industry)
                            largest_score['weight'] = [single_sec_weight] * nb_sec_selected_per_industry
                        else:
                            largest_score = group.copy()
                            largest_score['weight'] = industry_weight[name] / len(group) / 100.0

                        ret = pd.concat([ret, largest_score], axis=0)
            else:
                sec_score_on_date = sec_score_on_date[:self._nbSecSelectedTotal + 1]
                sec_score_on_date['weight'] = 1.0 / self._nbSecSelectedTotal
                ret = pd.concat([ret, sec_score_on_date], axis=0)

        if self._useIndustryName:
            industry_name = IndexComp.map_industry_code_to_name(ret[self._industry.name])
            ret = ret[['score', 'weight']]
            ret = pd.concat([ret, industry_name], join_axes=[ret.index], axis=1)

        self._secSelectedFullInfo = ret
        self._secSelected = self._save_sec_selected_from_full_info(ret)
        if self._saveSecSelected:
            self._secSelectedFullInfo.to_csv('sec_selected.csv', date_format='%Y-%m-%d', encoding='gbk')
        return

    def sec_selected_universe(self):
        """
        :return: list of universal sec ids that are appeared in selections
        """
        if self._secSelectedFullInfo is None:
            self.sec_selection()

        ret = self._secSelectedFullInfo.index.get_level_values('secID').tolist()
        ret = list(set(ret))

        return ret
