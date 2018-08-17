#!/usr/bin/env python3
'''
gen_and_draw.py

usage: ./gen_and_draw.py file_number

generates random grid and draws
'''

import sys
import os
sys.path.append(os.path.abspath('../src'))
from gen_problems import generate_case
from datetime import datetime
import time

import data_structures as ds
import charm


if len(sys.argv) != 5:
    print("usage: ./gen_and_draw.py dimension n_nodes n_nets mode")
    sys.exit(1)


gendir = 'generated/random/'
    

def gen_and_test(test_num,dim,n_nodes,n_nets,mode):
    # print("\t test {}".format(test_num))

    x_min = 0 #test_num * dim * 1.5        
    nodes = generate_case(n_nodes,n_nets,
                          x_min = x_min, x_max = x_min + dim,
                          y_max = dim,
                          label_prefix = "test{}".format(test_num),
                          seed = 100)

    inputs = {
        'layers': 10,
        'rects': nodes,
        'order': 'pair_rule3',
        'route_modes': 'pl',
        'input_mode': 'explicit', # explicit (read all) or placed (read .pl)
        'output': 'layout.tcl'
    }
    charm.pipeline(inputs)
    # charm.route([],components)
        

    
# file_num = int(sys.argv[1])
file_num = time.time()
dimension = int(sys.argv[1])
n_nodes = int(sys.argv[2])
n_nets = int(sys.argv[3])
mode = sys.argv[4]
gen_and_test(file_num,dimension,n_nodes,n_nets,mode)

        
    
