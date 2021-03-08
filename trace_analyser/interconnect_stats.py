#number of branches an output goes to
#number of outputs per graph with multiple branches
#number of input registers
#number of output registers
#graph width
#graph depth 
#store load operations

from trace_analyser.sequence_profiler import find_node_depth
from trace_analyser.latency_mappings import get_ins_func_acc
# import matplotlib.pyplot as plt

def get_output_multiplicites(dfg):
    output_mutiplicites = []
    for node in range(len(dfg.nodeLst)):
        nodeOutputs = [edge for edge in dfg.adjLst if edge.fromNode == node]
        output_mutiplicites.append(len(nodeOutputs))
    
    return output_mutiplicites


def get_input_count(dfg):
    input_count = 0
    for node in dfg.nodeLst:
        if ("reg" in node):
            input_count += 1
    return input_count

def get_num_lsu_ops(dfg):
    lsu_op_count = 0
    for node in dfg.nodeLst:
        if (not "reg" in node) and (not "lit" in node) and (not "out" in node):
            if get_ins_func_acc(node) == "ls":
                lsu_op_count += 1

    return lsu_op_count

def extract_stats(sequence_profiles):
    graphs = [profile.df_graph for profile in sequence_profiles.values()]

    output_mutiplicites_lst = []
    multi_branch_outputs_lst = []
    input_count_lst = []
    width_lst = []
    depth_lst = []
    lsu_ops_lst = []
    size_lst = []
    fb_path_num_lst = []

    for graph in graphs:
        output_multiplicites = get_output_multiplicites(graph)
        multi_branch_outputs = 0
        input_count = get_input_count(graph)

        for multiplicity in output_multiplicites:
            if multiplicity > 1:
                multi_branch_outputs += 1

        output_nodes = graph.get_output_nodes()
        maxDepth = 0
        for node in output_nodes:
            depth = find_node_depth(node, graph, no_weightings=True)
            if depth > maxDepth:
                maxDepth = depth
        
        
        # simple view of width - assumes parallelisim can only be achieved due to one intermediate result being ready, or at the start of the accelerator. In reality, maximum width can be at any point where multiple inputs to OUs are ready at the same time.
        width = max(output_multiplicites, default = 1)
        width = max(width, input_count)

        lsu_ops = get_num_lsu_ops(graph)

        num_feedback_paths = len(graph.get_feedback_paths())

        output_mutiplicites_lst = output_mutiplicites_lst + output_multiplicites
        multi_branch_outputs_lst.append(multi_branch_outputs)
        input_count_lst.append(input_count)
        width_lst.append(width)
        depth_lst.append(maxDepth)
        size_lst.append(len(graph.nodeLst))
        lsu_ops_lst.append(lsu_ops)
        fb_path_num_lst.append(num_feedback_paths)

    return output_mutiplicites_lst, multi_branch_outputs_lst, input_count_lst, width_lst, depth_lst, size_lst, lsu_ops_lst, fb_path_num_lst

# def display_histograms(output_mutiplicites_lst, multi_branch_outputs_lst, input_count_lst, width_lst, depth_lst, size_lst, lsu_ops_lst, fb_path_num_lst):

#     fig, axs = plt.subplots(4,2)
#     # print(output_mutiplicites_lst)

#     n, bins, patches = axs[0, 0].hist(x=output_mutiplicites_lst, bins=range(20))
#     axs[0, 0].set_title('Node output edge multiplicites')
#     axs[0, 0].set(ylabel='frequency')
#     axs[0, 0].set_xticks(bins)


#     n, bins, patches = axs[0, 1].hist(x=multi_branch_outputs_lst, bins=range(20))
#     axs[0, 1].set_title('Number of multi branch ouputs in a graph')
#     axs[0, 1].set(ylabel='frequency')
#     axs[0, 1].set_xticks(bins)

#     n, bins, patches = axs[1, 0].hist(x=input_count_lst, bins=range(20))
#     axs[1, 0].set_title('Number of Inputs in a graph')
#     axs[1, 0].set(ylabel='frequency')
#     axs[1, 0].set_xticks(bins)

#     n, bins, patches = axs[1, 1].hist(x=width_lst, bins=range(20))
#     axs[1, 1].set_title('Approximate max parallel operations in graph')
#     axs[1, 1].set(ylabel='frequency')
#     axs[1, 1].set_xticks(bins)

#     n, bins, patches = axs[2, 0].hist(x=depth_lst, bins=range(20))
#     axs[2, 0].set_title('Max graph depth')
#     axs[2, 0].set(ylabel='frequency')
#     axs[2, 0].set_xticks(bins)

#     n, bins, patches = axs[2, 1].hist(x=size_lst, bins=range(20))
#     axs[2, 1].set_title('Number of nodes in graph')
#     axs[2, 1].set(ylabel='frequency')
#     axs[2, 1].set_xticks(bins)

#     n, bins, patches = axs[3, 0].hist(x=lsu_ops_lst, bins=range(20))
#     axs[3, 0].set_title('Number of load/store operations in a graph')
#     axs[3, 0].set(ylabel='frequency')
#     axs[3, 0].set_xticks(bins)

#     n, bins, patches = axs[3, 1].hist(x=fb_path_num_lst, bins=range(20))
#     axs[3, 1].set_title('Number of feedback paths in a graph')
#     axs[3, 1].set(ylabel='frequency')
#     axs[3, 1].set_xticks(bins)

#     fig.tight_layout()

#     plt.show()