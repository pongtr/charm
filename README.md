# CHARM 2.0

### Inputs
- `layout.pl`: placed layout
- `layout.nets`
- `layout.nodes`
- For each cell type `cell` in `layout.nodes`:
	geometry of cell in `cell.mag`
- Mode: `-s`ingle or `-p`laced

### Flow
1. Load inputs
2. Route using the route ordering technique
3. Output the TCL that draws the routes

## DATA STRUCTURES

### Grids
- Global grid: `(x,y) -> cell`
	3D grid with pointers to each cell that occupies the grid
- Cell grid: `(x,y,m) -> rect`
	Within each cell, 3D grid with pointers to each rect that occupies the grid

### Rect
* `x`,`y` location
* width `w` and height `h`
* material `m`
* net `n`
* cell parent `cp`

### Cell
- `x`,`y` location
- width `w` and height `h`
- `cell_type`
- `geometry` (rectangles in cell)
- `grid`

### Component
- `net`
- `segments`
- `pins`
- `dependencies`

### Waypoint
- `x`,`y`
- material `m`
- width `w`

A **segment** is a pair of waypoints. Width and material of a segment is the width and material of the first waypoint.
A **route** is a list of many waypoints.

## ROUTE ORDERING

### LAFRIEDA ORDERING
Use "heuristic 3"

### SEGMENT-RRR
When no routes are available, then rip up a segment from existing component.
Lay down new route, then reroute the split components.
Undo if new route increases cost over a certain threshold.

## ROUTING TECHNIQUES
**Inputs**
- Source component
- Destination component

**Environment**
- Existing Layout
- Laid Routes

**Output**
- Valid route (as waypoints) or False

### PATTERN ROUTER

Generate routes between source and destination with increasing cost
Check if routes adhere to all the rules and are drawable

**Possible shapes:**
- Components already touching
- I: straight
- L: one bend
- Z/S: two bends inside MBB (Manhattan Bounding Box)
- U: detour outside MBB

**Design Rule Checks**
- Spacing: compare to nets passed
- Width: always generate with correct width
- Jog length: check segment length
	- Check as routes are generated†
- Min area: check connections
- End of line: increased spacing

### LEE MAZE ROUTER

Propagate wave from both source component and destination component
End when either wavefronts touch or a wavefront touches same net

**Constraints**
- Direction change after min jog
- Layer change after min area

## ADDITIONAL FUNCTIONS

### ELEVATOR
Apply to source/dest to quickly move up from low metal layer to higher metal layer while adhering to design rules.