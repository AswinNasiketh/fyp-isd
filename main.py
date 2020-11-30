from trace_analyser.branch_profiler import *
from trace_analyser.sequence_selector import *
from trace_analyser.cycle_counter import *

def main():
    branch_profile = BranchProfile()
    sequence_selector = SequenceSelector(4)
    cycle_counter = CycleCounter(4)

    with open('trace_files/sim4.trace', 'r') as reader:
        for line in reader:
            cycle_counter.count_line(line, sequence_selector.accelerating_sequences)
            branch_profile.process_trace_line(line)
            sequence_selector.update_accelerated_sequences(line, branch_profile)
    print("Profiling done")
    cycle_counter.print_cycles()
    branch_profile.dump_profile()

main()