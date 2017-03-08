# -*- coding: utf-8 -*-

from enum import IntEnum
from enum import unique


@unique
class FactorNormType(IntEnum):
    Null = 0
    IndustryNeutral = 1
    IndustryAndCapNeutral = 2


@unique
class DCAMFactorType(IntEnum):
    alphaFactor = 0
    layerFactor = 1
    returnFactor = 2
    industryFactor = 3
    indexWeight = 4


@unique
class FactorICSign(IntEnum):
    Null = 0
    Positive = 1
    Negative = -1


@unique
class FactorWeightType(IntEnum):
    EqualWeight = 1
    ICWeight = 2
