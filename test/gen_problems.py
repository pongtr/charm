#!/usr/bin/env python3
'''
gen_problems.py

generate simple problems of nodes in random places
'''

import sys
import os
sys.path.append(os.path.abspath('../src'))
import data_structures as ds
import design_rules as dr
import random

X_MIN,X_MAX = 0,30
Y_MIN,Y_MAX = 0,30
LIMIT = 100
MAT = ['ndc','m3','m4']

# set random seed
random.seed(100)

def generate_case(n_nodes, n_nets, x_min = X_MIN, x_max = X_MAX,
                  y_min = Y_MIN, y_max = Y_MAX,
                  label_prefix = "",seed = None,
                  pairs = False):
    if label_prefix != '':
        label_prefix += '_'
    if seed is not None:
        random.seed(seed)
    rectangles, contours = [], []
    if pairs: n_nodes = 2 * n_nets
    for i in range(n_nodes):
        # pick material
        mat = random.choice(MAT)

        # width
        width = dr.material_width[mat]

        # spacing
        spacing = 4

        overlapping = True

        iteration = 0
        while overlapping or iteration == LIMIT:
            iteration += 1
            
            # generate position
            pos = (random.randint(x_min,x_max),random.randint(y_min,y_max))

            # net
            net = i // 2 if pairs else random.randint(0,n_nets)
            net_name = "{}{}".format(label_prefix,net)

            # generate rectangle
            rect = ds.Rect(pos[0],pos[1],width,width,mat,net_name)

            overlapping = False
            for contour in contours:
                if contour.overlaps(rect):
                    overlapping = True

            if not overlapping:
                rectangles.append(rect)

                contour = ds.Rect(
                    rect.x - spacing,
                    rect.y - spacing,
                    rect.w + 2 * spacing,
                    rect.h + 2 * spacing,
                    rect.m,
                    rect.l
                )
                
                contours.append(contour)
                
    print("Done generating.")

    return rectangles
        
