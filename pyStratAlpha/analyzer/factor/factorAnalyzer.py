# -*- coding: utf-8 -*-
from PyFin.DateUtilities import Calendar
from alphalens.performance import factor_returns
from alphalens.performance import mean_return_by_quantile
from alphalens.utils import get_clean_factor_and_forward_returns

from pyAlphaStrat.analyzer.indexComp import IndexComp
from pyAlphaStrat.enums import DataSource
from pyAlphaStrat.utils import WindMarketDataHandler

_alphaLensFactorIndexName = ['date', 'asset']
_alphaLensFactorColName = 'factor'


class FactorAnalyzer(object):
    def __init__(self,
                 start_date,
                 end_date,
                 factor,
                 industry,
                 data_source=DataSource.WIND,
                 calendar='China.SSE'):
        """
        :param factor: pd.Series, multi index=[tradeDate, secID]  columns = [factor]
        :param industry: pd.Series/dict, Either A MultiIndex Series indexed by date and asset, containing the period
        wise group codes for each asset, or a dict of asset to group mappings. If a dict is passed, it is assumed that
        group mappings are unchanged for the entire time period of the passed factor data.
        :param data_source: enum, DataSource type
        :param calendar: PyFin.Calendar type
        :return:
        """
        self._calendar = Calendar(calendar)
        self._startDate = start_date
        self._endDate = end_date
        self._factor = factor
        self._industry = industry
        self._dataSource = data_source

        self._factor.index = self._factor.index.rename(_alphaLensFactorIndexName)
        self._factor.name = _alphaLensFactorColName
        self._factor = self._factor.loc[
            self._factor.index.get_level_values(_alphaLensFactorIndexName[0]) >= self._startDate]
        self._factor = self._factor.loc[
            self._factor.index.get_level_values(_alphaLensFactorIndexName[0]) <= self._endDate]

        self._tradeDate = sorted(set(self._factor.index.get_level_values(_alphaLensFactorIndexName[0])))
        self._secID = sorted(set(self._factor.index.get_level_values(_alphaLensFactorIndexName[1]).tolist()))
        self._price = self._get_price_data()

    def _get_price_data(self):
        if self._dataSource == DataSource.WIND:
            price_data = WindMarketDataHandler.get_sec_price_on_date(self._tradeDate, self._secID)
        else:
            raise NotImplementedError
        return price_data

    def _get_clean_factor_and_fwd_return(self):
        factor = get_clean_factor_and_forward_returns(factor=self._factor,
                                                      prices=self._price,
                                                      groupby=self._industry,
                                                      groupby_labels=IndexComp.get_industry_name_dict())
        return factor

    def create_full_tear_sheet(self):
        factor = self._get_clean_factor_and_fwd_return()
        factor_return = factor_returns(factor, long_short=True)

        mean_quantile, std_qauntile = mean_return_by_quantile(factor,
                                                              by_group=False,
                                                              demeaned=True)

        return
