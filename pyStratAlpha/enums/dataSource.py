# -*- coding: utf-8 -*-


from enum import IntEnum
from enum import unique


@unique
class DataSource(IntEnum):
    CSV = 0
    WIND = 1
