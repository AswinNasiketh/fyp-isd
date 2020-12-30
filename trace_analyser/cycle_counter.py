from trace_analyser.latency_mappings import *
from trace_analyser.trace_utils import get_instr_addr

#This class will measure the improvement in cycle count
class CycleCounter:

    def __init__(self):
        self.non_accelerated_cycles = 0
        self.accelerated_cycles = 0


        # self.accelerator_used = [False for i in range(num_accelerators)]

#assumes in order operation for non accelerated sections
    def count_line(self, trace_line, accelerated_seqs, inst_mem, seq_profiles):
        count_in_accelerated = True
        pc_addr = int(trace_line.split()[0].split("=")[-1] , base=16)
        instr = inst_mem[get_instr_addr(trace_line)].opcode

        
        for seq in accelerated_seqs:            
            range_start = int(seq.branch_target_addr, base=16)
            range_stop = int(seq.branch_address, base=16)
            if pc_addr >= range_start and pc_addr < range_stop:
                count_in_accelerated = False
            
            if pc_addr == range_start:
                self.accelerated_cycles += seq_profiles[seq.branch_address].acc_time

        in_order_instr_lat = get_ins_lat_cpu(instr)
        self.non_accelerated_cycles += in_order_instr_lat
        if count_in_accelerated:
            self.accelerated_cycles += in_order_instr_lat

    def print_cycles(self):
        print("Non accelerated cycles", self.non_accelerated_cycles)
        print("Accelerated cycles", self.accelerated_cycles)

        percentage_improvement = (1.0 - (float(self.non_accelerated_cycles)/float(self.accelerated_cycles))) * 100