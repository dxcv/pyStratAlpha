# coding=utf-8

import itertools


def running_sum(s, n):
    """
    :param s: list of elements
    :param n: length of running sum
    :return: generator object of a running sum
    Generate the series of running sums of n elements of s.

    list(running_sum([1, 2, 3, 4], 2))
    [3, 5, 7]
    rs = running_sum(itertools.count(), 3)
    rs.next(), rs.next(), rs.next()
    (3, 6, 9)
    list(running_sum([1, 2], 3))
    []
    """
    lo, hi = [i.next for i in itertools.tee(s)]
    rs = sum([hi() for _ in range(n)])
    while True:
        yield rs
        rs += hi() - lo()


if __name__ == "__main__":
    print list(running_sum([1, 2, 3, 4], 3))
