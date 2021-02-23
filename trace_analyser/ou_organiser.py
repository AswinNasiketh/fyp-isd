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
import random
from math import exp
import statistics


class PRUnit:
    def __init__(self, opcode, nodeID):
        self.opcode = opcode
        self.nodeID = nodeID
        self.inps = []

class PRGrid:
    def __init__(self, n, m):
        self.n = n
        self.m = m
        self.slots = []
        for i in range(n):
            innerArray = [None] * m #m columns
            self.slots.append(innerArray) #n rows


    def scatterDFG(self, dfg: DFGraph):
        num_slots_filled = 0
        for i, node in enumerate(dfg.nodeLst):
            if (not "out" in node):
                rowNum = num_slots_filled//self.n #*integer division
                colNum = num_slots_filled % self.m
                self.slots[rowNum][colNum] = PRUnit(node, i)
                num_slots_filled += 1


#*returns diffence between size of prgrid based on boundaries and number of slots needed by dfg
def gapsCost(pg:PRGrid, dfg:DFGraph):
    rightmost_used_col = 1
    highest_used_row = 1
    for rowNum, row in enumerate(pg.slots):
        for colNum, ou in enumerate(row):
            if ou != None:
                highest_used_row = rowNum + 1

                if (colNum + 1) > rightmost_used_col:
                    rightmost_used_col = colNum + 1

    slotsUsed = rightmost_used_col * highest_used_row
    nOPRegs = len([node for node in dfg.nodeLst if (not "out" in node)])
    minSlotsNeeded = len(dfg.nodeLst) - nOPRegs
    return slotsUsed - minSlotsNeeded

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
    opNodes = [wb[1] for wb in dfg.final_reg_wbs.items()]

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
            if ou != None:
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
                    ptMods.append((row, col, PRUnit("pt(" + str(fromNodePos[0]) + "," + str(fromNodePos[1]) + ")", -1)))
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

    return cost

#* in random switching function allow x and y direction switches for all nodes, except pt nodes, which are deleted
#*nodes for literals will need to be initialised when accelerator is started

def calculateTotalCost(pg, dfg):
    cost = 0

    cost += gapsCost(pg, dfg)
    cost += LSUCongestionCost(pg)
    cost += outputCongestionCost(pg, dfg)
    cost += inputCongestionCost(pg)
    cost += unconnectedNetsCost(pg, dfg)
    return cost

def makeRandomChange(pg, maxStepX, maxStepY):
    x = random.randint(0, pg.n - 1) #*rng is inclusive of both boundaries
    y = random.randint(0, pg.m - 1)

    nextXUB = x + maxStepX #*upper bound on x step
    nextXLB = x - maxStepX
    nextYUB = y + maxStepY
    nextYLB = y - maxStepY

    if nextXLB < 0:
        nextXLB = 0
    if nextXUB >= pg.n:
        nextXUB = pg.n - 1
    
    if nextYLB < 0:
        nextYLB = 0
    if nextYUB >= pg.m:
        nextYUB = pg.m - 1

    nextX = random.randint(nextXLB, nextXLB)
    nextY = random.randint(nextYLB, nextYUB)


    unitToSwap = pg.slots[x][y]
    unitSwapped = pg.slots[nextX][nextY] 

    if unitToSwap != None:
        if "pt(" in unitToSwap.opcode:
            unitToSwap = None

    if unitSwapped != None:
        if "pt(" in unitSwapped.opcode:
            unitSwapped = None
        
    pg.slots[x][y] = unitSwapped
    pg.slots[nextX][nextY] = unitToSwap

    return pg


#*VPR based initial temperature selection
def selectTemp(pg: PRGrid, dfg: DFGraph, maxStepX, maxStepY):
    n_blocks = len([node for node in dfg.nodeLst if (not "out" in node)])
    cost_list = [calculateTotalCost(pg, dfg)]
    for i in range(n_blocks):
        pg = makeRandomChange(pg, maxStepX, maxStepY)
        cost = calculateTotalCost(pg, dfg)
        cost_list.append(cost)
    
    std = statistics.stdev(cost_list)
    print("std", std)
    return pg, round(20 * std)


def anneal(pg, dfg, n_iterations, maxStepX, maxStepY, initTemp):
    curr = pg
    currCost = calculateTotalCost(pg, dfg)

    for i in range(n_iterations):
        pgCopy = copy.deepcopy(curr)
        pgCopy = makeRandomChange(pgCopy, maxStepX, maxStepY)
        newCost = calculateTotalCost(pgCopy, dfg)

        diff = newCost - currCost
        t = initTemp/float(i+1)

        acceptanceProb = exp(-diff/t)
        if diff < 0 or random.random() < acceptanceProb:
            curr = pgCopy
            currCost = newCost
    
    return curr, currCost

def genPRGrid(dfg, numRows, numColumns):
    pg = PRGrid(numRows, numColumns)

    pg.scatterDFG(dfg)
    pg, initTemp = selectTemp(pg, dfg, 2, 2)
    

    pg, _ = anneal(pg, dfg, initTemp * 100, 2, 2, initTemp)

    print("Unconnected Nets", unconnectedNetsCost(pg, dfg))
    print("LSU Congestion Cost", LSUCongestionCost(pg))
    print("Output Congestion Cost", outputCongestionCost(pg, dfg))
    print("Input Congestion Cost", inputCongestionCost(pg))

    return pg