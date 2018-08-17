#!/usr/bin/env python3
"""Data Structures for CHARM

Includes:
- SPQ: Stable Priority Queue
- Rect: basic rectangles containing
    x,y coordinates of bottom left
    width and height
    material
    net if any
    parent cell if applicable
- Cell: placed cell information
- GlobalGrid: Contains pointers to cells in coordinate
- LocalGrid: Contains pointers to rectangles at coordinate
- Component: area components used when routing
- Route: contains list of waypoints and estimated cost
"""

import auxiliary as aux
from collections import defaultdict
import design_rules as dr
import lee_router
import heapq
from copy import deepcopy


##########
# Stable Priority Queue

class SPQ:
    """Stable Priority Queue
    Priority queue that serves lowest priority first
    If same priority, then FIFO for that priority
    """
    def __init__(self):
        self.queue = defaultdict(list)
        self.priorities = []

    def put(self,priority,item):
        """Add item with given priority to queue
        """
        self.queue[priority].append(item)
        heapq.heappush(self.priorities,priority)

    def get(self):
        """Remove and return the first in item with lowest priority
        If empty, return None
        """
        if len(self.priorities) == 0: return None
        lowest = heapq.heappop(self.priorities)
        return self.queue[lowest].pop(0)

    def peek(self):
        """Return smallest value in priority without popping
        """
        return self.priorities[0] if len(self.priorities) > 0 else None

    def empty(self):
        """Return True if priority queue is empty, False otherwise
        """
        if len(self.priorities) == 0:
            return True
        else:
            return False

##########
# Cell

class CellTemplate:
    def __init__(self,w,h,layout):
        self.w, self.h = w, h
        self.layout = defaultdict(list)
        for rect in layout:
            self.layout[dr.layers_mat[rect.m]].append(rect)

class Cell:
    def __init__(self,pk,cell_type,cell_lib):
        self.pk = pk
        self.cell_type = cell_type
        self.x, self.y = 0, 0 # initialize location to 0 0

        # get cell information
        template = cell_lib[cell_type]
        self.w, self.h = template.w, template.h
        self.geometry = deepcopy(template.layout)
        self.geometry_material= defaultdict(list)

        # tag all rects as coming from this block
        for layer,rects in self.geometry.items():
            for rect in rects:
                rect.bk = pk
                self.geometry_material[rect.m].append(rect)

    def add_net(self,net,x,y,mat):
        # first check direct material            
        # if not found, then check connected material
        for om in [mat] + dr.other_mats[mat]:
            for rect in self.geometry_material[om]:
                if rect.is_in((x,y)):
                    rect.l = net
                    return True
        print("Pin not found"
              "({},{},{}) in  {}".format(x,y,mat,self.cell_type))

    def offset(self,dx,dy):
        self.x, self.y = dx, dy        
        for layer,rects in self.geometry.items():
            for rect in rects:
                rect.offset(dx,dy)

    def get_enclosing_rect(self):
        try:
            return self.enclosing_rect
        except AttributeError:
            self.enclosing_rect = Rect(self.x,self.y,
                                       self.w,self.h,None,points=False)
            return self.enclosing_rect
                
    def emit_tcl(self,fp,dump=False,cell_dir='cells/'):
        """Emit tcl command to place cell at x,y
        if dump True, then dump, else getcell
        """
        fp.write("box position {} {}\n".format(self.x,self.y))
        cellfile = "{}{}.mag".format(cell_dir,self.cell_type)
        if dump:
            fp.write("dump {}\n".format(cellfile))
        else:
            fp.write("getcell {}\n".format(cellfile))

    def emit_net_rectangles(self,fp):
        """Emit tcl commands to place rectangles with nets
        """        
        for layer,rects in self.geometry.items():
            for rect in rects:
                if rect.l is not None:
                    rect.emit_tcl(fp)

    def get_points(self):
        try:
            return self.points
        except AttributeError:
            self.points = defaultdict(set)
            for mat,rects in self.geometry_material.items():
                layer = dr.layers_mat[mat]
                for rect in rects:
                    self.points[layer] = self.points[layer].union(rect.points)
            return self.points


##########
# Rect

class Point:
    def __init__(self,x,y):
        self.x,self.y = x,y

class Rect:
    f = None

    def __init__(self,x,y,w,h,m,l=None,bk=None,points=True):
        self.x, self.y = x, y
        self.w, self.h = w, h
        self.get_x1_y1()
        self.m = m
        self.l = l
        self.bk = bk # block key

        # only get points if needed
        if points:
            self.get_mat_points()
            self.points = self.get_points()

    def get_x1_y1(self):
        """Calculate the max x and y
        """
        self.x1, self.y1 = self.x + self.w - 1, self.y + self.h - 1        

    def offset(self,dx,dy):
        """Offsets the rectangle by dx and dy
        """
        self.x += dx
        self.y += dy
        self.x1 += dx
        self.y1 += dy
        self.get_mat_points()
        
    def emit_tcl(self,fp):
        """emit tcl commands to draw rectangle
        """
        fp.write("box {} {} {} {}\npaint {}\n"
                 .format(self.x,self.y,
                         self.x + self.w,self.y + self.h,
                         self.m))
        if self.l is not None and self.m[-1] == 'c':
            fp.write("move right 1\nmove up 1\nbox w 0\nbox h 0\nlabel {}\n"
                     .format(self.l))

    def is_in(self,d):
        """return true if point d is in rect
        """
        if ((d[0] >= self.x and d[0] < self.x + self.w) and
            (d[1] >= self.y and d[1] < self.y + self.h)):
            return True

    def print_info(self):
        """Print info of rect (for debugging)
        """
        print("Rect({},{},{},{},{},{})".format(
            self.x,self.y,self.w,self.h,self.m,self.l))
        
    def overlaps(self,rect):
        """Returns True if self and rect overlap
        """
        a_bottom_left = Point(self.x,self.y)        
        a_top_right = Point(self.x + self.w - 1, self.y + self.h - 1)
        b_bottom_left = Point(rect.x,rect.y)
        b_top_right = Point(rect.x + rect.w - 1,rect.y + rect.h - 1)
        return not (a_top_right.x < b_bottom_left.x or
                    a_bottom_left.x > b_top_right.x or
                    a_top_right.y < b_bottom_left.y or
                    a_bottom_left.y > b_top_right.y)

    def overlap_relative(self,rect,material):
        """report position of rect relative to self
        """
        width = material_width[material]
        
        # right edge of rect to left edge of self
        extend_right = self.x - (rect.x + rect.w)    
        
        # left edge of rect to right edge of self
        extend_left = rect.x - (self.x + self.w)

        # top edge of rect to bottom edge of self
        extend_top = self.y - (rect.y + rect.h)

        # bottom edge of rect to top edge of self
        extend_bottom = rect.y - (self.y + self.h)

        extensions = [extend_right,extend_left,extend_top,extend_bottom]
        extensions = [max(0,width + e) for e in extensions]
        return extensions
    
    def bloated(self,material,spacing=None):
        """Returns bloated rectangle (with spacing)
        """
        if spacing is None:
            spacing = material_spacing[material]
        x = self.x - spacing
        y = self.y - spacing
        w = self.w + 2 * spacing
        h = self.h + 2 * spacing
        # l = self.l
        return Rect(x,y,w,h,material)

    def duplicate(self):
        """return a copy with same values
        """
        return Rect(self.x,self.y,self.w,self.h,self.m,self.l)

    def get_points(self,material=False):
        """Returns the set of points of the rectangle
        """
        points = set()
        for i in range(self.x,self.x + self.w):
            for j in range(self.y,self.y + self.h):
                point = (i,j,self.m) if material else (i,j)
                points.add(point)
        return points

    def get_mat_points(self):
        """Calculate set of points in lower left that expands to rect
        """
        if self.m not in dr.material_width:
            return set()
        points = set()
        width = dr.material_width[self.m]
        for i in range(self.x,self.x + self.w - width + 1):
            for j in range(self.y,self.y + self.h - width + 1):
                points.add((i,j,self.m))
        self.mat_points = points
        
    def make_rects(points,material,label=None):
        """Returns list of rects for given set of points and material
        """
        rects = []
        while len(points) > 0:
            p = points.pop()
            x0 = x1 = p[0]
            y0 = y1 = p[1]
            test = (x0 + 1, y0)
            # extend right
            while test in points:
                points.remove(test)
                x1 = test[0]
                test = (test[0] + 1, y0)
            # extend left
            test = (x0 - 1, y0)
            while test in points:
                points.remove(test)
                x0 = test[0]
                test = (test[0] - 1, y0)
            # extend up
            while all([(xi,y1 + 1) in points for xi in range(x0,x1 + 1)]):
                [points.remove((xi,y1 + 1)) for xi in range(x0,x1 + 1)]
                y1 += 1
            while all([(xi,y0 - 1) in points for xi in range(x0,x1 + 1)]):
                [points.remove((xi,y0 - 1)) for xi in range(x0,x1+1)]
                y0 -= 1
            rects.append(Rect(x0,y0,x1 - x0 + 1, y1 - y0 + 1, material, label))
        return rects 

##########
# GlobalGrid

##########
# LocalGrid
        
##########
# Component

        
class Component:
    """Connected Component
    """
    def __init__(self,label):
        """Initialize a component by given a node (as rect)
        """
        self.label = label        
        self.line = set()
        self.nodes = []
        self.segments = []
        self.seg_rects = {} # segment rectangles (key is segment)
        self.fillers = {} # fillers between segment and node (key: (seg,node))
        self.blocks = []
        # key: junction_point, val: list of segments
        self.junctions = defaultdict(list)
        self.x0,self.x1,self.y0,self.y1 = None,None,None,None

    def add_block(self,bk):
        """Add the block key to list of blocks the component interacts with
        """
        self.blocks.append(bk)
    
    def get_centroid(self):
        """Return the centroid of a component
        """
        x,y = 0,0
        n = len(self.line)        
        for p in self.line:
            x += p[0]
            y += p[1]
        return (x / n, y / n)

    def get_mat_points(rect,mat=None):
        """Given a rectangle, return the bottom left points from
        which the rectangle is formed
        """
        if mat is None: mat = rect.m
        # if mat not in dr.material_order: return set()
        width = dr.material_width[mat]
        line = set()
        for x in range(rect.x,rect.x + rect.w - width + 1):
            for y in range(rect.y,rect.y + rect.h - width + 1):
                line.add((x,y,mat))
        return line
    
    def add_node(self,node,layout=None):
        """Add node (given as rect) to component
        """
        self.nodes.append(node)

        if node.m in dr.contact_materials:
            for mat in dr.contact_materials[node.m]:
                self.line = self.line.union(Component.get_mat_points(node,mat))
                point = (node.x,node.y,mat)
                self.junctions[point].append([point,node])
        else:
            self.line = self.line.union(node.mat_points)
            point = (node.x,node.y,node.m)
            self.junctions[point].append([point,node])
        self.get_corners()

    def elevate(self,dest_mat,layout,platform_sf=5):
        """Elevator to quickly increase layer
        Creates large platform at dest_mat then use lee router to join

        platform_sf is scale factor of platform at dest_mat
        """

        # origin is the only node in the component
        if len(self.nodes) > 1:
            print("multiple nodes. picking one")
            # raise ValueError("Cannot have multiple nodes in component")
        origin = self.nodes[0]

        # return if elevation is not needed
        if dr.layers_mat[origin.m] >= dr.layers_mat[dest_mat]:
            return
        
        # create platform
        w,h = int(origin.w * platform_sf), int(origin.h * platform_sf)
        x = int(origin.x - ((platform_sf - 1) / 2 * origin.w))
        y = int(origin.y - ((platform_sf - 1) / 2 * origin.h))
        platform = Rect(x,y,w,h,dest_mat,origin.l)
        platform_cpn = Component(origin.l)
        platform_cpn.add_node(platform)

        # route between origin and platform
        route = lee_router.lee_route_components(self,platform_cpn,layout,
                                            layout.drc_cache,vertical=True)
        if route:
            self.add_route(route)
        else:            
            print("    Unable to elevate Rect{} to {}".
                  format((origin.x,origin.y,origin.w,origin.h,origin.m),
                         dest_mat))
        
    def add_route(self,route):
        """Add a route to the component
        return False if route not connected to existing segment
        """
        first,last = route.waypoints[0][:3], route.waypoints[-1][:3]
        
        # find connecting segment and break
        if (len(self.segments) != 0 and
            not self.connect_break(first) and
            not self.connect_break(last) and
            first not in self.line and last not in self.line):
            raise ValueError("Route is not connected to component")
        
        # add segments from route
        for i in range(len(route.waypoints) - 1):
            segment = ([route.waypoints[i], route.waypoints[i + 1]])
            self.add_segment(segment)
        return True
                
        
    def connect_break(self,point):
        """Find point on existing segment
        If found, break the segment into two at that point and return True
        else, return False
        """        
        for seg in self.segments:
            # no need to split
            if point in seg: return True
            
            d = aux.get_dir(seg[0],seg[1])
            if point[not d] != seg[0][not d]: continue
            if point[d] < min(seg[0][d],seg[1][d]): continue
            if point[d] > max(seg[0][d],seg[1][d]): continue
            if point[2] != seg[0][2]: continue # different material            
            
            # found segment
           
            # split
            self.segments.remove(seg)
            for ep in seg:
                self.junctions[ep].remove(seg)
            self.add_segment([seg[0],point])            
            self.add_segment([seg[1],point])
            return True # found and broke

        # in list of points but not on a segment
        if point in self.line:            
            return True
        
        return False

    def add_segment(self,segment):
        """Given a segment, add it to the component
        Add it to list of segments, then add the junction pointers
        """

        def list_line(segment):
            """Returns set of points on line of segment
            """
            a,b = segment[0],segment[1]
            drtn = aux.get_dir(a,b) # get direction
            points = set()
            for i in range(min(a[drtn],b[drtn]),max(a[drtn],b[drtn]) + 1):
                point = (a[0],i,a[2]) if drtn else (i,a[1],a[2])
                points.add(point)
            return points

        # add segment
        self.segments.append(segment)

        # add points on line
        self.line = self.line.union(list_line(segment))

        # create junctions
        self.junctions[segment[0]].append(segment)
        self.junctions[segment[1]].append(segment)

        # generate segment rectangle
        seg_rect = make_segment_rect(segment[0],segment[1],self.label)
        self.seg_rects[tuple(segment)] = seg_rect

        # determine corners
        self.get_corners()

    def remove_segment(self,segment):
        """Remove segment from component
        If segment on end, then remove and return current component as list
        If segment disconnects two components, 
           then return list of new components
        If segment not in component, raise error
        """
        if segment not in self.segments:
            raise ValueError("Segment {} not in component".format(segment))

        # remove segment
        self.segments.remove(segment)

        # remove points of segment
        for p in pg.list_line(segment[0],segment[1],[],True):
            if p in self.junctions and len(self.junctions[p]) > 1: continue
            self.line.remove(p)
        for ep in segment:
            if (ep in self.junctions and len(self.junctions[ep]) == 1 and
                ep in self.line):
                self.line.remove(ep)

        # remove rectangle of segment
        self.segments.remove(tuple(segment))
        
        # segment on end so just return current component
        if any([len(self.junctions[ep]) < 2 for ep in segment]):
            for ep in segment: # remove segment from junction
                self.junctions[ep].remove(segment)
                if len(self.junctions[ep]) == 0:
                    self.junctions.pop(ep)
            # determine new corners
            self.get_corners()
            return [self]
        
        # find other components
        components = []
        for i,ep in enumerate(segment):
            queue = [ep]
            visited_junctions, visited_segs = [], []
            cpn = Component(self.label)
            while len(queue) > 0:
                junction = queue.pop(0)
                if junction in visited_junctions: continue
                visited_junctions.append(junction)
                for seg in self.junctions[junction]:
                    if seg in visited_segs or seg == segment: continue
                    visited_segs.append(seg)
                    for i in range(2):
                        if isinstance(seg[i],Rect):
                            cpn.add_node(seg[i])
                        elif seg[i] != junction:
                            queue.append(seg[i])
                            cpn.add_segment(seg)
            components.append(cpn)
        return components

    def get_corners(self):
        for p in self.line:
            if self.x0 is None or p[0] < self.x0: self.x0 = p[0]
            if self.x1 is None or p[0] > self.x0: self.x1 = p[0]            
            if self.y0 is None or p[1] < self.y0: self.y0 = p[1]
            if self.y1 is None or p[1] < self.y1: self.y1 = p[1]            
            
    
    def trim(self):
        """Remove branches of the component that does not connect
        to any node
        Return False if no nodes remaining, True otherwise
        """
        # start at a node, DFS the component

        # No nodes remaining        
        if len(self.nodes) == 0:
            return False

        # Pick the first possible node
        node = self.nodes[0]
        junction = (node.x,node.y,node.m)

        # trim recursively
        self.trim_from_junction(junction,[],[node],[])

    def trim_from_junction(self,junction,v_segments,v_nodes,v_junctions):
        """Given a node, recursively trim the other nodes
        """
        if junction not in self.junctions:
            raise ValueError("Invalid junction {}".format(junction))

        if junction in v_junctions: return True
        v_junctions.append(junction)

        has_node = False        
        for seg in self.junctions[junction]:
            if seg in v_segments: continue # already visited segment
            v_segments.append(seg)

            for ep in seg:

                if ep in self.nodes:
                    v_nodes.append(ep)
                    v_junctions.append(ep)
                    has_node = True

                if ep in v_junctions: continue                
                if self.trim_from_junction(ep,v_segments,v_nodes,v_junctions):
                    has_node = True
                else:
                    self.remove_segment(seg)

        return has_node

    def is_empty(self):
        """Returns true if component is empty (has no segments or nodes)
        """
        return (len(self.segments) == 0 and len(self.nodes) == 0)

    def emit_tcl(self,fp):
        """Output tcl to fp
        """
        # no need to draw nodes, just draw segments
        for segment in self.segments:
            make_segment_rect(segment[0],segment[1],self.label).emit_tcl(fp)
        for k,f in self.fillers.items():
            f.emit_tcl(fp)

    def get_points(self):
        """Calculates and returns points in component
        """
        try:
            return self.points
        except AttributeError:
            points = set()
            for segment in self.segments:
                seg_rect = make_segment_rect(segment[0],segment[1],self.label)
                points = points.union(seg_rect.get_points(material=True))
            for k,f in self.fillers.items():
                points = points.union(f.get_points(material=True))
            self.points = points
            return points
            
                
    def join(cp1,cp2,route):
        """Given two components, and route connecting the two,
        return a new component joining all three
        """
        if cp1.label != cp2.label:
            raise ValueError("Different labels {} {}"
                             .format(cp1.label,cp2.label))
        comp = Component(cp1.label)        
        for cp in [cp1,cp2]:
            # add original nodes
            for n in cp.nodes:
                comp.add_node(n)
            # add original segments
            for s in cp.segments:
                comp.add_segment(s)
            # add fillers
            for k,f in cp.fillers.items():
                comp.fillers[k] = f
        comp.fill_notches(route)
        comp.add_route(route)
        return comp

    def fill_notches(self,route):
        """Fill any notches that may be added by route
        """
        route_contacts = []
        for wp in route.waypoints:
            if wp[2] in dr.contact_materials:
                width = wp[3] if len(wp) > 3 else dr.material_width[wp[2]]
                route_contacts.append(Rect(wp[0],wp[1],width,width,wp[2]))
        
        for seg in range(len(route.waypoints) - 1):
            A,B = route.waypoints[seg],route.waypoints[seg+1]
            seg_rect = make_segment_rect(A,B,self.label,contoured=False)
            rect_contoured = make_segment_rect(A,B,self.label,contoured=True)
            mat = A[2]
            if mat in dr.contact_materials: continue # skip contacts
            layer = dr.layers_mat[A[2]]
            contact_rects = [rect for _,rect in self.seg_rects.items()
                             if rect.m in dr.contact_materials]
            for n in self.nodes + contact_rects + route_contacts:
                if abs(dr.layers_mat[n.m] - layer) < 2: # check layer
                    # if connected or irrelevant, continue
                    if seg_rect.overlaps(n) or not rect_contoured.overlaps(n):
                        continue
                    drtn = aux.get_dir(A,B)
                    if drtn: # vertical
                        x = min(seg_rect.x1,n.x1) + 1
                        w = max(max(seg_rect.x,n.x) - x, 0)
                        y = max(seg_rect.y,n.y)
                        h = max(min(seg_rect.y1,n.y1) - y + 1, 0)
                    else: # horizontal
                        x = max(seg_rect.x,n.x)
                        w = max(min(seg_rect.x1,n.x1) - x + 1, 0)
                        y = min(seg_rect.y1,n.y1) + 1
                        h = max(max(seg_rect.y,n.y) - y + 1, 0)
                    filler = Rect(x,y,w,h,mat,self.label)
                    self.fillers[(seg,n)] = filler
    
    def line_materials(self):
        """Returns a list of material in self.line sorted from low to high layer
        """
        layers = []
        for p in self.line:
            mat = p[2]
            layer = dr.layers_mat[mat]
            if layer not in layers:
                layers.append(layer)
        return sorted(layers)
                    
class Route:
    """Has waypoints, cost, and rectangles
    """
    def __init__(self,waypoints):
        self.waypoints = waypoints
        self.cost = self.cost_estimate()
        self.materials = self.get_materials()

    def cost_estimate(self):
        """Returns estimate of route cost
        """
        route = self.waypoints
        cost = 0
        for seg in range(len(route) - 1):
            A,B = route[seg], route[seg+1]
            mat, width = A[2],A[3] if len(A) > 3 else dr.material_width[A[2]]
            drt = aux.get_dir(A,B)
            length = abs(A[drt] - B[drt])
            area = length * width
            if mat != B[2] or seg == len(route) - 2:
                area += width * (width - 1) # add end if material change
            cost += area * dr.material_cost[mat]
        return cost

    def get_materials(self):
        """Returns a set of materials used in the route
        """
        materials = set()
        for wp in self.waypoints:
            materials.add(wp[2])
        return materials

    def from_points(points):
        """Generate and return route given a list of points (from Lee)
        """
        curr_direction, curr_mat = None, None
        curr_start, curr_end = None, None
        waypoints = []
        component = []
        for point in points:
            # skip same point
            if point == curr_end:
                continue
            
            if curr_start is None:
                component.append(point)
                curr_start = point
                curr_end = point
                curr_mat = point[2]
                continue

            if point[2] == curr_mat:
                # get direction
                direction = None
                if point[0] == curr_end[0]:    # vertical
                    if   point[1] > curr_end[1]: direction = 'n'
                    elif point[1] < curr_end[1]: direction = 's'
                    else:
                        raise ValueError("IMPOSSIBLE DIRECTION {} {}".
                                         format(point,curr_end))
                elif point[1] ==  curr_end[1]: # horizontal
                    if   point[0] > curr_end[0]: direction = 'e'
                    elif point[0] < curr_end[0]: direction = 'w'
                    else:
                        raise ValueError("IMPOSSIBLE DIRECTION {} {}".
                                         format(point,curr_end))
                else:
                    component.append(curr_end)
                    waypoints.append(component)
                    component = []
                    curr_start, curr_direction = None, None                
                    # raise ValueError("IMPOSSIBLE DIRECTION")

                if curr_direction is None:
                    curr_direction = direction
                    curr_end = point
                elif curr_direction == direction:
                    curr_end = point
                else:
                    # commit corner
                    component.append(curr_end)
                    curr_start = curr_end
                    curr_end = point
                    curr_direction = direction

            else:
                component.append(point)
                curr_start, curr_end = point, point
                curr_mat, curr_direction = point[2], None


        component.append(curr_end)
        waypoints.append(component)
        return Route(component)



#####
# SEGMENT

SEG_CACHE = {}

@aux.Timer.timeit
def make_segment_rect(A,B,label,contoured=False,force_eol=True):
    """Returns rectangle representation of segment.
    If contoured True, then add spacing contour with end of line spacing
    """
    '''
    global SEG_CACHE
    if (A,B) in SEG_CACHE:
        val = SEG_CACHE[(A,B)]
        return Rect(val[0],val[1],val[2],val[3],val[4],label,points=False)
    '''
    
    # make search area
    x,y = min(A[0],B[0]),min(A[1],B[1])
    mat = A[2]
    mat_width = dr.material_width[mat]
    seg_width = A[3] if len(A) > 3 else mat_width
    # calculate width and height of segment
    if A[0] != B[0]:
        w = abs(A[0] - B[0]) + mat_width
        h = seg_width
    elif A[1] != B[1]:
        h = abs(A[1] - B[1]) + mat_width
        w = seg_width
    else:
        w,h = seg_width,seg_width

    # not contoured, return just rectangle
    if not contoured:
        return Rect(x,y,w,h,mat,label,points=False)
        
    # calculate contour (with end of line)
    spacing = dr.material_spacing[mat]
    eol = dr.end_of_line[mat] if mat in dr.end_of_line else spacing
    contour_x = eol if force_eol or h < eol else spacing
    contour_y = eol if force_eol or w < eol else spacing
    x -= contour_x
    w += 2 * contour_x
    y -= contour_y
    h += 2 * contour_y

    SEG_CACHE[(A,B)] = (x,y,w,h,mat)

    return  Rect(x,y,w,h,mat,label,points=False)
