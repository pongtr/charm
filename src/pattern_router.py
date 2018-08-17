#!/usr/bin/env python3
"""Pattern Router (|,L,Z,U)
"""

import design_rules as dr
import auxiliary as aux
import data_structures as ds
import design_rule_checker as drc
import pprint as pprint


TERMINATE = 50000
LAZY_THRESHOLD = 100

@aux.Timer.timeit
def pattern_route_components(cp1,cp2,layout,drc_cache,elevate=True):
    """Generate lowest cost legal route  between two components
    """
    if elevate:
        # get the highest layer from each
        hl1,hl2 = cp1.line_materials()[-1], cp2.line_materials()[-1]
        # elevate a component if needed
        if hl1 < hl2:
            print("  Elevating")
            cp1.elevate(dr.mat_layers[hl2],layout)
        if hl2 < hl1:
            print("  Elevating")
            cp2.elevate(dr.mat_layers[hl1],layout)

    
    for i,route in enumerate(generate_routes(cp1,cp2)):
        print_status(i,route.cost)
        if i > TERMINATE: break
        drc_status = drc.check_route(route,cp1.label,layout,drc_cache,[cp1,cp2])
        if not drc_status: # conflict with existing layout
            continue
        elif isinstance(drc_status,list): # conflict with existing route
            continue
        else:
            return route
    return False



            
######################################
# PRIVATE FUNCTIONS

####
# GENERATE POINTS

def generate_routes(cp1,cp2,lazy=False):
    """Generator that returns routes between points from two components
    in increasing cost. Lazy True attempts to yield one by one in heuristic
    order. Lazy False will return by increasing cost.
    """
    def mat_cost(p):
        """Returns cost of material cost in a given pair p
        """
        p1,p2 = p[0],p[1]
        mat1,mat2 = p1[2],p2[2]
        estimate = ((dr.material_cost[mat1] + dr.material_cost[mat2]) / 2)
        contact = dr.get_contact([mat1,mat2])
        if mat1 != mat2 and contact is not None:
            estimate += dr.material_cost[contact] * dr.material_width[contact]
        return estimate
        
    def get_pair_distance(cp1,cp2):
        """Returns a sorted list of point pairs between cp1 and cp2.
        Sorted by increasing manhattan distance
        """        
        pair_distance = {}
        for p1 in cp1.line:
            if p1[2] not in dr.routing_materials: continue        
            for p2 in cp2.line:
                if p2[2] not in dr.routing_materials: continue
                pair_distance[(p1,p2)] = aux.manhattan_distance(p1,p2)
        key = lambda p: pair_distance[p] * mat_cost(p)
        pairs = [k for k in sorted(pair_distance,key=key)]
        return pairs, pair_distance

    pairs, pair_distance = get_pair_distance(cp1,cp2)
    route_pq = ds.SPQ()

    # print(len(pairs))
    if len(pairs) > LAZY_THRESHOLD:
        lazy = True
        
    detour_dist,detouring = 0, []
    for p in pairs:
        # generate and return all possible detours first
        current_dist = pair_distance[p]
        for dt in range(detour_dist,current_dist):
            for d_pair in detouring:
                d_pair[2] += 1 # increase detour amount
                start,end,detour = d_pair[0],d_pair[1],d_pair[2]
                routes = route_points(start,end,'U',detour)
                routes.sort(key=lambda r:r.cost)
                for route in routes:
                    if (lazy and len(route.materials) == 1 and
                        (route_pq.empty() or route.cost < route_pq.peek())):
                        yield route # yield if lowest cost
                    else:
                        route_pq.put(route.cost,route) # otherwise add to pq
        detour_dist = current_dist

        # generate direct routes in MBB (O,I,L,Z)
        start,end = p[0],p[1]
        if start[2] not in dr.mat_layers or end[2] not in dr.mat_layers:
            continue # skip invalid starting materials
        for pattern in ['O','I','L','Z']:
            routes = route_points(start,end,pattern)
            if len(routes) == 0: continue
            
            routes.sort(key=lambda r: r.cost)

            # yield routes in pq with lower cost
            while (lazy and not route_pq.empty() and
                   route_pq.peek() < routes[0].cost):
                yield route_pq.get()

            # yield lowest cost route
            for i,route in enumerate(routes):
                if (lazy and len(route.materials) == 1 and
                    (route_pq.empty() or route.cost < route_pq.peek())):
                    yield route
                else:
                    route_pq.put(route.cost,route)
        detouring.append([start,end,0])

    while not route_pq.empty():
        yield route_pq.get()


    
        
def route_points(source,dest,pattern,detour=0):
    """Generate routes between source and dest points with specified pattern

    Source and Dest are points to connect
    Patterns can be 'O','I','L','Z', or 'U'
    Detour is the extra amount of detour for 'U' pattern
    """
    def unfiltered(source,dest,pattern,detour):
        """Returns basic geometry without regards to certain design rules
        """
        if pattern == 'O': # source and dest are the same
            return incident(source,dest)
        elif pattern == 'I':
            return i_pattern(source,dest)
        elif pattern == 'L':
            return l_pattern(source,dest)
        elif pattern == 'Z':
            return z_pattern(source,dest)
        elif pattern == 'U':
            return u_pattern(source,dest,detour)

    def seg_length(p1,p2):
        """Returns the legnth of the segment between p1 and p2
        """
        if p1[0] != p2[0] and p1[1] != p2[1]:
            raise ValueError("Invalid segment {} {}".format(p1,p2))
        return aux.manhattan_distance(p1,p2)

    def check_jog(route):
        """Given a route, return True if jog lengths are ok.
        First, last, and segments that touch contact must be at least min jog
        Other segments can be shorter if adjacent segment is at least min jog
        """

        prev_length = 0
        
        for seg in range(len(route) - 1):
            A,B = route[seg], route[seg+1]
            if A[2] != B[2]: # skip contacts
                continue
            A,B = route[seg], route[seg + 1]
            length = seg_length(A,B)
            if (seg == 0 or seg == len(route) - 2 or     # first/last segment
                (seg > 0 and route[seg-1][2] != A[2]) or # prev is contact
                (seg < len(route) - 2 and
                 A[2] != route[seg + 2][2]) or           # next is contact
                prev_length < dr.point_to_edge[A[2]]):   # prev seg too short
                if length < dr.point_to_edge[A[2]]: # make sure this jog is ok
                    return False
            prev_length = length

        return True
        
    filtered_routes = []
    for route in unfiltered(source,dest,pattern,detour):
        if check_jog(route):
            filtered_routes.append(ds.Route(route))
    return filtered_routes

####
# INCIDENT POINTS

def is_incident(s,d):
    """Returns True if s and d in same location (regardless of material). 
    False otherwise
    """
    return (s[0],s[1]) == (d[0],d[1])

def incident(s,d):
    """Returns route if source and dest can be connected with just layer change
    or if already connect. Returns [] otherwise
    """

    if s == d:
        width = dr.material_width[s[2]]
        return [[add_width(s,width),add_width(d,width)]]
    elif (s[0],s[1]) == (d[0],d[1]): # same position, different material
        contact = dr.get_contact([s[2],d[2]])
        width = dr.material_width[contact]
        if contact: # valid contact
            return [[
                add_width(s,width),
                (s[0],s[1],contact,width),
                add_width(d,width)
            ]]
        else:       # no contact between materials
            return []
    else:
        return []

def sandwich_contact(x,y,mat1,mat2,contact,out_width=None):
    """Generate a list of three points at x,y with [mat1, contact, mat2] 
    Widths of first and second segment same as contact width.
    Outgoing segment width out_width if specified, otherwise mat2 min width
    """
    c_width = dr.material_width[contact] # contact width
    p1 = (x,y,mat1,c_width)
    p2 = (x,y,contact,c_width)
    p3 = (x,y,mat2,out_width if out_width else dr.material_width[mat2])
    return [p1,p2,p3]

#####
# NO BEND (I SHAPE)

def is_i(s,d):
    """Returns True if s and d can be connected with I pattern,Fale otherwise
    """
    return s[0] == d[0] or s[1] == d[1]
    

def i_pattern(s,d):
    """Returns list of routes if source and dest can be connected with a
    straight line. If on adjacent layers, then allow layer change anywhere
    along the way. Return empty list if no route is valid.
    """

    # filter out incident
    if is_incident(s,d): return []
    
    # check if same x or same y
    if not is_i(s,d):
        return []

    # same material => simply connect
    if s[2] == d[2]:
        w = dr.material_width[s[2]]
        return [[add_width(s,w),add_width(d,w)]]

    # get contact
    contact = dr.get_contact([s[2],d[2]])
    if contact: # has valid contact => place contact anywhere on route
        routes = []
        drt = aux.get_dir(s,d) # direction: 0 horizontal, 1 vertical
        w = dr.material_width[contact]

        # get points along route
        for i in range(abs(s[drt] - d[drt]) + 1):
            if drt: # vertical
                x, y = s[0], min(s[1],d[1]) + i
            else:   # horizontal
                x, y = min(s[0],d[0]) + i, s[1]
            # add route
            routes.append([add_width(s,w)] +
                          sandwich_contact(x,y,s[2],d[2],contact) +
                          [add_width(d,w)])
        return routes
    else:
        return []    
        


####
# 1 BEND (L SHAPE)

def l_pattern(s,d):
    """Returns list of routes if source and dest can be connected with a
    L-shaped pattern. If on adjacent layers, then allow layer change anywhere
    along the route.
    """

    # filter out incident and i
    if is_incident(s,d) or is_i(s,d):
        return []

    # get corners
    c1_x, c1_y = s[0], d[1]
    c2_x, c2_y = d[0], s[1]

    # same material => just connect
    if s[2] == d[2]:
        w = dr.material_width[s[2]] # get material width
        c1 = (c1_x,c1_y,s[2],w)
        c2 = (c2_x,c2_y,s[2],w)        
        return [[add_width(s,w),ci,add_width(d,w)] for ci in [c1,c2]]

    # get contact
    contact = dr.get_contact([s[2],d[2]])
    if contact:
        w1 = dr.material_width[s[2]]
        p1 = add_width(s,w1)
        w2 = dr.material_width[d[2]]
        p2 = add_width(d,w2)
        routes = []
        for c in [(c1_x,c1_y),(c2_x,c2_y)]:
            corner = sandwich_contact(c[0],c[1],s[2],d[2],contact)
            routes.append([p1] + corner + [p2])
        return routes
    else:
        return []
    
        
def find_corners(source,dest):
    """Find the corners given two points
    Points given as cartesian co-ordinates tuple (x,y)
    Returns a list of tuples of corners
    If in straight line, then return emtpy list
    """

    # if incompatible material, return empty list
    if (source[2] != dest[2] and dr.get_contact([source[2],dest[2]]) is None):
        return False

    # straight line => no corners
    if source[0] == dest[0] or source[1] == dest[1]:
        if source[2] == dest[2]:
            return [] # same material, no corner
        else:
            # different material, "corner" can be anywhere along axis    
            dir = 0 if source[0] != dest[0] else 1
            points = []
            for i in range(source[dir],dest[dir],
                           -1 if dest[dir] < source[dir] else 1):
                points.append((i,source[1],dest[2]) if not dir
                              else (source[0],i,dest[2]))
            return points
         
    return [(source[0],dest[1],dest[2]),(dest[0],source[1],dest[2])]

    
#####
# 2 BENDS

def generate_projections(s,d):
    """Generates projections from source in x and y directions
    towards the destination
    """
    x_min,x_max = min(s[0],d[0]), max(s[0],d[0])
    y_min,y_max = min(s[1],d[1]), max(s[1],d[1])

    points = []
    for x in range(x_min, x_max + 1):
        points.append((x,s[1]))
    for y in range(y_min, y_max + 1):
        points.append((s[0],y))
    return points

def generate_detours(s,d,detour):
    """Generates fist waypoint of a detour from s to d
    """
    x_min,x_max = min(s[0],d[0]), max(s[0],d[0])
    y_min,y_max = min(s[1],d[1]), max(s[1],d[1])

    return [(s[0],y_max + detour),(s[0],y_min - detour),
            (x_min - detour,s[1]), (x_max + detour,s[1])]

def is_colinear(p1,p2,p3):
    """Returns True if p1,p2,and p3 are colinear and same material
    """

    # not all same material
    if not aux.all_equal([p1[2],p2[2],p3[2]]):
        return False

    for i in range(2):
        if aux.all_equal([p1[i],p2[i],p3[i]]):
            return True

    return False    

def pattern_2(s,d,first_wps):
    """Given source, destination, and list of first waypoints,
    Returns routes with first waypoint and one corner to the destination
    """
    s_layer, d_layer = dr.get_mat_layer(s[2]), dr.get_mat_layer(d[2])

    # require more than two layer transitions
    if abs(s_layer - d_layer) > 4:
        return []

    # determine possible materials of first waypoint
    wp1_mat = []
    for i in range(s_layer//2 - 1, s_layer//2 + 2):
        if i < 0: continue
        if abs(i - d_layer//2) <= 1:
            wp1_mat.append(dr.mat_layers[2 * i])
    # remove poly if not routing with poly
    no_poly = not any([m in ['poly','pc'] for m in [s[2],d[2]]])
    if no_poly and 'poly' in wp1_mat:
        wp1_mat.remove('poly')
            
    routes = []
    for wp1 in first_wps:
        p0 = add_width(s,dr.material_width[s[2]])
        for mat in wp1_mat:
            w = dr.material_width[mat]
            p1 = (wp1[0],wp1[1],mat,w) # first waypoint

            # generate contact for first waypoint if needed
            if mat != s[2]:
                contact = dr.get_contact([s[2],mat])
                sandwich = sandwich_contact(wp1[0],wp1[1],s[2],mat,contact)
                first_part = [p0] + sandwich
                first_part = first_part [:-1]
            else:
                first_part = [p0]

            # generate second waypoint
            for pattern in l_pattern(p1,d):
                route = first_part + pattern
                
                # check if any three points are co-linear
                has_colinear = False
                for i in range(len(route) - 3):
                    if is_colinear(route[i],route[i+1],route[i+2]):
                        has_colinear = True
                        break

                # add route
                if not has_colinear:
                    routes.append(first_part + pattern)
                    
    return routes
                    

def z_pattern(source,dest):
    return pattern_2(source,dest,generate_projections(source,dest))

def u_pattern(source,dest,detour):
    """Given a source and destination (x,y) tuples
    Returns a list of possible detour combinations
    with a given distance for the detour
    """
    return pattern_2(source,dest,generate_detours(source,dest,detour))

#####
# AUXILIARY FUNCTIONS

def add_width(point,width):
    """Given a point as (x,y,mat) and width,
    return a tuple with (x,y,mat,width)
    """
    return (point[0],point[1],point[2],width)

#####
# PRINT

def print_status(it,cost):
    # determine color
    if it > TERMINATE: color = 'FAIL'
    elif it > TERMINATE / 2: color = 'WARNING'
    else: color = 'OKGREEN'
    
    # get iteration
    iteration = "{}".format(it+1)

    # print
    print(
        "   PATTERN: Cost {} | Route {}"
        .format(cost,aux.color_format(it,color)),
        end='\r'
    )    
