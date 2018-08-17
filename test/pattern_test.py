#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.abspath('../src'))
from pprint import pprint
import pattern_router as pr
import data_structures as ds

def test_patterns(s,d):
    print("s: {}\td: {}".format(s,d))
    print("O PATTERN")
    pprint(pr.incident(s,d))
    print()
    print("I PATTERN")
    pprint(pr.i_pattern(s,d))
    print()
    print("L PATTERN")
    pprint(pr.l_pattern(s,d))
    print("----------------")
    print()

def test_incident():
    print("TEST INCIDENT")
    s = (0,0,'m1')
    d = (0,0,'m1')
    test_patterns(s,d)

    s = (0,0,'m1')
    d = (0,0,'m2')
    test_patterns(s,d)

def test_i():
    print("TEST I SHAPE")
    s = (0,0,'m1')
    d = (0,10,'m1')
    test_patterns(s,d)

    s = (0,0,'m1')
    d = (10,0,'m1')
    test_patterns(s,d)

    s = (0,0,'m1')
    d = (0,10,'m2')
    test_patterns(s,d)

    s = (0,0,'m1')
    d = (10,0,'m2')
    test_patterns(s,d)

def test_l():
    print("TEST L SHAPE")
    s = (0,0,'m1')
    d = (10,10,'m1')
    test_patterns(s,d)

    s = (0,0,'m1')
    d = (10,10,'m2')
    test_patterns(s,d)

def test_z():
    for i in range(1,6):
        s = (0,0,'m1')
        d = (10,10,'m{}'.format(i))
        print(s,d)
        for pattern in pr.z_pattern(s,d):
            print(pr.cost_estimate(pattern))
        print('---------')

def test_generate():
    cp1 = ds.Component('cp1')
    n1 = ds.Rect(0,0,4,4,'pc','net')
    cp1.add_node(n1)

    cp2 = ds.Component('cp2')
    n2 = ds.Rect(0,10,4,4,'pc','net')
    cp2.add_node(n2)

    for r in pr.generate_routes(cp1,cp2,False):
        print(r.cost)

def test_route():
    cp1 = ds.Component('cp1')
    n1 = ds.Rect(0,0,4,4,'pc','net')
    cp1.add_node(n1)

    cp2 = ds.Component('cp2')
    n2 = ds.Rect(0,10,4,4,'pc','net')
    cp2.add_node(n2)

    pr.route_components(cp1,cp2)
    
test_route()
    


