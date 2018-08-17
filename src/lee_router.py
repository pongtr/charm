#!/usr/bin/env python3
"""Lee Maze Router
"""

import data_structures as ds
import auxiliary as aux
import design_rules as dr
import design_rule_checker as drc

import time

TIMEOUT = 120

@aux.Timer.timeit
def lee_route_components(cp1,cp2,layout,drc_cache,vertical=False):
    """Genereate route between cp1 and cp2 using Lee's algorithm
    Return route if possible, False otherwise.
    
    vertical option waives contact cost (used for pin elevation)
    """

    # Initialize variables
    visited = {} # dictionary of visited points
    queue = ds.SPQ()
    found = False
    start_time = time.time()
    label = cp1.label

    # Generate starting points and add to queue
    starting_points = get_starting_points([cp1,cp2],visited)
    for component,points in starting_points.items():
        for sp in points:
            queue.put(0,(sp,component))

    # Keep going until no more valid points or path found
    while not queue.empty() and not found:

        # Timeout
        if time.time() - start_time > TIMEOUT:
            break        

        # Get information
        vertex, cpn = queue.get()
        info = visited[(vertex,cpn)]

        # Check bounding box
        if not layout.bounding_box.is_in(vertex):
            continue

        # Print status
        # if not vertical:
        if not vertical: print_status(info.cost,start_time)

        # Get direction changes
        changes = get_changes(vertex,info)

        # Check each change
        for change in changes:
            # In vertical mode, cp1 can only go up, cp2 can only go down
            if vertical:
                if cpn == cp1 and change == (0,0,-1): continue
                if cpn == cp2 and change == (0,0,1): continue

            # Get new mat/continue if not valid
            mat = get_mat(info,change)
            if not mat: continue

            # New vertex
            new = (vertex[0] + change[0], vertex[1] + change[1], mat)
            key = (new,info.component)
            new_info = get_info(info,change,new,vertical)            
            if key in visited: continue

            # Check if found path
            match = find_match(new,new_info,visited,[cp1,cp2])
            if match:
                found = True
                
                # retrace
                route_points = (new_info.retrace() +
                                list(reversed(visited[match].retrace())))
                return ds.Route.from_points(route_points)

            # Check if drawable
            drawable = drc.check_point(new,label,layout,drc_cache)
            if not drawable or isinstance(drawable,list):
                visited[key] = False
                continue
            
            # Add info to visited and add to queue
            visited[key] = new_info
            queue.put(new_info.cost,(new,cpn))

    return False


######################################
# PRIVATE FUNCTIONS

class LeeEntry:
    def __init__(self,point,cost,parent,change,jog,prev_jog,length,cpn):
        self.point = point
        self.material = point[2]
        self.cost = cost
        self.parent = parent
        self.change = change
        self.jog = jog
        self.prev_jog = prev_jog # length of previous jog. used at end
        self.length = length     # length of current path (same material)
        self.area = self.get_area()
        self.component = cpn # origin component
                                       

    def retrace(self):
        """Given an entry, retrace back to origin. Return list of points
        """
        if self.parent is None:
            return [self.point]
        else:
            return self.parent.retrace() + [self.point]

    def get_area(self):
        width = dr.material_width[self.material]
        return (self.length + width - 1) * width

def get_starting_points(components,visited):
    """Generates starting points from each component and add to visited dict
    """
    starting_points = {}
    for c in components: # iterate through components
        starting_points[c] = []
        for p in c.line: # iterate through points in component
            if p[2] not in dr.routing_materials: continue # non-routing material
            visited[(p,c)] = LeeEntry(p,0,None,None,1,0,1,c)
            starting_points[c].append(p)
    return starting_points

def get_changes(vertex,info):
    """Give all the possible direction changes for given point
    """
    # get material
    mat = info.material
    layer = dr.layers_mat[mat]

    # contact keep shifting layer
    if mat not in dr.material_directions and mat in dr.contact_materials:
        return [info.change]

    # get turn options
    turn = dr.material_directions[mat]
    min_jog = dr.point_to_edge[mat]
    turnable = (info.jog >= min_jog or info.prev_jog >= min_jog or
                info.change is None)
    layer_change = info.area >= dr.min_area[mat]
        
    # possible changes for each direction
    dx,dy,dz = [(-1,0,0),(1,0,0)],[(0,-1,0),(0,1,0)],[(0,0,-1),(0,0,1)]

    changes = []
    if info.change in dz: # just had layer change can go any direction
        if 'x' in turn:
            changes += dx
        if 'y' in turn:
            changes += dy
    else:
        # continue in same direction
        if info.change is not None:
            changes.append(info.change)
        
        # turns if possible
        if 'x' in turn and info.change not in dx and turnable:
            changes += dx
        if 'y' in turn and info.change not in dy and turnable:
            changes += dy
        
        # layer change if possible
        if layer_change:
            if dr.layers_mat[mat] > 0:
                changes.append((0,0,-1))
            if dr.layers_mat[mat] < len(dr.mat_layers) - 1:
                changes.append((0,0,1))

    return changes

def get_mat(info,change):
    """Returns the new material. False if invalid
    """
    layer = dr.layers_mat[info.material]
    new_layer = layer + change[2]
    try:
        return dr.mat_layers[new_layer]
    except KeyError:
        return False
    
def get_info(info,change,new,vertical):
    """Returns a new LeeEntry for new point
    """

    # Calculate cost
    if change[2] == 0: # same material
        cost = dr.material_cost[new[2]] * dr.material_width[new[2]]
    elif vertical:     # material change cost waived
        cost = 0
    else:              # material change
        cost = dr.material_cost[new[2]] * (dr.material_width[new[2]] ** 2)
    cost += info.cost

    # Calculate jogs
    if change == info.change: # continue straight
        jog, prev_jog = info.jog + 1, info.prev_jog
    elif change[2] == 0:      # turn but same material
        jog, prev_jog = 1, info.jog
    else:                     # new material
        jog, prev_jog = 1, 0

    # Calculate length of same material path
    length = info.length + 1 if change[2] == 0 else 1
        
    return LeeEntry(new,cost,info,change,jog,prev_jog,
                    length,info.component)

def find_match(new,new_info,visited,components):
    """Returns True if a valid path is found
    """
    mat = new_info.material
    # cannot connect on contact
    if mat not in dr.routing_materials:
        return False
    
    min_jog = dr.point_to_edge[mat]

    # find match with other components
    for c in components:
        if c == new_info.component: continue        
        key = (new,c)
        if key in visited:
            info = visited[key]
            if not info: return False
            changes = set([info.change,new_info.change])
            dx,dy = set([(1,0,0),(-1,0,0)]),set([(0,1,0),(0,-1,0)])            
            if changes == dx or changes == dy: # same direction
                if info.jog + new_info.jog >= min_jog:
                    return key
            else: # different direction
                min_jog = dr.point_to_edge[new[2]]
                if info.jog >= min_jog or new_info.jog >= min_jog:
                    return key
                
    return False

def print_status(cost,start_time):
    # determine color
    elapsed = time.time() - start_time
    if elapsed > TIMEOUT * 0.98: color = 'FAIL'
    if elapsed > TIMEOUT * 0.75: color = 'WARNING'
    else:                     color = 'OKGREEN'

    # print
    elapsed_time = "{:.2f}s".format(elapsed)
    print("   LEE: Cost {:4d} | Time {}".
          format(cost,aux.color_format(elapsed_time,color)),
          end="\r")
    

