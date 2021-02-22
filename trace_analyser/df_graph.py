from trace_analyser.trace_utils import TraceLine
from trace_analyser.logger import *
from trace_analyser.instruction_profiles import get_instr_prof
#data container class
class DFGraphEdge:
    
    def __init__(self, fromNode, toNode, reg):
        self.fromNode = fromNode
        self.toNode = toNode
        self.reg = reg


class DFGraph:

    def __init__(self):
        self.adjLst = []
        self.nodeLst = []

    def addNode(self, op):
        self.nodeLst.append(op)
        return len(self.nodeLst) - 1

    def addEgde(self, edge):
        self.adjLst.append(edge)
    
    def print_nodes(self):
        for i, op in enumerate(self.nodeLst):
            print_line("nodeID:", i, ", op:", op)

    def print_edges(self):
        for edge in self.adjLst:
            print_line("Edge from:", edge.fromNode, "Edge To:", edge.toNode)
    
    def get_output_nodes(self):
        intermediate_nodes = []
        for edge in self.adjLst:
            intermidiate_node_criteria = not (edge.fromNode in intermediate_nodes) and not ("reg" in self.nodeLst[edge.toNode]) and not ("out" in self.nodeLst[edge.toNode])
            #if the nodes output is not a feedback or output register then it is an intermediate node
            #first condition to ensure uniqueness
            if intermidiate_node_criteria: 
                intermediate_nodes.append(edge.fromNode)

        allNodes = [i for i in range(len(self.nodeLst))]
        outputNodes = [i for i in allNodes if not i in intermediate_nodes and not "out" in self.nodeLst[i]]
        return outputNodes

    def get_feedback_paths(self):
        feedback_paths = []

        for edge in self.adjLst:
            if "reg" in self.nodeLst[edge.toNode]:
                feedback_paths.append(edge)
        
        return feedback_paths

# fai_instructions = ["sw", "sh", "sd", "sb", "c.j", "c.jr", "beq", "bne", "blt", "bltu", "bge", "bgeu"] #first argument as input instructions

def get_reg_name(reg_expr):
    op_exprs = reg_expr.replace("(", " ").replace(")", " ").split(" ") #replace all brackets with spaces, then split by spaces

    while op_exprs[-1] == '':
        op_exprs.pop()

    return op_exprs[-1]

def createDFGraph(inst_mem, seq_start_addr, seq_stop_addr):
    seq_start_addr = int(seq_start_addr, base=16)
    seq_stop_addr = int(seq_stop_addr, base=16)

    reg_file = {}

    df_graph = DFGraph()

    inst_mem_sorted = list(inst_mem.items())
    inst_mem_sorted.sort(key = lambda x: int(x[0]))
    # print(inst_mem_sorted)
    inst_mem_sorted = [instr[1] for instr in inst_mem_sorted if int(instr[0]) >= seq_start_addr and int(instr[0]) < seq_stop_addr]

    node2instr = {} #for finding non feedback output node registers
    for instrNum, instr in enumerate(inst_mem_sorted):
        
        nodeID = df_graph.addNode(instr.opcode)
        node2instr[str(nodeID)] = instrNum

        start_index = 1

        if get_instr_prof(instr.opcode).fai or get_instr_prof(instr.opcode).das:
            start_index = 0
        

        for i in range(start_index, len(instr.operands)):
            fromNodeID = -1
            for key in reg_file.keys():
                if key in instr.operands[i]:
                    fromNodeID = reg_file[key]
                    df_graph.addEgde(DFGraphEdge(fromNodeID, nodeID, key))
                    break

            if fromNodeID == -1:
                if instr.operands[i].isdecimal() or "0x" in instr.operands[i] or "-" in instr.operands[i]:
                    inpNode = df_graph.addNode("lit(" + instr.operands[i] + ")")
                    df_graph.addEgde(DFGraphEdge(inpNode, nodeID, 'lit'))
                else:
                    regName = get_reg_name(instr.operands[i])
                    inpNode = df_graph.addNode("reg(" + regName + ")")
                    reg_file[regName] = inpNode
                    df_graph.addEgde(DFGraphEdge(inpNode, nodeID, regName))


        if start_index == 1 or get_instr_prof(instr.opcode).das:
            reg_file[get_reg_name(instr.operands[0])] = nodeID

    #find feedback paths
    for nodeID, node in enumerate(df_graph.nodeLst):
        if not "reg" in node:
            continue

        reg = get_reg_name(node)
        # print("Inp reg", reg)
        if reg in reg_file.keys():
            df_graph.addEgde(DFGraphEdge(reg_file[reg], nodeID, reg))
    
    #add registers for output nodes
    opNodes = df_graph.get_output_nodes()
    for node in opNodes:
        feedback_node = False
        for edge in df_graph.adjLst:
            if edge.fromNode == node: #will only be true if output node has a feedback connection to a reg
                feedback_node = True
                break
        if feedback_node:
            continue
        else:
            opcode = df_graph.nodeLst[node]
            instr_prof = get_instr_prof(opcode)
            if not instr_prof.fai: 
                #instruction has writeback 
                instrNum = node2instr[str(node)]
                instr = inst_mem_sorted[instrNum]
                opRegName = get_reg_name(instr.operands[0])
                opNodeID = df_graph.addNode("out(" + opRegName + ")")
                df_graph.addEgde(DFGraphEdge(node, opNodeID, opRegName))

    return df_graph

# test_mem = {
#     '0' : TraceLine("pc=20000725e0 auipc a5,774144"),
#     '4' : TraceLine("pc=20000725e4 addi a5,a5,-1816"),
#     '8' : TraceLine("pc=20000725e8 auipc s4,774144"),
#     'c' : TraceLine("pc=20000725ec addi s0,s4,1200"),
#     '10' : TraceLine("pc=20000725f0 sub s4,s4,a5"),
#     '18' : TraceLine("pc=20000725f4 sub a5,s11,a5"),
#     '14' : TraceLine("pc=20000727d2 sd a5,-1176(s0)")
    
# }

# pc=20000725e0 auipc a5,774144
# pc=20000725e4 addi a5,a5,-1816
# pc=20000725e8 auipc s4,774144
# pc=20000725ec addi s4,s4,1200
# pc=20000725f0 sub s4,s4,a5
# pc=20000725f4 sub a5,s11,a5

# test_bprof = BranchProfileEntry('1c', '0')

# df_graph = createDFGraph(test_mem, test_bprof)

# df_graph.print_nodes()
# df_graph.print_edges()