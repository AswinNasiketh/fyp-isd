from trace_analyser.branch_profiler import *
from trace_analyser.sequence_selector import *
from trace_analyser.cycle_counter import *
from trace_analyser.trace_utils import *
from trace_analyser.sequence_profiler import *

max_hit_count = 64
max_area = 64
max_num_accelerators = 4
num_bprof_entries = 8

def main():
    branch_profile = BranchProfile(max_hit_count, max_area * 2)
    new_seq_addresses = None
    counters_shifted = False
    sequence_selector = SequenceSelector(max_area, max_num_accelerators, num_bprof_entries, max_hit_count)
    reconf_penalty = 0
    cycle_counter = CycleCounter()
    inst_mem = {}
    sequence_profiles = {"0": SequenceProfileEntry(0, 1, 0, 0)} #initial entry for dummy accelerator

    instr_addr = ''
    with open('trace_files/sim5.trace', 'r') as reader:
        for line in reader:
            if line[0:2] != "pc":
                continue
            instr_addr = get_instr_addr(line)
            inst_mem[instr_addr] = TraceLine(line)
            # print(inst_mem)
            cycle_counter.count_line(line, sequence_selector.accelerating_sequences, inst_mem, sequence_profiles)
            new_seq_addresses, counters_shifted = branch_profile.process_trace_line(line)

            if new_seq_addresses != None:
                branch_inst_addr, branch_target_addr = new_seq_addresses
                sequence_profiles[branch_inst_addr] = profile_seq(inst_mem, branch_target_addr, branch_inst_addr)

            reconf_penalty = sequence_selector.update_accelerated_sequences(line, branch_profile, sequence_profiles)

            cycle_counter.add_reconf_penalty(reconf_penalty)

            if counters_shifted:
                sequence_selector.shift_hits_right()

            
    print("Profiling done")
    cycle_counter.print_cycles()
    branch_profile.dump_profile()

main()