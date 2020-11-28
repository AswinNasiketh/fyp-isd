from trace_analyser.branch_profiler import *

def main():
    branch_profile = BranchProfile()

    with open('trace_files/sim4.trace', 'r') as reader:
        for line in reader:
            branch_profile.process_trace_line(line)
    
    print("Profiling done:")
    branch_profile.dump_profile()

main()