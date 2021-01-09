from trace_analyser.branch_profiler import *
from trace_analyser.sequence_selector import *
from trace_analyser.cycle_counter import *
from trace_analyser.trace_utils import *
from trace_analyser.sequence_profiler import *
from trace_analyser.logger import *

trace_file = 'trace_files/sim_cm20.trace'

max_hit_count = 64
max_area = 64
max_num_accelerators = 4
num_bprof_entries = 8

print_line("Simulation Params")
print_line("Max Hit Count", max_hit_count)
print_line("Max Area", max_area)
print_line("Max Num Acclerators", max_num_accelerators)
print_line("Num BProf Entries", num_bprof_entries)
print_line("Reconf start penalty modifier" , RECONF_START_PENALTY_MODIFIER)
print_line("Reconf penalty modifier", RECONF_PENALTY_MODIFIER)

print_line("Using trace", trace_file)


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
    line_num = 0
    with open(trace_file, 'r') as reader:
        for line in reader:
            print_line("Line number:", line_num)
            line_num += 1

            if line[0:2] != "pc":
                continue
            instr_addr = get_instr_addr(line)
            inst_mem[instr_addr] = TraceLine(line)
            # print_line(inst_mem)
            
            new_seq_addresses, counters_shifted = branch_profile.process_trace_line(line)

            if new_seq_addresses != None:
                branch_inst_addr, branch_target_addr = new_seq_addresses
                sequence_profiles[branch_inst_addr] = profile_seq(inst_mem, branch_target_addr, branch_inst_addr)

            reconf_penalty = sequence_selector.update_accelerated_sequences(line, branch_profile, sequence_profiles)

            cycle_counter.count_line(line, sequence_selector.accelerating_sequences, inst_mem, sequence_profiles, reconf_penalty)

            # cycle_counter.add_reconf_penalty(reconf_penalty)

            if counters_shifted:
                sequence_selector.shift_hits_right()

            
    print_line("Profiling done")
    cycle_counter.print_cycles()
    branch_profile.dump_profile()

main()