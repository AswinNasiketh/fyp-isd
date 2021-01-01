from trace_analyser.df_graph import *
from trace_analyser.latency_mappings import *



class SequenceProfileEntry:
    def __init__(self, cpu_time, acc_time, area_cost, reconf_time):
        self.cpu_time = cpu_time
        self.acc_time = acc_time
        self.area_cost = area_cost
        self.reconf_time = reconf_time

def find_node_depth(node, graph, cpu = False):
    if "inp" in graph.nodeLst[node]:
        return 0
    
    inputNodes = [edge.fromNode for edge in graph.adjLst if edge.toNode == node]
    inputNodeDepths = []
    for inpNode in inputNodes:
        inputNodeDepths.append(find_node_depth(inpNode, graph, cpu))
    
    # print(inputNodeDepths)

    if cpu:
        return get_ins_lat_cpu(graph.nodeLst[node]) + max(inputNodeDepths)
    else:
        return get_ins_lat_acc(graph.nodeLst[node]) + max(inputNodeDepths)



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

    return SequenceProfileEntry(maxDepthCpu, maxDepthAcc, area_cost, reconf_time)