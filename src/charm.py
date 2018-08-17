#!/usr/bin/env python3
"""CHARM: CHip Automated Routing Module

write simple descriptions here
"""

from pprint import pprint

import data_structures as ds
# import interface
from layout import Layout
import auxiliary as aux
import controller

import sys

__author__ = "Pong Trairatvorakul"
__version__ = "2.0"
__email__ = "pong.tr@me.com"
__status__ = "pre-alpha"

def pipeline(inputs):    
    # inputs = interface.load_inputs(sys.argv)



    layout = Layout(inputs)            
    try:
        # layout.elevate('poly','m1')
        controller.lafrieda(layout,inputs)
    except KeyboardInterrupt:
        inputs['output'] = 'interrupted-' + inputs['output']
        print(aux.color_format(
            "\n\nKeyboard interrupt. Output current layout to {}".
            format(inputs['output']),
            'HEADER'))
    layout.emit_tcl(inputs['output'])
    aux.Timer.print_times()
