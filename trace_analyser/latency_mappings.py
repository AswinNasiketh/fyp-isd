
fetch_latency = 1
decode_issue_latency = 2


ins2funcacc = {} #mapping from instruction to functional unit for accelerator
ins2funccpu = {} #mapping from instruction to functional unit for cpu
func2latacc = {} #mapping of functional units to latency for accelerator
func2latcpu = {} #mapping of functional units to latency for cpu (includes fecth->dispatch latency)

#in future these dictionaries will be updated with different latencies for accelerator and CPU
#CPU will use full functional unit latencies
#accelerator will only use latencies of part of functional unit responsible for instruction