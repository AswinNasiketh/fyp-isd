from trace_analyser.ou_organiser import estimateGridSize, genPRGrid, trimGrid
from trace_analyser.df_graph import *
from trace_analyser.latency_mappings import *
from trace_analyser.logger import *
from trace_analyser.rci_params import rf_num_cols, rf_num_rows

class SequenceProfileEntry:
    def __init__(self, cpu_time, acc_time, reconf_time, df_graph, initiation_interval):
        self.cpu_time = cpu_time
        self.acc_time = acc_time
        
        self.reconf_time = reconf_time
        self.df_graph = df_graph
        self.initiation_interval =  initiation_interval

        self.num_rows = None
        self.pg = None
        self.num_annealing_attempts = 0

        self.MAX_ANNEALING_ATTEMPTS = 5
    
    def area_cost(self):
        if self.num_rows != None:
            return self.num_rows
        else:
            if self.num_annealing_attempts > self.MAX_ANNEALING_ATTEMPTS:
                return -1
            else:
                nRows = estimateGridSize(self.df_graph)
                if nRows > rf_num_rows: #if number of rows needed exceeds number of available rows, can't place accelerator
                    self.num_annealing_attempts = self.MAX_ANNEALING_ATTEMPTS + 1
                    return -1

                newPG, unCost, lsuCost, IOCost = genPRGrid(self.df_graph, nRows, rf_num_cols)

                if unCost > 0 or lsuCost > 0 or IOCost > 0:
                    self.num_annealing_attempts += 1
                    return -1
                else:
                    self.pg = trimGrid(newPG)
                    self.num_rows = self.pg.n
                    return self.num_rows

    def print_profile(self):
        print_line("CPU Time:", self.cpu_time)
        print_line("Acc Time:", self.acc_time)

        print_line("Reconf Time:", self.reconf_time)
        print_line("Initiation Interval:", self.initiation_interval)
        print_line("Num Rows PRGrid:", self.num_rows)
        print_line("Num Annealing Attemps", self.num_annealing_attempts)


def find_node_depth(node, graph, cpu = False, no_weightings = False):
    if "lit" in graph.nodeLst[node] or "reg" in graph.nodeLst[node]:
        return 0
    
    inputNodes = [edge.fromNode for edge in graph.adjLst if edge.toNode == node]
    inputNodeDepths = []
    for inpNode in inputNodes:
        inputNodeDepths.append(find_node_depth(inpNode, graph, cpu))
    
    if no_weightings:
        return 1 + max(inputNodeDepths)
    else:
        if cpu:
            return get_ins_lat_cpu(graph.nodeLst[node]) + max(inputNodeDepths)
        else:
            return get_ins_lat_acc(graph.nodeLst[node]) + max(inputNodeDepths)

def get_feedback_depth(destNode, currNode, graph):
    if currNode == destNode:
        return 0
    elif "reg" in graph.nodeLst[currNode] or "lit" in graph.nodeLst[currNode]: 
        return -1 #-1 to signal traversal did not find node

    inputNodes = [edge.fromNode for edge in graph.adjLst if edge.toNode == currNode]

    feedback_depths = list(map(lambda n: get_feedback_depth(destNode, n, graph), inputNodes))
    feedback_depths = [d for d in feedback_depths if d != -1]

    if len(feedback_depths) > 0:
        return  get_ins_lat_acc(graph.nodeLst[currNode]) + max(feedback_depths)
    else:
        return -1 #propagate traversal failed to find node

def profile_seq(inst_mem, start_addr, end_addr):

    df_graph = createDFGraph(inst_mem, start_addr, end_addr)
    outputNodes = df_graph.get_output_nodes()

    maxDepthAcc = 0
    for node in outputNodes:
        depth = find_node_depth(node, df_graph, False)
        if depth > maxDepthAcc:
            maxDepthAcc = depth

    maxDepthAcc += fetch_latency + decode_issue_latency # one fetch and decode for each custom instr    

    maxDepthCpu = 0
    for node in outputNodes:
        depth = find_node_depth(node, df_graph, True)
        if depth > maxDepthCpu:
            maxDepthCpu = depth
    #fetch and decode latencies already included in mappings for CPU

    # area_cost = len(df_graph.nodeLst) #assume 1 unit area per FU required and 1 FU per instruction

    reconf_time = len(df_graph.nodeLst) * FRAMES_PER_FU * RECONF_TIME_PER_FRAME * CPU_CLK_FREQ #in cycles

    feedback_paths = df_graph.get_feedback_paths()

    feedback_depths = list(map(lambda e: get_feedback_depth(e.toNode, e.fromNode, df_graph), feedback_paths))
    max_init_interval = max(feedback_depths, default= 1)


    return SequenceProfileEntry(maxDepthCpu, maxDepthAcc, reconf_time, df_graph, max_init_interval)