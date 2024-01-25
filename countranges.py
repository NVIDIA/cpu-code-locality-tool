# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
#

import argparse
import os
import re
from collections import defaultdict

def get_range(addr, cpu_id):
    mask = 0xFFFFFFFFFFe00000
    range = addr & mask
    return (range, cpu_id)  # Return a tuple of range and cpu_id

def get_function_name_from_symbol(symbol):
    """Extract the function name from symbol information."""
    # Assuming the symbol information contains function name like 'function_name+offset'
    match = re.search(r'(.+?)\+0x', symbol)
    return match.group(1) if match else None

def gen_cpu_id_histogram(tid_dict):
    cpu_id_histogram = defaultdict(set)

    for tid, (ranges_samples, _) in tid_dict.items():
        for range, cpu_id in ranges_samples:
            cpu_id_histogram[cpu_id].add(range)

    # Print CPU ID histogram
    print(f"\n{'='*50}")
    print("CPU ID - Number of Unique ranges Histogram:\n")
    for cpu_id, ranges in sorted(cpu_id_histogram.items()):
        print(f"CPU ID {cpu_id}: {len(ranges)} unique ranges")
    print(f"\n{'='*50}")
    return cpu_id_histogram

def gen_dso_data(so_dict, total_samples, output):
    print("List of executable/libraries in this trace:\n")
    for so in so_dict.keys():
        if not so.startswith('['):
            # Ignore kernel space
            print(so)
    print(f"\n{'='*50}")
    with open(output, "w") as DSO_file:
        for so, ranges in so_dict.items():
            DSO_file.write(f"\n{so}\n")
            for range, details in ranges.items():
                count = details['count']
                symbols = '; '.join(details['sym'])  # Concatenate all function names
                percent = count * 100 / total_samples
                # Write the range, count, and concatenated function names
                DSO_file.write(f"\t {range} : {count}, {percent:.3f}%, Functions: {symbols}\n")
        DSO_file.write(f"\n{'='*50}\n")
    print(f"DSO data written to [{os.path.abspath(output)}]")

def main():
    parser = argparse.ArgumentParser(description="Process trace data")
    parser.add_argument("--perf-trace", type=str, help="Path to the tracefile to be processed.", required=True)
    parser.add_argument("--output", default="mytrace.stats", help="Output stats")
    args = parser.parse_args()
    tracefile = args.perf_trace

    pattern_with_cpu = r'^\s*[^ ]+\s+(\d+)\s+\[(\d+)\]\s+\d+\.\d+\:\s+\d+\s+cycles\:\S*\s+([0-9a-fA-F]+)\s+(.+)\s+\((.+)\)\s*$'
    pattern_without_cpu = '^.+\s+(\d+)\s+\d+\.\d+\:\s+\d+\s+cycles\:\S*\s+([0-9a-fA-F]+)\s+(.+)\s+\((.+)\)\s*$'

    tid_dict = defaultdict(lambda: ([], 0))
    so_dict = {}  # Dictionary to hold the symbols and their DSOs

    with open(tracefile, 'r') as f:
        print(f"\n{'='*50}")
        print("\nProcessing trace: ",tracefile)
        print(f"\n{'='*50}")

        for line in f:
            match_with_cpu = re.match(pattern_with_cpu, line)
            match_without_cpu = re.match(pattern_without_cpu, line)

            if match_with_cpu:
                tid = match_with_cpu.group(1)
                cpu = match_with_cpu.group(2)
                str_address = match_with_cpu.group(3)
                str_sym_org = match_with_cpu.group(4)
                str_so = match_with_cpu.group(5)
            elif match_without_cpu:
                tid = match_without_cpu.group(1)
                cpu = "N/A"
                str_address = match_without_cpu.group(2)
                str_sym_org = match_without_cpu.group(3)
                str_so = match_without_cpu.group(4)
            else:
                print(f"Unmatched line:\n{line}")
                continue

            function_name = get_function_name_from_symbol(str_sym_org)
            address = int(str_address, 16)
            range_cpu_tuple = get_range(address, cpu)  # Get the tuple of range and CPU ID
            range = range_cpu_tuple[0]  # Extract the range from the tuple

            # Now add this tuple to the list in tid_dict
            ranges_list, count = tid_dict[tid]
            ranges_list.append(range_cpu_tuple)
            tid_dict[tid] = (ranges_list, count + 1)

            # Remove 0x offset from str_sym_org
            str_sym = re.sub("\+0x.*$", "", str_sym_org)

            # Update the so_dict with the range, DSO, symbol, and function name details
            if str_so not in so_dict:
                so_dict[str_so] = {}

            if range not in so_dict[str_so]:
                so_dict[str_so][range] = {"count": 1, "sym": [str_sym], "functions": set()}
            else:
                so_dict[str_so][range]["count"] += 1
                if str_sym not in so_dict[str_so][range]["sym"]:
                    so_dict[str_so][range]["sym"].append(str_sym)
                if function_name:
                    so_dict[str_so][range]["functions"].add(function_name)

    total_samples = sum(count for _, count in tid_dict.values())
    gen_dso_data(so_dict, total_samples, args.output)
    cpu_id_histogram = gen_cpu_id_histogram(tid_dict)
    print(f"Maximum unique range count in a CPU for this trace: {max(len(x) for x in cpu_id_histogram.values())}")
    print(f"\n{'='*50}")

if __name__ == "__main__":
    main()
