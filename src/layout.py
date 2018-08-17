#!/usr/bin/env python3
"""Layout class for CHARM
"""


import data_structures as ds
import design_rules as dr
from collections import defaultdict
import mag_reader
import auxiliary as aux
import design_rule_checker as drc

class Layout:

    BB_SF = 1.1 # Bounding box scale factor

    def __init__(self,inputs):
        print(aux.color_format("INITIALIZING LAYOUT","HEADER"))
        
        self.nodes = defaultdict(list)
        self.grid = [defaultdict(list) for _ in range(inputs['layers'])]
        self.grid_points = {}
        self.block_grid = defaultdict(list) # pointer to block for each point
        self.components = defaultdict(list)
        self.labels = set()
        self.rects = []
        self.blocks = []
        self.drc_cache = drc.Cache()

        mode = inputs['input_mode']
        self.mode = mode
        if mode == 'explicit':
            print("  Reading rectangles")
            for rect in inputs['rects']:
                self.add_rect(rect)
        elif mode == 'placed':
            self.read_placement(inputs)
        else:
            raise ValueError("Input mode is either explicit or placed")

        for layer,points in enumerate(self.grid):
            self.grid_points[layer] = set(points)
            
        self.bounding_box = self.get_bounding_box()

    def elevate(self,start_mat,end_mat):
        """Elevate nodes that start with start_mat to end_mat
        """
        n_components = sum([len(self.components[net]) for net in self.labels])
        elevating = 1        
        for net in self.labels:
            for c in self.components[net]:
                print("  Elevating {}/{} ".
                      format(elevating,n_components),end="\r")
                elevating += 1
                if c.nodes[0].m == start_mat:
                    c.elevate(end_mat,self)

        
    def add_rect(self,rect):
        """Adds the rect to the grid. If rect has label, add to nodes.
        """

        if rect.l is not None:
            # add to nodes
            self.nodes[rect.l].append(rect)

            # make and add component
            c = ds.Component(rect.l)
            c.add_node(rect)
            self.components[rect.l].append(c)

            # add to set of labels
            self.labels.add(rect.l)

        self.rects.append(rect)
            
        # get layer
        if rect.m in dr.mat_layers:
            layer = dr.layers_mat[rect.m]
        elif rect.m in dr.diff_mats: # diffusion materials (and contacts)
            layer = dr.diff_mats[rect.m]
        else:
            raise ValueError("INVALID MATERIAL {}".format(rect.m))

        # contacts also add adjacent layers
        if layer % 2 == 1:
            layers = [layer - 1, layer, layer + 1]
        else:
            layers = [layer]
        
        for x in range(rect.x, rect.x1 + 1):
            for y in range(rect.y, rect.y1 + 1):
                for l in layers:
                    self.grid[l][(x,y)].append(rect)

    def emit_tcl(self,filename):
        """Output tcl to draw layout in filename
        """

        with open(filename,'w') as f:
            if self.mode == 'explicit':            
                # output existing layouts
                for rect in self.rects:
                    rect.emit_tcl(f)
            else:
                for b in self.blocks:
                    b.emit_tcl(f)
                for l,nodes in self.nodes.items():
                    for n in nodes:
                        n.emit_tcl(f)
                
            
            # output components
            for net,comps in self.components.items():                
                [comp.emit_tcl(f) for comp in comps]

    def get_bounding_box(self):
        """Returns bounding box of layout (as rect)
        """
        x0,x1 = None,None
        y0,y1 = None,None

        # get bounding box
        for r in self.rects:
            if x0 is None or r.x < x0:
                x0 = r.x
            if x1 is None or r.x1 > x1:
                x1 = r.x
            if y0 is None or r.y < y0:
                y0 = r.y
            if y1 is None or r.y1 > y1:
                y1 = r.y1

        # expand by scale factor
        w,h = int((x1 - x0) * Layout.BB_SF), int((y1 - y0) * Layout.BB_SF)
        
        return ds.Rect(x0,y0,w,h,None)

    def read_placement(self,inputs):
        """Read placement and load into layout
        """
        def load_cell(cell_lib,cell,w,h):
            w, h = int(w), int(h)
            if cell not in cell_lib:
                cellfile = "{}{}.mag".format(inputs['cell_dir'],cell)
                cell_lib[cell] = ds.CellTemplate(w,h,mag_reader.read(cellfile))
            else:
                c = cell_lib[cell]
                if c.w != w or c.h != h:
                    raise ValueError("Cell width and height mismatch")

        def get_nodelist(nodefile,blocks,cell_lib):
            print(nodefile, end = ' ', flush=True)
            with open(nodefile) as f:
                for l in f:
                    t = l.split()
                    if len(t) == 0 or t[0] == '#': continue
                    if len(t) == 4: # node line
                        load_cell(cell_lib,t[3],t[1],t[2])
                        blocks[t[0]] = ds.Cell(t[0],t[3],cell_lib)

        def get_netlist(netfile,blocks):
            print(netfile, end = ' ', flush=True)
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
                        blocks[pk].add_net(current_net,x,y,mat)
                        # nets[current_net].append((t[0],t[3],t[4],t[5]))

        def get_placement(placefile,blocks):
            print(placefile)
            with open(placefile) as f:
                for l in f:
                    t = l.split()
                    if len(t) == 0 or t[0] == '#': continue
                    if t[0][0] == 'o':
                        pk,x,y = t[0],int(t[1]),int(t[2])
                        blocks[pk].offset(x,y)

        # Print status
        print("  Reading Placement from ",end=' ',flush=True)

        # initialize cell library and blocks dictionary
        cell_lib, blocks = {}, {}

        # get information from each file
        get_nodelist(inputs['nodefile'],blocks,cell_lib)
        get_netlist(inputs['netfile'],blocks)
        get_placement(inputs['placefile'],blocks)

        # add pins from block
        for pk,b in blocks.items():
            for layer,rects in b.geometry.items():
                for rect in rects:
                    # if rect.l is not None:
                    self.add_rect(rect)
            self.add_block(b)

        
        
    def add_block(self,block):
        """Add block to layout
        """

        # add block
        self.blocks.append(block)
        
        # add block pointer to grid
        for x in range(block.x, block.x + block.w):
            for y in range(block.y, block.y + block.h):
                self.block_grid[(x,y)].append(block)
    
