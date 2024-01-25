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
import csv
import re
import pandas as pd

def parse_dso_file(dso_file_path, libraries):
    symbol_counts = {}
    functions = {}
    current_lib = None
    with open(dso_file_path, 'r') as file:
        for line in file:
            # Check for a library header with a path and ignore libraries within []
            if '/' in line and not line.strip().startswith('[') and ':' not in line:
                current_lib = line.strip()
                functions[current_lib] = []
                continue

            if current_lib and any(lib.lower() in current_lib.lower() for lib in libraries):
                # Extract the count and percentage
                match = re.match(r'\s*(\d+) : (\d+), (\d+\.\d+)%', line)
                if match:
                    range = match.group(1)
                    count = int(match.group(2))
                    # Extract function names after "Functions: "
                    func_names = re.findall(r'Functions: (.+)', line)
                    func_list = func_names[0].split('; ') if func_names else []
                    symbol_counts[current_lib] = symbol_counts.get(current_lib, 0) + count
                    functions[current_lib].extend(func_list)

    # Sort the function lists for each library
    for lib in functions:
        functions[lib] = sorted(set(functions[lib]))

    return symbol_counts, functions

def write_to_csv(output_file, data, functions):
    total_count = sum(data.values())
    all_rows = []
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['row', 'funcname', 'libname', 'count', 'frequency']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        row_counter = 0
        for lib in sorted(data):
            count = data[lib]
            func_list = sorted(set(functions.get(lib, [])))
            if not func_list:
                row = {
                    'row': row_counter,
                    'funcname': '',
                    'libname': lib,
                    'count': count,
                    'frequency': count / total_count
                }
                writer.writerow(row)
                all_rows.append(row)
                row_counter += 1
            else:
                for func in func_list:
                    row = {
                        'row': row_counter,
                        'funcname': func,
                        'libname': lib,
                        'count': count,
                        'frequency': count / total_count
                    }
                    writer.writerow(row)
                    all_rows.append(row)
                    row_counter += 1

    df = pd.DataFrame(all_rows)
    print(df)

def main(dso_filename, libname, output):
    libraries = [lib.strip() for lib in libname.split(',')]
    symbol_counts, functions = parse_dso_file(dso_filename, libraries)
    write_to_csv(output, symbol_counts, functions)
    print(f"Data has been written to {output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate CSV data from .DSO file.')
    parser.add_argument("--symbol-stats", help="Input symbol stats (countranges.py output)", required=True)
    parser.add_argument("--library-list", help="Comma-separated list of executable/libraries to filter trace", default='')
    parser.add_argument("--output", default="mydata.csv", help="Output CSV filename")

    args = parser.parse_args()
    main(args.symbol_stats, args.library_list, args.output)
