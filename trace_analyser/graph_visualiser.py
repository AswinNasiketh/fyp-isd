import networkx as nx
import matplotlib.pyplot as plt
from trace_analyser.df_graph import *

def convert_dfg_nxg(df_graph):
    nxg = nx.DiGraph()

    # print(df_graph.nodeLst)

    for i, nodeOp in enumerate(df_graph.nodeLst):
        nxg.add_node(i, op = nodeOp)

    for edge in df_graph.adjLst:
        nxg.add_edge(edge.fromNode, edge.toNode)

    return nxg

def draw_nxg(nx_graph, ax):
    # print(nx_graph.graph)
    node_labels = {i:nx_graph.nodes[n]["op"] for i, n in enumerate(nx_graph.nodes)}


    pos = nx.planar_layout(nx_graph)
    nx.draw(nx_graph, pos = pos, ax = ax, node_color="#32CD32")
    nx.draw_networkx_labels(nx_graph, pos, labels = node_labels, ax=ax)

def plot_accs(acc_start_addrs, seq_profiles):
    # print(acc_start_addrs)
    used_accs = [start_addr for start_addr in acc_start_addrs if start_addr != '0']
    fig, axs = plt.subplots(1 ,len(used_accs))

    # fig.suptitle("Accelerator data flow graphs")

    if len(used_accs) > 1:
        for i, start_addr in enumerate(used_accs):
            df_graph = seq_profiles[start_addr].df_graph
            nx_graph = convert_dfg_nxg(df_graph)
            
            draw_nxg(nx_graph, axs[i])
            axs[i].set_title("Accelerator starting address = " + start_addr)
    else:
        df_graph = seq_profiles[used_accs[0]].df_graph
        nx_graph = convert_dfg_nxg(df_graph)
            
        draw_nxg(nx_graph, axs)
        axs.set_title("Accelerator starting address = " + used_accs[0])

    plt.show()
