from trace_analyser.acc_organiser import ReconfigurableFabric
from trace_analyser.branch_profiler import *
from trace_analyser.sequence_selector import *
from trace_analyser.cycle_counter import *
from trace_analyser.trace_utils import *
from trace_analyser.sequence_profiler import *
from trace_analyser.logger import *
# from trace_analyser.graph_visualiser import *
# import trace_analyser.interconnect_stats
from trace_analyser.ou_organiser import estimateGridSize, genPRGrid
from trace_analyser.rci_params import *

trace_file = 'trace_files/sim_ds_mod.trace'

print_line("Simulation Params")
print_line("Max Hit Count", max_hit_count)
print_line("RF num rows", rf_num_rows)
print_line("RF num cols", rf_num_cols)
print_line("Max Num Acclerators", max_num_accelerators)
print_line("Num BProf Entries", num_bprof_entries)
print_line("Reconf start penalty modifier" , RECONF_START_PENALTY_MODIFIER)
print_line("Reconf penalty modifier", RECONF_PENALTY_MODIFIER)

print_line("Using trace", trace_file)


def main():
    branch_profile = BranchProfile(max_hit_count, max_area)
    new_seq_addresses = None
    counters_shifted = False
    sequence_selector = SequenceSelector(rf_num_rows, max_num_accelerators, num_bprof_entries, max_hit_count)
    reconf_penalty = 0
    cycle_counter = CycleCounter()
    inst_mem = {}
    # dummy_profile = SequenceProfileEntry(0, 1, 0, 0, DFGraph(), 0)
    # dummy_profile.num_rows = 0
    sequence_profiles = {} #initial entry for dummy accelerator
    rf = ReconfigurableFabric(rf_num_rows, rf_num_cols)

    instr_addr = ''
    line_num = 0
    with open(trace_file, 'r') as reader:
        for line in reader:
            # print_line("Line number:", line_num)
            line_num += 1

            #ignore lines of the trace which do not show instructions
            if line[0:2] != "pc":
                continue
            instr_addr = get_instr_addr_dec_str(line)
            trace_line_obj = TraceLine(line)
            inst_mem[instr_addr] = trace_line_obj
            # print_line(inst_mem)
            
            new_seq_addresses, counters_shifted = branch_profile.process_trace_line(trace_line_obj)

            if new_seq_addresses != None:
                branch_inst_addr, branch_target_addr = new_seq_addresses
                print_line("New Sequence", branch_inst_addr, branch_target_addr)
                print_line("Num Sequences Profiled", len(sequence_profiles))
                sequence_profiles[branch_inst_addr] = profile_seq(inst_mem, branch_target_addr, branch_inst_addr)
                #*PRGrid Generation Test
                # numRows = estimateGridSize(sequence_profiles[branch_inst_addr].df_graph)
                # newPG, unCost, lsuCost, IOCost = genPRGrid(sequence_profiles[branch_inst_addr].df_graph, numRows, rf_num_cols)

                # if unCost > 0 or lsuCost > 0 or IOCost > 0:                    
                #     print_line("PR Grid not found")
                #     print_line(branch_inst_addr, branch_target_addr)

                #     print_line("Unconnected Nets Cost", unCost)
                #     print_line("LSU Congestion Cost", lsuCost)
                #     print_line("IO Congestion Cost", IOCost)

                #     newPG.visualise()


            reconf_penalty = sequence_selector.update_accelerated_sequences(trace_line_obj, branch_profile, sequence_profiles, rf)

            cycle_counter.count_line(trace_line_obj, sequence_selector.accelerating_sequences, inst_mem, sequence_profiles, reconf_penalty)

            # if reconf_penalty > 0:
            #     print_line("Accelerators changing, showing dataflow graphs")
                
            #     acc_start_addrs = [seq.branch_address for seq in sequence_selector.accelerating_sequences]

            #     plot_accs(acc_start_addrs, sequence_profiles)


            # cycle_counter.add_reconf_penalty(reconf_penalty)

            if counters_shifted:
                sequence_selector.shift_hits_right()

            
    print_line("Profiling done")
    cycle_counter.print_cycles()

    for key, prof in sequence_profiles.items():
        print_line("Sequence Branch Address:", key)
        prof.print_profile()

    # print_line("Gathering interconnect stats")
    # output_mutiplicites_lst, multi_branch_outputs_lst, input_count_lst, width_lst, depth_lst, size_lst, lsu_ops_lst, feedback_paths = trace_analyser.interconnect_stats.extract_stats(sequence_profiles)
    # trace_analyser.interconnect_stats.display_histograms(output_mutiplicites_lst, multi_branch_outputs_lst, input_count_lst, width_lst, depth_lst, size_lst, lsu_ops_lst, feedback_paths)
    # branch_profile.dump_profile()

main()