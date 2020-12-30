from trace_analyser.branch_profiler import *
from trace_analyser.sequence_selector import *
from trace_analyser.cycle_counter import *
from trace_analyser.trace_utils import *
from trace_analyser.sequence_profiler import *

def main():
    branch_profile = BranchProfile()
    new_seq_addresses = None
    sequence_selector = SequenceSelector(4, 8)
    cycle_counter = CycleCounter()
    inst_mem = {}
    sequence_profiles = {}

    instr_addr = ''
    with open('trace_files/sim4.trace', 'r') as reader:
        for line in reader:
            if line[0:2] != "pc":
                continue
            instr_addr = get_instr_addr(line)
            inst_mem[instr_addr] = TraceLine(line)
            # print(inst_mem)
            cycle_counter.count_line(line, sequence_selector.accelerating_sequences, inst_mem, sequence_profiles)
            new_seq_addresses = branch_profile.process_trace_line(line)

            if new_seq_addresses != None:
                branch_inst_addr, branch_target_addr = new_seq_addresses
                sequence_profiles[branch_inst_addr] = profile_seq(inst_mem, branch_target_addr, branch_inst_addr)

            sequence_selector.update_accelerated_sequences(line, branch_profile, sequence_profiles)

            
    print("Profiling done")
    cycle_counter.print_cycles()
    branch_profile.dump_profile()

main()