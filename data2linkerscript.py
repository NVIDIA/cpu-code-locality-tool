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

import pandas as pd
import argparse
import os


def write_gnu_linker_script(prioritized_text, outname, ld_args):
    linker_script_lines = os.popen(f"ld {ld_args} -verbose").read().split("\n")
    indices = [i for i, x in enumerate(
        linker_script_lines) if x == "=================================================="]
    linker_script_lines = linker_script_lines[indices[0]+1:indices[1]]

    text_line_start = [i for i, line in enumerate(
        linker_script_lines) if ".text           :" in line]
    assert len(
        text_line_start) == 1, "The linker script has multiple text sections!"
    text_line_start = text_line_start[0]

    linker_script_lines.insert(text_line_start+2, prioritized_text)

    with open(outname, "w") as f:
        for line in linker_script_lines:
            f.write(line + '\n')


def main():
    parser = argparse.ArgumentParser(
        description='Linker script generation from aggregated perf data')
    parser.add_argument("--profile-data", required=True, help='Comma-separated list of profile data (trace2data.py output)')
    parser.add_argument('--ld-args', help='ld arguments used when building the application (e.g. "-z now")', default='')
    parser.add_argument("--output", default="linkerscript.ld", required=False)
    parser.add_argument("--mincount", type=int, default=1, required=False)
    parser.add_argument("--symbol-ordering-file", action='store_true')

    args = parser.parse_args()
    input_files = args.profile_data.split(',')
    dataframes = list()

    raw_function_count = 0
    # try to gracefully handle profiles with repeated functions
    for input_file in input_files:
        df = pd.read_csv(input_file)
        raw_function_count += len(df)
        # merge repeated entries, sum here
        df = df.groupby(['funcname', 'libname']).agg(
            count=pd.NamedAgg(column='count', aggfunc='sum'),
            frequency=pd.NamedAgg(column='frequency', aggfunc='sum')).reset_index()
        dataframes.append(df)
    all_df = pd.concat(dataframes)

    # merge different profiles, average here, consider relying on last step only?
    merged_df = all_df.groupby(['funcname', 'libname']).agg(
        frequency=pd.NamedAgg(column='frequency', aggfunc='mean'),
        count=pd.NamedAgg(column='funcname', aggfunc='count'))
    sorted_df = merged_df.sort_values(
        by=['count', 'frequency'], ascending=False)

    # ignore libname for duplicated functions
    merged_df2 = sorted_df.groupby(['funcname']).agg(
        count=pd.NamedAgg(column='count', aggfunc='sum'),
        frequency=pd.NamedAgg(column='frequency', aggfunc='mean')).reset_index()
    sorted_df2 = merged_df2.sort_values(
        by=['count', 'frequency'], ascending=False)
    sorted_df2 = sorted_df2.loc[sorted_df2['count'] >= args.mincount]
    print(sorted_df2)

    if args.symbol_ordering_file:
        script_type = 'Symbol ordering file'
        with open(args.output, "w") as f:
            for funcname in sorted_df2['funcname']:
                f.write(f'{funcname}\n')
    else:
        script_type = 'Linker script'
        prioritized_text = ""
        for funcname in sorted_df2['funcname']:
            prioritized_text += f".text.{funcname} "
        prioritized_text = "    *(" + prioritized_text.strip() + ")"
        write_gnu_linker_script(prioritized_text, args.output, args.ld_args)

    print(f"processed raw funcs: {raw_function_count}, coalesced to: {len(sorted_df)}, final: {len(sorted_df2)}")
    print(f'{script_type} has been written to {args.output}')

if __name__ == '__main__':
    main()
