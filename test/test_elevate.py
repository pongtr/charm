#!/usr/bin/env python3
'''
test_elevate.py

'''

import sys
import os
sys.path.append(os.path.abspath('../src'))
import data_structures as ds
from layout import Layout

node = ds.Rect(0,0,4,4,'m1','net')
inputs = {
    'input_mode': 'explicit',
    'layers': 10,
    'rects': [node]
}

layout = Layout(inputs)
layout.emit_tcl('test_elevate.tcl')
