#!/usr/bin/env python3
'''
design_rules.py

design rules
'''

from collections import defaultdict

n_layers = 5 # number of metal layers

# == SPACING ==================

material_spacing = {
    'm1': 3,     # m1-m1
    'm2': 3,     # m2-m2
    'm3': 3,     # m2-m2
    'm4': 3,     # m2-m2
    'm5': 3,     # m2-m2
    'poly': 3,   # poly-poly
    'pdiff': 1,  # pdiff0- poly
    'ndiff': 1   # ndiff-poly
}
material_spacing['pc'] = max(material_spacing['m1'],material_spacing['poly'])
material_spacing['m2c'] = max(material_spacing['m1'],material_spacing['m2'])
material_spacing['m3c'] = max(material_spacing['m2'],material_spacing['m3'])
material_spacing['m4c'] = max(material_spacing['m3'],material_spacing['m4'])
material_spacing['m5c'] = max(material_spacing['m4'],material_spacing['m5'])
material_spacing['pdc'] = max(material_spacing['m1'],material_spacing['pdiff'])
material_spacing['ndc'] = max(material_spacing['m1'],material_spacing['ndiff'])

# == WIDTH =====================
material_width = {
    'm1': 3, # make this the same as contact size
    'm2': 3,
    'm3': 3,
    'm4': 3,
    'm5': 3,
    'poly':2,
    'pc': 4,
    'pdc': 4,
    'ndc': 4,
    'm2c': 4,
    'm3c': 4,
    'm4c': 4,
    'm5c': 4
    
}

# == COST ======================
material_cost = {
    'm1': 2,
    'm2': 2,
    'm3': 2,
    'm4': 2,
    'm5': 2,
    'm2c': 2,
    'm3c': 5,
    'm4c': 5,
    'm5c': 5,
    'poly': 5,
    'pc': 5
}

# == CONTACT MATERIALS ==========
contact_materials = {
    'ndc': ['m1'],
    'pdc': ['m1'],
    'pc' : ['poly','m1'],
    'm2c': ['m2','m1'],
    'm3c': ['m2','m3'],        
    'm4c': ['m3','m4'],
    'm5c': ['m4','m5'],        
}

def get_contact(materials):
    """Given a list of two materials,
    returns the contact material between the two
    or None if one does not exist
    """

    for contact, mat in contact_materials.items():
        if set(mat) == set(materials):
            return contact
    return None
        
# material_order = ['poly','m1','m2'] # just these two for now

# == MATERIAL IN EACH LAYER =======
'''
mat_layers = [['poly','pc','ndiff','ndc','pdiff','pdc'],
              ['m1','ndc','pdc','pc','m2c'],
              ['m2','m2c','m3c'],
              ['m3','m3c']]
'''

def get_mat_layer(mat):
    return layers_mat[mat]

diff_mats = {
    'pdiff': 0,
    'ndiff': 0,
    'pdc':   1,
    'ndc':   1
}


mat_layers, layers_mat = [], {}
routing_materials = []
def generate_mat_layers(n_layers):
    global mat_layers, layers_mat
    mat_layers.append('poly')
    routing_materials.append('poly')
    mat_layers.append('pc')
    for i in range(1, n_layers + 1):
        if i > 1:
            mat_layers.append('m{}c'.format(i))
        mat_layers.append('m{}'.format(i))
        routing_materials.append('m{}'.format(i))
    for i,mat in enumerate(mat_layers):
        layers_mat[mat] = i
    for k,v in diff_mats.items():
        layers_mat[k] = v
generate_mat_layers(n_layers)


connected_mats = [
    ['poly','pc'],
    ['m1','pc','m2c'],
    ['m2','m2c','m3c'],
    ['m3','m3c']
]

def get_other_mats():
    other_mats = defaultdict(list)
    for mats in connected_mats:
        for m in mats:
            other_mats[m] += [om for om in mats if om != m]
    return other_mats

other_mats = get_other_mats()

# == MATERIAL DIRECTIONS ============
'''
Options:
- s: straight only
- x: only horizontal
- y: only vertical
- xy: both horizontal and vertical
'''
material_directions = {
    'poly': 'xy',
    'm1': 'xy',
    'm2': 'xy',
    'm3': 'xy',
    'm4': 'xy',
    'm5': 'xy'
}

# == FIVE NEW RULES =============

# Line End Threshold (line vs joint)
line_end = {
    'poly': 3,  # arbitrary for now
    'm1': 3, # 0.04 microns
    'm2': 2, # 0.02 microns
    'm3': 2  # arbirary for now
}

# End of line
end_of_line = {
    'poly': 4, # arbitrary for now
    'm1': 4, # rules 506 : both sides >= 0.065 microns
    'm2': 4, # rules 606 : both sides >= 0.065 microns
    'm3': 4, # rules 606 : both sides >= 0.065 microns    
    'm4': 4, # rules 606 : both sides >= 0.065 microns
    'm5': 4, # rules 606 : both sides >= 0.065 microns    
}

# Point to edge
point_to_edge = {
    'poly': 5, # allow poly to turn for now
    'm1': 3,  # SE4 0.05 micron (same as min width)
    'm2': 3,  # SE5 0.05 micron (same as min width)
    'm3': 3,  # SE5 0.05 micron (same as min width)    
    'm4': 3,  # SE5 0.05 micron (same as min width)
    'm5': 3   # SE5 0.05 micron (same as min width)    
}

# Min area
min_area = {
    'poly':  4, # arbitrary
    'm1'  :  36, # 501d 0.01 micron2 (relative to min width 3)
    'm1se': 108, # 501aSE all edges less than 0.130 micron (8 lambda)
    'm2'  :  40, # 601d 0.01 micron2 (relative to min width 3)
    'm2se': 108, # 601aSE all edges less than 0.130 micron (8 lambda)
    'm2'  :  40, # 601d 0.01 micron2 (relative to min width 3)
    'm3'  :  40, # 601d 0.01 micron2 (relative to min width 3)        
    'm4'  :  40, # 601d 0.01 micron2 (relative to min width 3)        
    'm5'  :  40, # 601d 0.01 micron2 (relative to min width 3)        
}

# short edges for area
area_se = {
    'm1': 8,
    'm2': 8,
    'm3': 8
}

# Fat wire



# Coloring
