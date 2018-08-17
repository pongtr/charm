#!/usr/bin/env python3
"""Controller for determining which pairs to route/rip up
"""

import pattern_router
import lee_router
import ordering
import auxiliary as aux
import design_rule_checker as drc
import data_structures as ds

import time

    
@aux.Timer.timeit
def naive(layout,inputs):
    print(aux.color_format("NAIVE CONTROLLER",'HEADER'))

    # Get parameters
    route_modes = inputs['route_modes']
    
    # initialize drc cache
    drc_cache = drc.Cache()
    
    # order nets
    nets = ordering.net_rule3(layout)
    checked_pairs = []

    # order each net
    for net in nets:
        pair = ordering.closest_first(layout.components[net],checked_pairs)
        while pair:
            checked_pairs.append(pair)
            route = route_pair(pair[0],pair[1],layout,
                               drc_cache,mode=route_modes)
            if route:
                # remove old components and create new component
                layout.components[net].remove(pair[0])
                layout.components[net].remove(pair[1])
                new_component = ds.Component.join(pair[0],pair[1],route)
                layout.components[net].append(new_component)
            else:
                print()

            pair = ordering.closest_first(layout.components[net],checked_pairs)

@aux.Timer.timeit
def lafrieda(layout,inputs):
    """Ordering based on Lafrieda MS thesis. DFS.
    """

    def print_status():
        print("{}/{} routed | {} ripups | Time elapsed {:.2f}s".
              format(n_success,total_pairs,n_ripups,time.time() - start_time))
    
    print(aux.color_format("LAFRIEDA CONTROLLER",'HEADER'))

    # Get parameters
    order_pairs = getattr(ordering,inputs['order'])
    route_modes = inputs['route_modes']
    
    # initialize drc cache
    drc_cache = layout.drc_cache
    # initialize ordering cache
    ordering_cache = {}
    
    route_stack, route_index = [], 0
    route_queue = order_pairs(layout,ordering_cache)
    routed_nets, tried_pairs, n_success = [], [], 0
    n_ripups, total_pairs = 0, get_total_routes(layout)
    start_time = time.time()

    while route_index < len(route_queue):
        print_status()
        
        pair = route_queue[route_index] # get pair
        net = pair[0].label             # get net
        
        # try to route
        route = route_pair(pair[0],pair[1],layout,drc_cache,mode=route_modes)

        # successful route
        if route:
            # remove old components and create new component
            layout.components[net].remove(pair[0])
            layout.components[net].remove(pair[1])
            new_component = ds.Component.join(pair[0],pair[1],route)
            layout.components[net].append(new_component)

            # add component to stack
            route_stack.append((new_component,pair[0],pair[1],route_index))
            route_queue = order_pairs(layout,ordering_cache)
            route_index = 0
            n_success += 1

        # unsuccessful route
        else:
            # continue if both components appear again
            cp0_in, cp1_in, both_in = False, False, False
            for p in route_queue[route_index + 1:]:
                if pair[0] in p: cp0_in = True
                if pair[1] in p: cp1_in = True
                if cp0_in and cp1_in:
                    both_in = True
                    route_index += 1
                    break
            if both_in:
                print(aux.color_format("...but there's hope","WARNING"))
                continue

            # Last occurence of at least one component, so rip up
            first_time = True
            print()
            while (len(route_stack) > 0 and
                   (first_time or route_index + 1 >= len(route_queue))):
                first_time = False
                last = route_stack.pop()
                old_net = last[0].label
                print(aux.color_format("     ripping up {}".format(old_net),
                                       "FAIL"))
                n_ripups += 1
                n_success -= 1

                layout.components[old_net].remove(last[0])
                layout.components[old_net].append(last[1])
                layout.components[old_net].append(last[2])
                route_index = last[3] + 1
            route_queue = order_pairs(layout,ordering_cache)
                
    print(aux.color_format("\nDONE! ","OKGREEN"),end="")
    print_status()
    print()


#################
# PRIVATE FUNCTIONS

def route_pair(cp1,cp2,layout,drc_cache,mode="l"):
    """Given two components, return shortest route if possible, else False
    Mode determines method used. Current options are (l)ee and (p)attern
    """
    # check if same net
    if cp1.label != cp2.label:
        raise ValueError("Different nets {} {}".format(cp1.label,cp2.label))

    print(aux.color_format("Routing net {}".format(cp1.label),'OKBLUE'))

    # try each router type
    while len(mode) > 0:
        m = mode[0]
        mode = mode[1:]
        if m == 'p': # pattern router
            result = pattern_router.route_components(
                cp1,cp2,layout,drc_cache
            )
        elif m == 'l': # lee router
            result = lee_router.route_components(
                cp1,cp2,layout,drc_cache
            )
        else:
            raise ValueError ("Invalid Mode {}".format(m))
        print()

        # has a solution
        if result:
            print(aux.color_format("   SUCCESS :D","OKGREEN"))
            return result

    # no solution
    print(aux.color_format("   UNSUCCESSFUL :( ","FAIL"),end="")
    return False

def get_total_routes(layout):
    """Returns total number of routes (n - 1) for each net
    """
    total = 0
    for label in layout.labels:
        total += len(layout.components[label]) - 1
    return total
