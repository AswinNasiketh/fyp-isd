#*Simulated Annealing Placement Algorithm - with VPR temperature schedule

# Cost Function Terms:
# - Gaps in Layers
# - Unconnected nets in DFG (must be constrained to 0 for exit)
# - Multiple LSUs on a single layer
# - Multiple accelerator outputs on single layer 

# Constrain Grid Size to 5x5



from trace_analyser.latency_mappings import get_ins_func_acc
from trace_analyser.df_graph import DFGraph
import copy


class PRUnit:
    def __init__(self, opcode, nodeID):
        self.opcode = opcode
        self.nodeID = nodeID
        self.inps = []

class PRGrid:
    def __init__(self, n, m):
        self.n = n
        self.m = m
        innerArray = [None] * m #m columns
        self.slots = innerArray * n #n rows


    def scatterDFG(self, dfg: DFGraph):
        num_slots_filled = 0
        for i, node in enumerate(dfg.nodeLst):
            if (not "out" in node):
                rowNum = num_slots_filled//self.n #*integer division
                colNum = num_slots_filled % self.m
                self.slots[rowNum][colNum] = PRUnit(node, i)
                num_slots_filled += 1


#*returns number of unused slots and passthroughs in PRGrid. 
def gapsCost(pg:PRGrid):
    flatennedGrid = [slotItem for row in pg.slots for slotItem in row]
    cost = 0
    for ou in flatennedGrid:
        if ou == None:
            cost += 1
        elif "pt(" in ou.opcode:
            cost += 1
    
    return cost

def LSUCongestionCost(pg:PRGrid):
    cost = 0
    for row in pg.slots:
        num_lsus = 0

        for ou in row:
            if ou != None:
                if (not "lit" in ou.opcode) and (not "reg" in ou.opcode):
                    ou_type = get_ins_func_acc(ou.opcode)
                    if ou_type == "ls":
                        num_lsus += 1
        
        if num_lsus > 1:
            cost += 1

    return cost

def outputCongestionCost(pg:PRGrid, dfg:DFGraph):
    opNodes = dfg.get_output_nodes()

    cost = 0
    for row in pg.slots:
        num_ops = 0

        for ou in row:
            if ou != None:
                if ou.nodeID in opNodes:
                    num_ops += 1
        
        if num_ops > 1:
            cost += 1
    
    return cost

def inputCongestionCost(pg:PRGrid):
    cost = 0
    for row in pg.slots:
        num_inps = 0

        for ou in row:
            if ou != None:
                if "reg" in ou.opcode:
                    num_inps += 1

        if num_inps > 1:
            cost += 1

    return cost

def findNodePos(pg:PRGrid, nodeID):
    for rowNum, row in enumerate(pg.slots):
        for colNum, ou in enumerate(row):
            if ou.nodeID == nodeID:
                return (rowNum, colNum)

def findPath(pg:PRGrid, fromNodePos, toNodePos):
    pathFound = False

    row, _ = fromNodePos
    ptMods = []
    while not pathFound:
        row += 1
        #*check if grid size exceeded
        if row >= pg.n:
            break
        
        #*check if next row has toNode => crossbar connection can be made
        if toNodePos[0] == row:
            pathFound = True
            break
        
        #* check if next row has empty slot for passthrough => path can be made (maybe)
        if (None in pg.slots[row]):
            for col, ou in enumerate(pg.slots[row]):
                if ou == None:
                    #*mark slot as used passthrough so other paths cant use it
                    ptMods.append((row, col, PRUnit("pt(" + fromNodePos[0] + "," + fromNodePos[1] + ")", -1)))
                    break
        else:
            break
    
    #*path has been found => apply passthrough modifications
    if pathFound and (len(ptMods) > 0):
        pg = copy.deepcopy(pg)
        for r,c,mod in ptMods:
            pg.slots[r][c] = mod #* copy of pg is being modified
    
    return pathFound, pg

def unconnectedNetsCost(pg:PRGrid, dfg:DFGraph):
    opNodes = dfg.get_output_nodes()

    intermediateEdges = [edge for edge in dfg.adjLst if not edge.fromNode in opNodes]

    cost = 0

    for edge in intermediateEdges:
        edgeMade = False
        fromNodePos = findNodePos(pg, edge.fromNode)
        toNodePos = findNodePos(pg, edge.toNode)

        #*check for right to left datapath
        if fromNodePos[0] == toNodePos[0] and ((fromNodePos[1] + 1) == toNodePos[1]):
            edgeMade = True
        else:
            #*check for datapath between layers
            edgeMade, pg = findPath(pg, fromNodePos, toNodePos)

        if not edgeMade:
            cost += 1

#* in random switching function allow x and y direction switches for all nodes, except pt nodes, which are deleted
#*nodes for literals will need to be initialised when accelerator is started
#*find intermediate outputs
