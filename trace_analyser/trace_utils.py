def get_instr_addr(trace_line):
    return str(int(trace_line.split()[0].split('=')[1], 16)) #*string of decimal integer representation of address


def get_base_instr(instr):
    instr_parts = instr.split(".")
    if len(instr_parts) > 1:
        instr = instr_parts[0] + '.' + instr_parts[1] #only take opcode up to first .
    
    return instr


#class to orgainise trace lines into assembly opcodes and operands
#branch profiler does not use this because it uses metadata generated by the simulator in the trace files
class TraceLine:
    
    def __init__(self, trace_line):
        self.fields = trace_line.split()
        
        self.instr_addr = fields[0].split('=')[1]
        self.opcode = fields[1]
        self.operands = fields[2].split(',')



        