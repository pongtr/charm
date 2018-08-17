#!/usr/bin/env python3
'''
test_pipeline.py

'''

import sys
import os
sys.path.append(os.path.abspath('../src'))
import charm


layout_dir = 'layout/'
inputs = {
    'layers': 12,
    'order': 'pair_rule3',
    'route_modes': 'p',
    'input_mode': 'placed',
    'cell_dir' : 'cells/',
    'nodefile' : layout_dir + 'layout.nodes',
    'netfile'  : layout_dir + 'layout.nets',
    'placefile': layout_dir + 'layout.pl',
    'max_cell_layer': 4, # 4 corresponds to m2
    'output': 'layout.tcl'
}

charm.pipeline(inputs)
