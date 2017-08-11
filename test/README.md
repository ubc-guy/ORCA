# ORCA Automated Building and Testing
--------------------------------------------------
This directory contains the Makefile which starts the automated build/testing process, and is the
location where all the test builds are located when the test scripts are run.
The test scripts are located in the `GIT_TOP/scripts/` submodule.

## Makefile
--------------------------------------------------

The Makefile contains 4 different sections, one for Altera builds, one for Xilinx builds, one
for Microsemi builds, and one for Lattice builds. The Makefile is used to build the hardware
for each family of FPGAs. As of August 2017, only the Altera and Xilinx sections of the Makefile
build the ORCA hardware successfully when called from the build scripts. The Microsemi and Lattice
sections are yet unimplemented. 

To run the whole test process with the default build configurations, run `make builds`. Note that you
need to do the appropriate environment setup for the specific FPGA families your targeting. To build
for Altera targets, run: 
`ncsh latest full` 

for Xilinx targets, run:
`source /nfs/opt/xilinx/Vivado/latest/settings64.sh`
`export XILINXD_LICENSE_FILE=2100@vax`	
	 
## ORCA Build Configuration
--------------------------------------------------

The ORCA builds are initialized through the use of a Python script named `build_cfg_orca.py`. This file
is located in `GIT_TOP/test/build_cfg_orca.py`.

In this file, there is a variable `ORCA_BUILDS` that contains each of the builds that will be run by
the test scripts. This variable is an array of build configurations, each of which is generated by
a family specific Python function of the form `<family>_<architecture>_BuildCfg()`. These build
configurations contain all of the ORCA hdl parameters for the test. To test across multiple different
ORCA parameters, different build configurations with different parameters should be put in the array.

For the Xilinx builds, there needs to be a UART configuration variable for the scripts to communicate
with ORCA over UART. This is given in the `ZEDBOARD_UART_CFG`.

More than one family of architectures can exist in the same `ORCA_BUILDS` array, however, the builds
in the array will only be run if the required family flag is passed to the build scripts.

This array is used in build.py, which is the top level build script.

## Script Parameters
--------------------------------------------------

To learn about the details of the parameters of the build scripts, run `python build.py -h`.

When it comes to selecting which builds of the `ORCA_BUILDS` array to run, the key parameters
are -a, -x, -m, -s, -t, -u, -v, which correspond to Altera MXP builds, Xilinx MXP builds, 
Microsemi MXP builds, Microsemi Orca builds, Lattice Orca builds, Xilinx Orca builds, and 
Altera Orca builds, respectively. For each build in the `ORCA_BUILDS` array, if the flag is set
for the corresponding build architecture, then the test scripts will run that build using the
corresponding family specific function `build_<family>_<architecture>`.


## build_orca Functions
--------------------------------------------------

There are 5 main steps in the `build_orca` functions: 

1) Generate the software build directories
2) Set up the build
3) Compile and running the build
4) Check the test logs
5) Email the results

### Software Build Directories
--------------------------------------------------

The software build directories are generated using by using a glob-style accumulation of each folder
in the software directories. It also includes the riscv-tests/isa directory directly, since it has a unique
test directory structure. This is because they are copied over from the riscv isa tests repository. Each class
of tests has an associated build directory which includes the Makefile. Within each build directory, there is a
directory for each individual test which holds the test code as well as a Makefrag that contains some test 
specific build information. When the scripts compile the software, a binary is generated for each test 
subdirectory of each software build directory.

### Build Setup
--------------------------------------------------

The next step is to set up the build. This sets up the directory structure for the current build, and copies over
the required software directory. The top level directory name contains the hash of the current git commit (plus
`_mods` is tacked to the end if there are local modifications), and the next directory name contains the build configuration
information (the hdl parameters selected for the build). For example, for:

`20170809_133415_b27af1a980617eac3e61d1b3b736674c16f5d626_mods/de2-115_me1_de1_ps5_lve0_int1_1_po0_ce0`

The first directory contains the build date/time, then then git commit hash (plus the `_mods` at the end to signify that 
there are local modifications). The second directory contains the build platform (`de2-115`), and the hdl parameters. 
`me1` corresponds to `MULTIPLY_ENABLE=1`, `int1_1` corresponds to `ENABLE_EXT_INTERRUPTS=1`, and `NUM_EXT_INTERRUPTS=1`, etc.

The build setup is device-specific; each FPGA family requires different files to be present in the build directory to build 
the system. In addition, the hdl parameters are modified in this step to match the required build parameters. For example, 
if you set `CACHE_ENABLED=1` in `build_cfg_orca.py`, then in this step the ORCA hdl parameter `CACHE_ENABLED` will be set 
to `1` for this build. 

In the set up step, the riscv tests are also modified slightly to work with the automated build scripts. To do this,
the Makefile is modified slightly to use the ORCA linker script, and to include the common ORCA utility files for
the family-specific functions like `printf()`. The pass/fail clause of each test is also modified to write over the
UART rather than writing a value to a register. This allows the ORCA to communicate to the scripts whether the test
passed or failed. The `test_pass` and `test_fail` functions (located in `GIT_TOP/test/software/common/test_passfail.c`) 
contain a specific statement that will be logged by the scripts. This log will be later parsed in order to determine 
whether the test was successful or not. These functions also output ASCII 0x4 (Cx-d) to the host terminal in order to 
exit when the test is completed. This remote exit functionality is natively built into nios2-terminal, and the miniterm 
scripts used for the xilinx build have been modified to also perform this remote exit. The UART output from `test_pass`
and `test_fail` is run in an infinite loop after the test is complete in case the host terminal missed it the first time.

As of right now, there are unit tests included in the build, however, they have not yet been modified to use the
`test_pass` and `test_fail` functions, so they will fail every time regardless of outcome. In addition, the tests
are not making full use of the test scripts functionality; it would also be possible to put the number of test errors
over UART, and the scripts would parse that and include it in the results table. For now, when the riscv isa tests
fail explicitly, they fail with one error.

The final step in the build setup is to create the compile script. The script essentially calls the Makefile
to build the hardware, then calls `make` for each software test. The software test elf is then copied into a
separate directory, in which the compile logs, test logs, and timing logs are stored. The test elf is not copied if
it already exists, as this would cause the test to be re-run unneccesarily. If not run locally (`-l` is not passed to 
the test scripts), then the scripts use GridEngine instead for compilation.

### Compilation & Test Running
--------------------------------------------------

Next, the scripts compile all the pending builds by executing the relevant compile scripts. Once they are compiled,
the output logs for the hardware and software builds are parsed, and the compile warnings and errors are stored for
later. Once everything has been compiled, the software tests for each build are run sequentially on the target
device. This process is specific to the target FPGA family. 

For Altera, the .sof bitstream file that was generated for the current build is flashed to the device over JTAG. 
The build scripts will automatically call `jtagd` and connect to the target FPGA on their own. However, if 
something goes wrong, the scripts will stall and wait for user input before continuing. Each test elf file is then
converted to a raw binary file. The script then runs `orca_pgm.py` found in the `GIT_TOP/tools/` directory, which
holds the ORCA in reset, writes each byte in the .bin file to its corresponding address in the ORCA's instruction
ram, then releases the ORCA from reset. The scripts then run nios-2 terminal with a given timeout period. If the
test puts ASCII 0x4 over UART, nios2-terminal exits. The output over UART is logged, it will be parsed later to
determine if the test passed or failed. This process continues as the scripts iterate over the entire test list.

For Xilinx, the .bit bitstream file that was generated is flashed over JTAG to the fabric using the Xilinx 
XSDB tool. Ideally, the XSDB tool *should* be able to also write from the PS to the PL through an AXI bus,
but the tool currently doesn't allow it. It may be a permissions issue, or it may be a configuration issue; it's
not clear. One thing I found was that there is a `user_init` function referenced in some of the Xilinx forum 
posts, however, it is not located anywhere in the `ps7_init.tcl` that gets generated by the Xilinx SDK tools.
Another option is to use a JTAG Master block in the block design, and try accessing the PL through that using
the Vivado hardware manager. However, the hardware manager is unable to detect the JTAG Master block in its current
configuration. It may be due to how the resets are currently configured for the system, as there is a memory-mapped
auxillary reset that is feeding into reset controller to allow the JTAG bus to hold the ORCA in reset while it copies
over data to the IDRAM. It's not clear what's causing the JTAG to not be recognized, but the JTAG Master block seems
more likely to work than the XSDB solution, as the XSDB solution is giving a very clear message that the tool is not
allowed to write from the PS to the PL using JTAG transactions. More investigation is needed. A final option is to not
use JTAG, but to instead modify the bitstream with the test's .elf file. This is currently what is done in the
`GIT_TOP/systems/zedboard/` project, however, it may not be expandable to multicore systems.

As each software test is run, the terminal output is logged to be parsed later.

### Checking Test Logs
--------------------------------------------------

After the tests are finished running, each test log is parsed to prepare the test results. The scripts check whether
the tests passed, and the runtime of the test. Currently the test runtime feature seems to be bugged, but it shouldn't
be too difficult to fix. For the riscv isa tests, it is expected that many of them fail, as we do not implement a large
portion of the instruction set. Currently, certain isa tests fail in the automated test process that shouldn't. Further
investigation is required.

### Emailing the Results
--------------------------------------------------

In the final step of the test scripts, the parsed log data is formatted into an html table and emailed to each 
person in the notify list, as well as your own email if it is registered with git. The table contains all of the
hardware build warnings, hardware critical warnings, hardware errors, software warnings, software errors, and test
errors that were parsed from the compile/test logs during the build/test process.