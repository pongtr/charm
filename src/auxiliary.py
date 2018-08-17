#!/usr/bin/env python3
"""Auxiliary Functions
"""

import time
from collections import defaultdict

#####
# PRINTING

# for print formating
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    CBLINK    = '\33[5m'
    CBLINK2   = '\33[6m'

def color_format(text,color):
    """Returns a string of text with format color
    """
    return "{}{}{}".format(getattr(bcolors,color),text,bcolors.ENDC)

#####
# TIMING

class Timer:
    times = defaultdict(float)
    
    def timeit(f):
        def timed(*args, **kw):
            ts = time.time()
            result = f(*args, **kw)
            te = time.time()
            Timer.times[f.__name__] += (te - ts)
            return result
        return timed

    def print_times():
        for func,time in Timer.times.items():
            print("{}\t{:2f}s".format(func,time))

#####
# OPTIMIZATION

def memoize(f):
    memo = {}
    def helper(x,y):
        if x not in memo:
            memo[(x,y)] = f(x,y)
        return memo[(x,y)]
    return helper


#####
# DRAWING

def manhattan_distance(point1,point2):
    """Given 2 points, return the manhattan distance of the two
    """
    return abs(point1[0] - point2[0]) + abs(point1[1] - point2[1])

@memoize
def manhattan_components(cp1,cp2):
    """Given two components, return shortest manhattan distance between
    the two components.
    """
    min_dist = None
    for p1 in cp1.line:
        for p2 in cp2.line:
            dist = manhattan_distance(p1,p2)
            if min_dist is None or dist < min_dist:
                min_dist = dist
    return min_dist

def get_dir(A,B):
    """Given waypoints A and B
    return 0 if horizontal, 1 if vertical, -1 otherwise
    """
    if A[0] != B[0] and A[1] == B[1]:   return  0    
    elif A[0] == B[0]: return  1 # note: will also ok for incident
    else:
        raise ValueError('waypoints {} and {} not on same axis'.format(A,B))

#####
# LOGICAL
    
def all_equal(lst):
    """Given list of elements, returns True if all elements are equal
    else False
    """
    if len(lst) <= 1:
        return True
    if lst[0] == lst[1]:
        return all_equal(lst[1:])
    else:
        return False    

