#!/usr/bin/env python3
"""Design Rule Checker: Checks for spacing with existing layout & routes
"""

import data_structures as ds
import auxiliary as aux
import design_rules as dr

class Cache:
    """DRC Cache for memoization of design rule checks 
    """    

    def __init__(self):
        self.layout = {}
        self.route = {}

class ComponentConflict:
    """Conflict with existing component
    """
    def __init__(self,segment,label,conflict_comp,conflict_seg):
        self.segment = segment
        self.label = label
        self.conflict_comp = conflict_comp
        self.conflict_seg = conflict_seg
        
@aux.Timer.timeit    
def check_segment(A,B,label,layout,drc_cache,point=False,components=[]):
    """Checks if a segment is drawable.
    If point is True, then it allows getting close to existing net
    """

    @aux.Timer.timeit
    def get_search_points(search_area,grid_points):
        return search_area.points.intersection(grid_points)

    @aux.Timer.timeit
    def with_layout():
        """Search through existing layout
        """
        if mat in dr.contact_materials:
            contact = True
            layers = []
            if layer > 2: layers.append(layer - 2)
            layers.append(layer)
            if layer < len(dr.mat_layers) - 3: layers.append(layer + 2)
        else:
            contact = False
            layers = [layer]

        for l in layers:
            # ignore invalid layers
            if l >= len(layout.grid) or l < 0: continue
            # mask grid with search area
            grid_points = layout.grid_points[l]
            search_points = get_search_points(search_area,grid_points)
            searched_rects = set()
            for sp in search_points:
                existing_rects = layout.grid[l][sp]
                for rect in existing_rects:
                    # already ok
                    if rect in searched_rects:
                        continue

                    # different net conflict
                    if contact or rect.l != label:
                        return False

                    '''
                    # different component of same net
                    in_comp = False
                    for comp in components:
                        if rect in comp.nodes:
                            in_comp = True
                            break
                    if not in_comp: return False
                    '''

                    searched_rects.add(rect)

        return True

    def check_parallel_spacing(seg1,seg2):
        """Given two segments, return False if parallel and closer than 
        minimum spacing, else return True
        """

        # check if material are touching. If not, return True
        if seg1[0][2] != seg2[0][2]: return True
        
        # get directions and check if parallel
        d1, d2 = aux.get_dir(seg1[0],seg1[1]), aux.get_dir(seg2[0],seg2[1])
        if d1 != d2: return True

        # check spacing
        min_spacing = dr.material_spacing[seg1[0][2]]
        lower = seg1 if seg1[0][not d1] < seg2[0][not d1] else seg2
        higher = seg1 if seg1[0][not d1] >= seg2[0][not d1] else seg2
        width = (lower[0][3]
                 if len(lower[0]) > 3
                 else dr.material_width[lower[0][2]])
        space = higher[0][not d1] - lower[0][not d1] - width
        if space < 0 or space > min_spacing:
            return True

        # min spacing so check if overlap
        if (max(seg1[0][d1],seg1[1][d1]) > min(seg2[0][d1],seg2[0][d1]) and
            min(seg1[0][d1],seg1[1][d1]) < max(seg2[0][d1],seg2[1][d1])):
            return False

        return True
        

    # key for caching
    key = (A,B,label)

    # material
    mat = A[2]
    
    # get search area
    search_area = ds.make_segment_rect(A,B,label,contoured=True)
    contact_search = ds.make_segment_rect(A,B,label,contoured=False)
    layer = dr.layers_mat[mat]

    # search through existing layout
    if key not in drc_cache.layout:
        drc_cache.layout[key] = with_layout()
    if not drc_cache.layout[key]:
        return False
                
    # search through existing routes
    conflicts = []
    if key not in drc_cache.route:
        drc_cache.route[key] = {} # initialize entry for segment
    for net in layout.labels:
        # search through components
        for comp in layout.components[net]:
            for seg,rect in comp.seg_rects.items():
                comp_key = (comp,seg) # component key
                seg_layer = dr.layers_mat[rect.m]
                if comp_key not in drc_cache.route[key]:
                    # different net and overlaps
                    if (net != label and
                        seg_layer == layer and
                        rect.overlaps(search_area)):
                        drc_cache.route[key][comp_key] = True
                    # contact overlapping another contact
                    elif (mat in dr.contact_materials and
                        rect.m in dr.contact_materials and
                        abs(layer - seg_layer) < 3 and
                        rect.overlaps(contact_search)):
                        drc_cache.route[key][comp_key] = True
                    # same net and parallel without enough spacing
                    elif (not point and net == label and
                          not check_parallel_spacing((A,B),seg)):
                        drc_cache.route[key][comp_key] = True
                    else:
                        drc_cache.route[key][comp_key] = False
                if drc_cache.route[key][comp_key]:
                    conflict = ComponentConflict((A,B),label,comp,seg)
                    conflicts.append(conflict)

    if len(conflicts) > 0:
        return conflicts
    else:
        return True

def check_route(route,label,layout,drc_cache,components=[]):
    """Checks whether the route is drc clean with respect to existing 
    layout and routes. If clean, return True. If conflict with existing 
    layout, return False. If conflict with existing route, return 
    a RouteConflict.
    """
    conflicts = []
    for seg in range(len(route.waypoints) - 1):
        A,B = route.waypoints[seg],route.waypoints[seg+1]
        segment_result = check_segment(A,B,label,layout,drc_cache,components)

        # conflicts with existing layout => early termination
        if not segment_result:
            return False
        # conflicts with existing route => store for potential rip-up
        elif isinstance(segment_result,list):
            conflicts += segment_result

    # return list of layout conflcits
    if len(conflicts) > 0:
        return conflicts
    # no conflicts. return True
    else:
        return True

def check_point(point,label,layout,drc_cache):
    """Given a point, return True if drawable, False if conflicts with existing
    layout, and a list of route conflicts if conflicts with existing route
    """
    return check_segment(point,point,label,layout,drc_cache,point=True)







