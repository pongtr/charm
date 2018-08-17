#!/usr/bin/env python3
"""Route/Net ordering
"""

import data_structures as ds
import auxiliary as aux

#####
# NET ORDERING

def net_rule3(layout):
    """Given a layout, return an ordered list of nets
    """

    def get_mbb(label,layout):
        """Get the manhattan bounding box for a given label
        """
        nodes = layout.nodes[label]

        bottom_left = (nodes[0].x,nodes[0].y)
        top_right = (nodes[0].x + nodes[0].w, nodes[0].y + nodes[0].h)
        for n in nodes:
            bottom_left = (min(n.x,bottom_left[0]),min(n.y,bottom_left[1]))
            tr_x = max(n.x + n.w, top_right[0])
            tr_y = max(n.y + n.h, top_right[1])
            top_right = (tr_x, tr_y)

        return bottom_left, top_right
    
    def get_mbb_rect(label,layout):
        """Wrap the manhattan bounding box as a rect
        """
        bottom_left, top_right = get_mbb(label,layout)
        return ds.Rect(bottom_left[0],bottom_left[1],
                       top_right[0] - bottom_left[0],
                       top_right[1] - bottom_left[1],
                       None)

    # find number of pins from other nets inside mbb of given net
    pins_inside = {}
    for l in layout.labels:
        pins_inside[l] = 0
        mbb_rect = get_mbb_rect(l,layout)

        # find pins inside the mbb
        for l2 in layout.labels:
            if l == l2: continue # skip current net
            for n in layout.nodes[l2]:
                if mbb_rect.overlaps(n):
                    pins_inside[l] += 1
                    
    # sort by increasing number of pins and return
    return [net for net in sorted(pins_inside, key=pins_inside.get)]
            
#####
# NODE ORDERING
# nodes within each net

def closest_first(components,checked_pairs):
    """Given a list of components, return the pair of components with shortest
    manhattan distance between them first
    """
    dists = {}
    shortest, shortest_pair = None, None
    for i,cp1 in enumerate(components):
        for j,cp2 in enumerate(components[i + 1:]):
            dist = aux.manhattan_components(cp1,cp2)
            if ((cp1,cp2) not in checked_pairs and
                (shortest is None or dist < shortest)):
                shortest, shortest_pair = dist, (cp1,cp2)
    return shortest_pair

#####
# PAIR ODERING

def pair_rule3_closest(layout):
    """Order nets based on rule3 then order nodes by closest pair first
    """
    # order nets by rule3
    nets = net_rule3(layout)
    
    order = []

    # go through nets and order pairs within
    for net in nets:
        pairs = {}
        components = layout.components[net]
        for i,cp1 in enumerate(components):
            for j,cp2 in enumerate(components[i+1:]):
                dist = aux.manhattan_components(cp1,cp2)
                pairs[(cp1,cp2)] = dist
        # sort by increasing distance
        order += [pair for pair in sorted(pairs, key=pairs.get)]

    # return sorted order
    return order
    
def pair_rule3(layout,ordering_cache,count_same_net=True):
    """Ordering based on rule3 but by pairs and not net
    """

    def get_pairs(layout):
        """Returns all pairs of components
        """
        pairs = []
        for net in layout.labels:
            components = layout.components[net]
            for i,cp1 in enumerate(components):
                for j,cp2 in enumerate(components[i+1:]):
                    pairs.append((cp1,cp2))
        return pairs

    def get_mbb(pair):
        """Returns manhattan bounding box of the pair as a Rect
        """
        cp1, cp2 = pair
        x0, x1 = min(cp1.x0,cp2.x0), max(cp1.x1,cp2.x1)
        y0, y1 = min(cp1.y0,cp2.y0), max(cp1.y1,cp2.y1)
        return ds.Rect(x0,y0,x1-x0,y1-y0,None)
        
    
    def pins_inside(pair,layout):
        """Returns number of pins inside the mbb created by the pair
        """
        if pair in ordering_cache:
            return ordering_cache[pair]
        
        mbb = get_mbb(pair)
        n_pins = 0
        for net in layout.labels:
            # skip same nets
            if not count_same_net and net == pair[0].label: continue

            # count number of pins inside
            for n in layout.nodes[net]:
                if mbb.overlaps(n):
                    n_pins += 1

        ordering_cache[pair] = n_pins
        return n_pins

    return sorted(get_pairs(layout), key=lambda pair: pins_inside(pair,layout))
    
