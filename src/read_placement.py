#!/usr/bin/env python3

'''
read_placement.py

'''

from pprint import pprint
import sys
import mag_reader
from copy import deepcopy
import design_rules as dr
import data_structures as ds
from collections import defaultdict

cell_dir = 'cells/'
layout_dir = 'layout/'


class Cell:
    def __init__(self,w,h,layout):
        self.w, self.h = w, h
        self.layout = defaultdict(list)
        for rect in layout:
            for layer in dr.get_mat_layer(rect.m):
                self.layout[layer].append(rect)            
        
def load_cell(cells,cell,w,h):
    w, h = int(w), int(h)
    if cell not in cells:
        cellfile = "{}{}.mag".format(cell_dir,cell)
        cells[cell] = Cell(w,h,mag_reader.read(cellfile))
    else:
        c = cells[cell]
        if c.w != w or c.h != h:
            raise ValueError("Cell width and height mismatch")

def get_nodelist(nodefile,nodes,cells):
    with open(nodefile) as f:
        for l in f:
            t = l.split()
            if len(t) == 0 or t[0] == '#': continue
            if len(t) == 4: # node line
                load_cell(cells,t[3],t[1],t[2])
                nodes[t[0]] = Node(t[0],t[3],cells)

def get_netlist(netfile,nodes):
    with open(netfile) as f:
        nets = {}
        current_net = None
        for l in f:
            t = l.split()
            if len(t) == 0 or t[0] == '#': continue            
            if t[0] == 'NetDegree':
                current_net = t[3]
                nets[current_net] = []
            if t[0][0] == 'o':
                pk,x,y,mat = t[0],float(t[3]),float(t[4]),t[5]
                nodes[pk].add_net(current_net,x,y,mat)
                # nets[current_net].append((t[0],t[3],t[4],t[5]))

def get_placement(placefile,nodes):
    with open(placefile) as f:
        for l in f:
            t = l.split()
            if len(t) == 0 or t[0] == '#': continue
            if t[0][0] == 'o':
                pk,x,y = t[0],int(t[1]),int(t[2])
                nodes[pk].offset(x,y)

    pass

def init_layout():
    cells, nodes = {}, {}
    nodefile = layout_dir + 'layout.nodes'
    get_nodelist(nodefile,nodes,cells)
    netfile = layout_dir + 'layout.nets'
    get_netlist(netfile,nodes)
    placefile = layout_dir + 'layout.pl'
    get_placement(placefile,nodes)

    return nodes

'''    
for rect in load_cell(sys.argv[1]):
    print(vars(rect))
'''

#pprint(get_nodelist(sys.argv[1]))
