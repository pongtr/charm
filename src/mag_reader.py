#!/usr/bin/env python3
'''
magconverter.py

converts mag file to a list of rects readable in drawing.py
'''

import sys
from collections import defaultdict
from parse import parse # pip3 install parse
from pprint import pprint
from data_structures import Rect

MATERIALS = {
    'ntransistor': ['ndiff','poly'],
    'ptransistor': ['pdiff','poly'],
    'ndiffusion': ['ndiff'],
    'pdiffusion': ['pdiff'],
    'ndcontact' : ['ndc','ndiff'],
    'pdcontact' : ['pdc','pdiff'],
    'polysilicon': ['poly'],
    'polycontact': ['pc','poly'],
    'metal1' : ['m1'],
    'metal2' : ['m2'],
    'metal3' : ['m3'],
    'm2contact' : ['m2c','m1','m2'],
    'm3contact' : ['m3c','m2','m3']
}

def read(magfile,correct_offset=True,strip_label=True):
    """Given a magic file, convert into a list of rectangles from drawing.py

    Options:
    - correct_offset: if True, then make lowest left 0,0
    - strip_label: if True, returned rectangles don't have labels
    """
    linenum = 0
    material = None
    tag = None
    rectangles = defaultdict(list)
    labels = []
    ret_rects = [] # rectangles to return
    min_x, min_y = None, None
    with open(magfile) as f:
        for line in f:
            line = line.strip()

            # check if file is magic file
            if linenum == 0 and line != 'magic':
                print("invalid magic file")
                sys.exit(1)

            # ignore tech and timestamp lines
            if line.startswith('tech') or line.startswith('timestamp'):
                continue

            # get the tag
            if line.startswith('<<') and line.endswith('>>'):
                tag = line[3:-3]
                if tag in MATERIALS:
                    material = tag
                continue

            if line.startswith('rect'):
                rect = parse('rect {} {} {} {}',line)
                rect = [int(v) for v in rect]
                rectangles[material].append(rect)

                # try to get min x and min y
                if min_x is None or min_y is None:
                    min_x, min_y = rect[0], rect[1]
                if rect[0] < min_x: min_x = rect[0]
                if rect[1] < min_y: min_y = rect[1]

            if tag == 'labels':
                label = parse('rlabel {} {} {} {} {} {} {}',line)
                labels.append(label)

            linenum += 1

    # join all adjacent poly blocks
    poly_rects = []

    for material,rects in rectangles.items():
        if material is None:
            continue
        for r in rects:
            r = list(map(int, r))

            # check if label is on it
            this_labels = []
            for l in labels:
                l = list(l)
                # check material
                if l[0] != material:
                    continue
                # check dimensions
                for i in range(1,5):
                    l[i] = int(l[i])
                if (l[1] < r[0] or l[2] < r[1] or
                    l[3] > r[2] or l[4] > r[3]):
                    continue
                # attach label
                this_labels.append(l[6])

            for i,m in enumerate(MATERIALS[material]):
                if strip_label or len(this_labels) == 0 or i > 0:                    
                    if m == 'poly':
                        poly_rects.append(r)
                    else:
                        ret_rects.append(
                            Rect(r[0], r[1],r[2] - r[0], r[3] - r[1],m)
                        )
                else:
                    for label in this_labels:
                        if m == 'poly':
                            poly_rects.append(r + [label])
                        else:
                            ret_rects.append(
                                Rect(r[0], r[1],r[2] - r[0],
                                     r[3] - r[1],m,label)
                            )

    # join adjacent poly blocks
    # pprint(poly_rects)
    rect = None
    while len(poly_rects) > 0:
        if rect is None:
            rect = poly_rects.pop(0)

        extended = False
        for ext in poly_rects:
            if rect[1] == ext[1] and rect[3] == ext[3]: # same vertically
                if rect[2] == ext[0]: # extend right
                    if len(ext) == 5 and len(rect) == 4: rect.append(ext[4])
                    rect[2] = ext[2]
                    poly_rects.remove(ext)
                    extended = True
                if rect[0] == ext[2]: # extend left
                    if len(ext) == 5 and len(rect) == 4: rect.append(ext[4])
                    rect[0] = ext[0]
                    poly_rects.remove(ext)
                    extended = True
            if rect[0] == ext[0] and rect[2] == ext[2]: # same horizontally
                if rect[3] == ext[1]: # extend up
                    if len(ext) == 5 and len(rect) == 4: rect.append(ext[4])
                    rect[3] = ext[3]
                    poly_rects.remove(ext)
                    extended = True
                if rect[1] == ext[3]: # extend down
                    if len(ext) == 5 and len(rect) == 4: rect.append(ext[4])
                    rect[1] = ext[1]
                    poly_rects.remove(ext)
                    extended = True

        if not extended or len(poly_rects) == 0:
            r = rect
            if len(rect) == 5:
                ret_rects.append(
                    Rect(r[0], r[1],r[2] - r[0], r[3] - r[1],'poly',r[4])
                )
            else:
                ret_rects.append(
                    Rect(r[0], r[1],r[2] - r[0], r[3] - r[1],'poly')
                )
                
            rect = None
            # pprint(poly_rects)

    # join m3 blocks:
    join_rects('m3',ret_rects)
        
            
    if correct_offset:
        for r in ret_rects:
            r.offset(-1 * min_x, -1 * min_y)
            
    return ret_rects

def join_rects(mat,all_rects):
    y_rects = defaultdict(list) # rects of material mat, key y pos
    old_rects = []
    for rect in all_rects:        
        if rect.m == mat:
            y_rects[rect.y].append(rect)
            old_rects.append(rect)
            
    x_rects = defaultdict(list) # merged rects with key x pos
    for y,rects in y_rects.items():
        rects.sort(key=lambda rect: rect.x)
        cr = rects.pop(0) # current rect
        x,y,w,h,l = cr.x, cr.y, cr.w, cr.h, cr.l
        while len(rects) > 0:
            nr = rects.pop(0)
            if nr.h != cr.h or nr.x != cr.x1 + 1:
                x_rects[x].append(Rect(x,y,w,h,mat,l))
                x,y,w,h,l = nr.x,nr.y,nr.w,nr.h,nr.l                
            else:
                if nr.l is not None and nr.l != label:
                    raise ValueError("Invalid labels")
                if l is None:
                    l = nr.l
                w += nr.w
            cr = nr
        x_rects[x].append(Rect(x,y,w,h,mat,l))                

    # merge in y direction
    final_rects = []
    for x, rects in x_rects.items():
        rects.sort(key=lambda rect: rect.y)
        cr = rects.pop(0)
        x,y,w,h,l = cr.x,cr.y,cr.w,cr.h,cr.l
        while len(rects) > 0:
            nr = rects.pop(0)
            if nr.w != cr.w or nr.y != cr.y1 + 1:
                final_rects.append(Rect(x,y,w,h,mat,l))
                x,y,w,h,l = nr.x,nr.y,nr.w,nr.h,nr.l                
            else:
                if nr.l is not None and nr.l != label:
                    raise ValueError("Invalid labels")
                if l is None:
                    l = nr.l
                h += nr.h
            cr = nr
        final_rects.append(Rect(x,y,w,h,mat,l))                
            
    # remove old rects from original list
    for rect in old_rects:
        all_rects.remove(rect)

        
    # add new rects to list
    all_rects += final_rects
