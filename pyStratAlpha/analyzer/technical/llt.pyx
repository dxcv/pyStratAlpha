# -*- coding: utf-8 -*-
# ref: Github/Finance-Python/PyFin/Analysis/TechnicalAnalysis


cimport numpy as np
from math import isnan
from PyFin.Math.Accumulators.IAccumulators import StatelessSingleValueAccumulator
from PyFin.Math.Accumulators.impl import Deque
from PyFin.Analysis.TechnicalAnalysis.StatelessTechnicalAnalysers import SecurityStatelessSingleValueHolder
from PyFin.Utilities.Asserts import pyFinAssert



cdef class LLT(StatelessSingleValueAccumulator):

    def __init__(self, window, alpha, dependency='x', method=Deque):
        pyFinAssert(0 <= alpha <= 1.0, ValueError, "alpha must be between 0.0 and 1.0 however {0} received".format(alpha))
        super(LLT, self).__init__(dependency)
        self._window = method(window)
        self._alpha = alpha
        self._llt = Deque(3)

    cpdef push(self, data):
        cdef double value = self._push(data)
        cdef double popout

        if isnan(value):
            return np.nan
        popout = self._deque.dump(value)
        if not isnan(popout):
            underlyingPrice = self._deque.as_list()
            llt = (self._alpha - self._alpha**2 / 4.0) * underlyingPrice[-1] + (self._alpha^2 / 2 ) * underlyingPrice[-2] - \
                  (self._alpha - 3 * self._alpha**2 / 4.0) * underlyingPrice[-3] + 2 * (1 - self._alpha) * self._llt[2] -\
                  (1 - self._alpha)**2 * self._llt[1]
            self._llt.push(llt)
        else:
            self._llt.push(value)

    def result(self):
        return self._llt.as_list[-1]

    def __deepcopy__(self, memo):
        return LLT(self._window, self._dependency, self._alpha)

    def __reduce__(self):
        d = {}
        return LLT, (self._window, self._dependency, self._alpha), d

    def __setstate__(self, state):
        pass


cdef class SecurityLLT(SecurityStatelessSingleValueHolder):
    def __init__(self, window=3, alpha=2.0/61.0, dependency='x'):
        super(SecurityLLT, self).__init__(holderType=LLT,
                                          dependency=dependency,
                                          window=window,
                                          alpha=alpha)

    def __deepcopy__(self, memo):
        if self._compHolder:
            return SecurityLLT(self._holderTemplate._window, self._holderTemplate._alpha, self._compHolder)
        else:
            return SecurityLLT(self._holderTemplate._window, self._holderTemplate._alpha, self._dependency)

    def __reduce__(self):
        d = {}
        if self._compHolder:
            return SecurityLLT, (self._holderTemplate._window, self._holderTemplate._alpha, self._compHolder), d
        else:
            return SecurityLLT, (self._holderTemplate._window, self._holderTemplate._alpha, self._dependency), d

    def __setstate__(self, state):
        pass





if __name__ == "__main__":
    pass