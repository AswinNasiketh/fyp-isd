from df_graph import *
from latency_mappings import *

class SequenceProfileEntry:
    def __init__(self, cpu_time, acc_time):
        self.cpu_time = cpu_time
        self.acc_time = acc_time

def find_node_depth(node, graph, cpu = False):
    if "inp" in graph.nodeLst[node]:
        return 0
    
    inputNodes = [edge.toNode for edge in graph.adjLst if edge.toNode == node]
    inputNodeDepths = []
    for inpNode in inputNodes:
        inputNodeDepths = find_node_depth(inpNode, graph, cpu)

    if cpu:
        func2latcpu[ins2funccpu[graph.nodeLst[node]]] + max(inputNodeDepths)
    else:
        func2latacc[ins2funcacc[graph.nodeLst[node]]] + max(inputNodeDepths)



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
    return SequenceProfileEntry(maxDepthCpu, maxDepthAcc)
    