from trace_analyser.latency_mappings import *
import functools
from trace_analyser.logger import *

#dictate how aggressive the model is in going for reconfigurations. Lower numbers mean more risky. Realistically must be greater than 0.
RECONF_START_PENALTY_MODIFIER = 0.0 
RECONF_PENALTY_MODIFIER = 0.5

class AccleratedSequence:
    def __init__(self, branch_address, branch_target_addr, reconfiguring = True):
        self.branch_address = branch_address
        self.branch_target_addr = branch_target_addr
        self.hits = 0
        self.reconfiguring = reconfiguring
        
    def shift_num_hits_right(self):
        self.hits = self.hits >> 1

    def increment_hits(self):
        self.hits += 1

class SequenceSelector:
    def __init__(self, rf_num_rows, max_accelerators, bprof_size, max_hit_count):
        self.rf_num_rows = rf_num_rows
        self.max_accelerators = max_accelerators
        self.accelerating_sequences = []
        self.hit_saturate_limit = max_hit_count
        self.bprof_size = bprof_size
    
    def shift_hits_right(self):
        for seq in self.accelerating_sequences:
            seq.shift_num_hits_right()

    def update_hits(self, trace_line):

        for seq in self.accelerating_sequences:
            if seq.branch_address == str(trace_line.instr_addr):
                seq.increment_hits()

                if seq.hits >= self.hit_saturate_limit:
                    self.shift_hits_right()                
                break

    
    def caclulate_advantage(self, seq_profile):
        return seq_profile.cpu_time - seq_profile.acc_time #todo incorportate intiation interval

    def calculate_improvement(self, seq_profile, hits):
        return (self.caclulate_advantage(seq_profile) * hits) - (seq_profile.reconf_time * RECONF_PENALTY_MODIFIER)

    def get_replacement_seqs(self, branch_profile, seq_profiles):
        top_branches = branch_profile.get_n_most_executed_branches(self.bprof_size)
        acceleration_advantages = list(map(lambda b: (b.branch_instr_addr, self.caclulate_advantage(seq_profiles[b.branch_instr_addr])), top_branches)) #calculate advantage of accelerating each identified seq, store in tuple with its address
        acceleration_advantages.sort(key= lambda a: a[1], reverse=True)#put in descending order of advantages
        
        if len(acceleration_advantages) > self.max_accelerators:
            acceleration_advantages = acceleration_advantages[0:self.max_accelerators]# trim to maximum number of accelerators allowed
        acc_seq_addrs = [seq.branch_address for seq in self.accelerating_sequences]
        return [addr for addr, adv in acceleration_advantages if addr not in acc_seq_addrs] #return adresses of sequences which can be substituted

    def calculate_improvement_diff(self, rep_seq, seq_profiles, branch_profile, current_acc_improvements, rf):
        row_cost = seq_profiles[rep_seq].area_cost()
        if row_cost == -1: #annealing failed cannot place accelerator improvement
            return 0, -1; #return -1 for improvement difference so that this accelerator not taken into account
        
        improvement_gain = self.calculate_improvement(seq_profiles[rep_seq], branch_profile.get_entry_for_addr(rep_seq).num_branch_taken)

        extra_rows_required = rf.extraRowsRequired(row_cost)

        improvement_loss = 0
        num_accs_to_replace = 0        

        #to prevent more than the maximum available accelerator slots being used
        if len(self.accelerating_sequences) == self.max_accelerators:
            num_accs_to_replace = 1
            improvement_loss += current_acc_improvements[0][1]
            extra_rows_required -= seq_profiles[current_acc_improvements[0][0]].area_cost()
        
        for addr, imp in current_acc_improvements[num_accs_to_replace:]:
            if extra_rows_required <= 0:
                break
            
            improvement_loss += imp
            extra_rows_required -= seq_profiles[addr].area_cost()
            num_accs_to_replace += 1
        
        if extra_rows_required > 0:
            return num_accs_to_replace, -1 #negative result will be disregarded in next step 
            #todo:in reality, careful tuning of max backward branch displacement is required to ensure area isn't exceeded by single seq
        else:
            return num_accs_to_replace, improvement_gain - improvement_loss

    def get_sorted_current_improvements(self, seq_profiles):
        current_acc_improvements = list(map(lambda s: (s.branch_address, self.calculate_improvement(seq_profiles[s.branch_address], s.hits)), self.accelerating_sequences))

        current_acc_improvements.sort(key=lambda x: x[1])

        return current_acc_improvements

    def calculate_improvement_diffs(self, rep_seqs, branch_profile, seq_profiles, rf):
        current_acc_improvements = self.get_sorted_current_improvements(seq_profiles)

        imp_diffs = []
        pos_diffs_sum = 0
        for addr in rep_seqs:
            num_accs_to_replace, imp_diff = self.calculate_improvement_diff(addr, seq_profiles, branch_profile, current_acc_improvements, rf)
            if imp_diff > 0: # only consider accelerators which provide more improvement than 0
                imp_diffs.append((addr, num_accs_to_replace, imp_diff))
                pos_diffs_sum += imp_diff

        if pos_diffs_sum > RECONF_START_PENALTY * CPU_CLK_FREQ * RECONF_START_PENALTY_MODIFIER:
            return imp_diffs
        else:
            return []

    def replace_accelerator(self, current_acc_branch_address, new_acc):
        print_line("replacing:", current_acc_branch_address, "with:", new_acc.branch_address)
        for i, acc in enumerate(self.accelerating_sequences):
            if acc.branch_address == current_acc_branch_address:
                self.accelerating_sequences[i] = new_acc
                break
    
    def remove_accelerator(self, current_acc_branch_addr):
        for acc in self.accelerating_sequences:
            if acc.branch_address == current_acc_branch_addr:
                self.accelerating_sequences.remove(acc)
                break

    def add_accelerator(self, best_seq_to_acc, num_accs_to_replace, branch_profile, seq_profiles, rf):
        print_line("Adding accelerator for seq at:", best_seq_to_acc, "Replacing", num_accs_to_replace, "accelerators")
        current_acc_improvements = self.get_sorted_current_improvements(seq_profiles)
        # print_line(current_acc_improvements)

        replacement_acc_IDs = []
        for i in range(num_accs_to_replace):
            replacement_acc_IDs.append(current_acc_improvements[i][0])
            self.remove_accelerator(current_acc_improvements[i][0])

        new_accelerator_bprof = branch_profile.get_entry_for_addr(best_seq_to_acc)
        new_acc = AccleratedSequence(best_seq_to_acc, new_accelerator_bprof.branch_target)
        new_acc.hits = new_accelerator_bprof.num_branch_taken

        self.accelerating_sequences.append(new_acc)

        compactingCost = 0
        if num_accs_to_replace > 0:
            compactingCost = rf.replaceAccelerators(replacement_acc_IDs, best_seq_to_acc, seq_profiles[best_seq_to_acc].pg)
        else:
            rf.addAccelerator(rf.findNextFreeRow(), best_seq_to_acc, seq_profiles[best_seq_to_acc].pg)
        
        return compactingCost * FRAMES_PER_FU * RECONF_TIME_PER_FRAME * CPU_CLK_FREQ


    def update_accelerated_sequences(self, trace_line, branch_profile, seq_profiles, rf):
        # print_line("New line")
        # current_acc_improvements = self.get_sorted_current_improvements(seq_profiles)
        # print_line(current_acc_improvements)
        self.update_hits(trace_line)

        rep_seqs = self.get_replacement_seqs(branch_profile, seq_profiles)
        improvement_diffs = self.calculate_improvement_diffs(rep_seqs, branch_profile, seq_profiles, rf)
        reconf_penalty = 0
        if len(improvement_diffs) > 0:
            reconf_penalty += RECONF_START_PENALTY
        #iterates until no further improvements can be made
        while len(improvement_diffs) > 0:
            best_seq_to_acc, num_accs_to_replace, _ = max(improvement_diffs, key= lambda x: x[2])
            reconf_penalty += self.add_accelerator(best_seq_to_acc, num_accs_to_replace, branch_profile, seq_profiles, rf)

            reconf_penalty += seq_profiles[best_seq_to_acc].reconf_time #only takes into account adding of graph nodes, assumes Nones do not need to be written to fabric

            rep_seqs = self.get_replacement_seqs(branch_profile, seq_profiles)
            improvement_diffs = self.calculate_improvement_diffs(rep_seqs, branch_profile, seq_profiles, rf)

        return reconf_penalty