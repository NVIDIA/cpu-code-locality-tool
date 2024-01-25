# CPU code locality tool

Scripts in this repo help identifying an application that will benefit from code locality optimization on ARM architecture and will generate an optimized linker script for re-building the application.

Step 1: Gather profile data
------------------------------------------------
+ `perf record -F 100000 --sample-cpu [my_workload]`
+ `perf script --time=90%-95% --no-demangle > mytrace.txt`

Note that we are running a workload of at least several seconds in length, and that the `--time=90%-95%` flag on `perf script` is to focus our profile on the critical path of execution subsequent to the startup/warmup phase having completed. Please, adjust this time window to fit your actual workload.

Step 2: Determine whether application is a likely optimization candidate using `countranges.py`
------------------------------------------------
+ `python3 countranges.py --perf-trace mytrace.txt --output mytrace.stats`

Note this script will generate a mytrace.txt.stats file which we will use with the linker scripts below.

Step 3: Produce profile data from the perf stats using `trace2data.py`
------------------------------------------------
+ `python3 trace2data.py --symbol-stats mytrace.stats --library-list libmylib1.so,libmylib2.so,... --output mydata.csv`

Note that `trace2data.py` can be used on multiple stats files. The output CSV files will be combined by `data2linkerscript.py`.

Stats can be filtered by the executable/libraries that you plan on rebuilding via the `--library-list` argument. The `countranges.py` script from **step 2** lists the executable/library names present in the trace.

Step 4: Produce a linker script from the profile data using `data2linkerscript.py`
------------------------------------------------
+ `python3 data2linkerscript.py --profile-data mydata.csv,mydata2.csv,... --output mylinkerscript.ld`

If the application build scripts pass extra arguments to the GNU linker, make sure to add them via `--ld-args` to generate a correct linker script (e.g. `--ld-args "-z now"`).

If using the LLVM linker `lld`, use argument `--symbol-ordering-file` with `data2linkerscript.py` to output a symbol ordering file instead of a linker script.

Step 5: Use the linker script when re-building the application/library
-----------------------------------------------

Rebuild the application/library with compiler flag `-ffunction-sections` and one of the following linker flags:

With GNU linker `ld`, use flag `-Tmylinkerscript.ld`.

With LLVM linker `lld`, use flag `--symbol-ordering-file=mylinkerscript.ld`.
