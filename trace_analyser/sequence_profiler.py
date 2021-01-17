from trace_analyser.df_graph import *
from trace_analyser.latency_mappings import *
from trace_analyser.logger import *
from trace_analyser.graph_visualiser import plot_dfg

class SequenceProfileEntry:
    def __init__(self, cpu_time, acc_time, area_cost, reconf_time, df_graph, initiation_interval):
        self.cpu_time = cpu_time
        self.acc_time = acc_time
        self.area_cost = area_cost
        self.reconf_time = reconf_time
        self.df_graph = df_graph
        self.initiation_interval =  initiation_interval

def find_node_depth(node, graph, cpu = False):
    if "lit" in graph.nodeLst[node] or "reg" in graph.nodeLst[node]:
        return 0
    
    inputNodes = [edge.fromNode for edge in graph.adjLst if edge.toNode == node]
    inputNodeDepths = []
    for inpNode in inputNodes:
        inputNodeDepths.append(find_node_depth(inpNode, graph, cpu))
    
    # print_line(inputNodeDepths)
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

    # print("Feedback depths length", len(feedback_depths))

    if len(feedback_depths) > 0:
        return  get_ins_lat_acc(graph.nodeLst[currNode]) + max(feedback_depths)
    else:
        return -1 #propagate traversal failed to find node

    # for node in inputNodes:
    #     depth_result = get_feedback_depth(destNode, node, graph)
    #     if depth_result == -1:
    #         return -1 
    #     else:
    #         return get_ins_lat_acc(graph.nodeLst[currNode]) + depth_result

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

    area_cost = len(df_graph.nodeLst) #assume 1 unit area per FU required and 1 FU per instruction

    reconf_time = len(df_graph.nodeLst) * FRAMES_PER_FU * RECONF_TIME_PER_FRAME * CPU_CLK_FREQ #in cycles

    feedback_paths = df_graph.get_feedback_paths()
    # for path in feedback_paths:
    #     print("Feedback Path from", path.fromNode, "To", path.toNode)
    feedback_depths = list(map(lambda e: get_feedback_depth(e.toNode, e.fromNode, df_graph), feedback_paths))
    max_init_interval = max(feedback_depths)

    # print_line("Initiation interval", max_init_interval)
    # if max_init_interval == 0:
    #     plot_dfg(df_graph)

    # print("Acc Depth", maxDepthAcc)
    # print("CPU Depth", maxDepthCpu)

    return SequenceProfileEntry(maxDepthCpu, maxDepthAcc, area_cost, reconf_time, df_graph, max_init_interval)