#*Simulated Annealing Placement Algorithm - with VPR temperature schedule

# Cost Function Terms:
# - Gaps in Layers
# - Unconnected nets in DFG (must be constrained to 0 for exit)
# - Multiple LSUs on a single layer
# - Multiple accelerator outputs on single layer 

# Constrain Grid Size to 5x5



from trace_analyser.logger import print_line
from trace_analyser.latency_mappings import get_ins_func_acc
from trace_analyser.df_graph import DFGraph, DFGraphEdge
import copy
import random
from math import exp
import statistics

random.seed('92125812f4159a7e8712862af1c77ddb60993dd49a448f869cea030809e2bbf1')

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
                rowNum = num_slots_filled//self.m #*integer division
                colNum = num_slots_filled % self.m
                self.slots[rowNum][colNum] = PRUnit(node, i)
                num_slots_filled += 1
        return num_slots_filled

    def visualise(self):
        for row in self.slots:
            for ou in row:
                if ou != None:
                    print(str(ou.nodeID), ":", ou.opcode, end="\t")
                else:
                    print("None", end="\t")
            print()


#*returns number of passthroughs being used
def gapsCost(pg:PRGrid):
    cost = 0
    for  row in pg.slots:
        for ou in row:
            if ou != None:
                if "pt(" in ou.opcode:
                    cost += 1

    return cost

def LSUCongestionCost(pg:PRGrid):
    cost = 0
    for row in pg.slots:
        num_lsus = 0

        for ou in row:
            if ou != None:
                if (not "lit" in ou.opcode) and (not "reg" in ou.opcode) and (not "pt(" in ou.opcode):
                    ou_type = get_ins_func_acc(ou.opcode)
                    if ou_type == "ls":
                        num_lsus += 1
        
        if num_lsus > 1:
            cost += 1

    return cost

def outputCongestionCost(pg:PRGrid, dfg:DFGraph):
    wbNodes = [wb[1] for wb in dfg.final_reg_wbs.items()]

    cost = 0
    for row in pg.slots:
        num_ops = 0

        for ou in row:
            if ou != None:
                if ou.nodeID in wbNodes:
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

def IOCongestionCost(pg:PRGrid, dfg:DFGraph):
    wbNodes = [wb[1] for wb in dfg.final_reg_wbs.items()]

    cost = 0

    for row in pg.slots:
        num_io = 0
        for ou in row:
            if ou != None:
                if (ou.nodeID in wbNodes) or ("reg" in ou.opcode):
                    num_io += 1
        if num_io > 1:
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
    ptOpCode = "pt(" + str(fromNodePos[0]) + "," + str(fromNodePos[1]) + ")"
    while not pathFound:
        row += 1
        #*check if grid size exceeded
        if row >= pg.n:
            break
        
        #*check if next row has toNode => crossbar connection can be made
        if toNodePos[0] == row:
            pathFound = True
            break

        #*check if next row has passthrough for fromNode already
        ptFound = False
        for ou in pg.slots[row]:
            if ou != None:
                if ou.opcode == ptOpCode:
                    ptFound = True
                    break
        
        if ptFound:
            continue
        
        #* check if next row has empty slot for passthrough => path can be made (maybe)
        if (None in pg.slots[row]):
            for col, ou in enumerate(pg.slots[row]):
                if ou == None:
                    #*mark slot as used passthrough so other paths cant use it
                    ptMods.append((row, col, PRUnit(ptOpCode, -1)))
                    break
        else:
            break
    
    #*path has been found => apply passthrough modifications
    if pathFound and (len(ptMods) > 0):
        pgc = copy.deepcopy(pg)
        for r,c,mod in ptMods:
            pgc.slots[r][c] = mod #* copy of pg is being modified
        return pathFound, pgc
    else:
        return pathFound, pg

def unconnectedNetsCost(pg:PRGrid, dfg:DFGraph):
    opNodes = dfg.get_output_nodes()

    intermediateEdges = [edge for edge in dfg.adjLst if not edge.fromNode in opNodes]

    #*filter out edges to regs - these are feedback paths and will be done without direct connections
    #* filter out edges to self - this is a bug

    intermediateEdges = [edge for edge in intermediateEdges if (not "reg" in dfg.nodeLst[edge.toNode])]
    intermediateEdges = [edge for edge in intermediateEdges if edge.fromNode != edge.toNode]

    cost = 0
    unconnectedNets = []
    pgc = copy.deepcopy(pg)
    for edge in intermediateEdges:
        edgeMade = False
        fromNodePos = findNodePos(pgc, edge.fromNode)
        toNodePos = findNodePos(pgc, edge.toNode)

        #*check for right to left datapath
        if fromNodePos[0] == toNodePos[0] and ((fromNodePos[1] + 1) == toNodePos[1]):
            edgeMade = True
        else:
            #*check for datapath between layers
            edgeMade, pgc = findPath(pgc, fromNodePos, toNodePos)

        if not edgeMade:
            cost += 1
            unconnectedNets.append(edge)

    return cost, pgc, unconnectedNets

#* in random switching function allow x and y direction switches for all nodes, except pt nodes, which are deleted
#*nodes for literals will need to be initialised when accelerator is started

def calculateTotalCost(pg, dfg):
    cost = 0

    cost += gapsCost(pg)
    cost += LSUCongestionCost(pg)
    # cost += outputCongestionCost(pg, dfg)
    # cost += inputCongestionCost(pg)
    cost += IOCongestionCost(pg, dfg)
    costUN, _, _ = unconnectedNetsCost(pg, dfg)
    cost += costUN
    return cost

def makeRandomChange(pg, swapDistX, swapDistY):
    x = random.randint(0, pg.n - 1) #*rng is inclusive of both boundaries
    y = random.randint(0, pg.m - 1)

    nextXUB = x + swapDistX #*upper bound on x swap
    nextXLB = x - swapDistX
    nextYUB = y + swapDistY
    nextYLB = y - swapDistY

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
def selectTemp(pg: PRGrid, dfg: DFGraph, n_blocks, swapDistX, swapDistY):
    cost_list = [calculateTotalCost(pg, dfg)]
    for i in range(n_blocks):
        pg = makeRandomChange(pg, swapDistX, swapDistY)
        cost = calculateTotalCost(pg, dfg)
        cost_list.append(cost)
    
    std = statistics.stdev(cost_list)
    # print("std", std)
    return pg, round(20 * std)

def canExitAnneal(temp, pg, dfg):
    TEMP_THRESHOLD = 0.0005
    if temp < TEMP_THRESHOLD:
        return True

    unetCost, _, _ = unconnectedNetsCost(pg, dfg)
    lsuCongCost = LSUCongestionCost(pg)
    # inpCongCost = inputCongestionCost(pg)
    # opCongCost = outputCongestionCost(pg, dfg)
    ioCongCost = IOCongestionCost(pg, dfg)

    return (unetCost == 0) and (lsuCongCost == 0) and (ioCongCost == 0)

#*VPR temperature schedule
def newTempModifier(propAccepted):
    if propAccepted > 0.96:
        return 0.5
    elif (propAccepted > 0.8) and (propAccepted <= 0.96):
        return 0.9
    elif (propAccepted > 0.15) and (propAccepted <= 0.8):
        return 0.95
    else:
        return 0.8

def newSwapDistModifier(propAccepted):
    return 1 - 0.44 + propAccepted

def anneal(pg, dfg, iters_per_temp, initSwapDistX, initSwapDistY, initTemp):
    curr = pg
    currCost = calculateTotalCost(pg, dfg)

    temp = initTemp

    swapDistX = initSwapDistX
    swapDistY = initSwapDistY

    while not canExitAnneal(temp, curr, dfg):
        nAccepted = 0
        for i in range(iters_per_temp):
            pgCopy = copy.deepcopy(curr)
            pgCopy = makeRandomChange(pgCopy, swapDistX, swapDistY)
            newCost = calculateTotalCost(pgCopy, dfg)

            diff = newCost - currCost

            acceptanceProb = exp(-diff/temp)
            if diff < 0 or random.random() < acceptanceProb:
                curr = pgCopy
                currCost = newCost
                nAccepted += 1
        
        propAccepted = nAccepted/float(iters_per_temp)
        temp = newTempModifier(propAccepted) * temp
        swapDistMod = newSwapDistModifier(propAccepted)
        swapDistX = round(swapDistX * swapDistMod)
        swapDistY = round(swapDistY * swapDistMod)

    return curr, currCost

def genPRGrid(dfg, numRows, numColumns):
    pg = PRGrid(numRows, numColumns)

    n_blocks = pg.scatterDFG(dfg)
    pg, initTemp = selectTemp(pg, dfg, n_blocks, numRows, numColumns)
    iters_per_temp = round(10 * (n_blocks**1.33))
    pg, _ = anneal(pg, dfg, iters_per_temp, numRows, numColumns, initTemp)

    unCost, newPG, UNs = unconnectedNetsCost(pg, dfg)
    lsuCost = LSUCongestionCost(newPG)
    IOCost = IOCongestionCost(newPG, dfg)
    # print("Unconnected Nets", unCost)
    # print("LSU Congestion Cost", LSUCongestionCost(newPG))
    # print("IO Congestion Cost", IOCongestionCost(newPG, dfg))

    # print("Unconnected nets")
    # for edge in UNs:
    #     print("edge from", edge.fromNode, "to", edge.toNode)
    return newPG, unCost, lsuCost, IOCost


def estimateGridSize(dfg: DFGraph):
    #*min number of rows decided by max of number of inputs + number of writebacks, and number of LSUs
    #*number of columns decided by avg output multiplicity * number of nodes with branching outputs

    num_inputs = len([1 for node in dfg.nodeLst if "reg" in node])
    num_wbs = len([1 for wb in dfg.final_reg_wbs.items()])
    num_lsus = 0

    for node in dfg.nodeLst:
        if (not "reg" in node) and (not "lit" in node) and (not "out" in node):
            ou_type = get_ins_func_acc(node)
            if ou_type == "ls":
                num_lsus += 1 

    numRows = max(num_inputs + num_wbs, num_lsus)

    # numSlotsRequired = len([1 for node in dfg.nodeLst if not "out" in node])
    # minCols = ceil(numSlotsRequired/numRows)

    # nodeOPMults = get_output_multiplicites(dfg)
    # branchingOPNodes = len([1 for mult in nodeOPMults if mult > 1])

    # avgOPMult = statistics.mean(nodeOPMults)
    # numCols = minCols + round(branchingOPNodes*avgOPMult)

    return numRows


def trimGrid(pg: PRGrid):
    #* remove rows full of Nones (on top and bottom)

    trimmedGrid = []
    for row in pg.slots:
        rowUsed = False
        for ou in row:
            if ou != None:
                rowUsed = True
                break
        
        if rowUsed:
            trimmedGrid.append(row)

    pg.slots = trimmedGrid
    pg.n = len(trimmedGrid)

    return pg

def tryConnectNet(pg: PRGrid, dfg: DFGraph, unconnectedNet: DFGraphEdge):
    #*try move toNode beneath fromNode of unconnectedNet, creating passthroughs for the other input of toNode
    pass