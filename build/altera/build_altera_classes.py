import glob
import os
import sys
import re
import logging
import datetime
import shlex
import signal
import time
import copy
import stat
import shutil
import subprocess
import fcntl

repo_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '../..'))
scripts_dir = repo_dir+'/scripts'

scripts_build_path = scripts_dir+'/build'
if scripts_build_path not in sys.path:
    sys.path.append(scripts_build_path)

from build_common import *
from build_common_classes import *

scripts_common_path = scripts_dir+'/common'
if scripts_common_path not in sys.path:
    sys.path.append(scripts_common_path)

from file_utils import *
    
scripts_altera_path = scripts_dir+'/build/altera'
if scripts_altera_path not in sys.path:
    sys.path.append(scripts_altera_path)

from build_altera_common import *

repo_build_path = repo_dir+'/build'
if repo_build_path not in sys.path:
    sys.path.append(repo_build_path)

from build_classes import *


#Altera specific defaults
DEFAULT_RESET_VECTOR=0x00000000
DEFAULT_INTERRUPT_VECTOR=0x00000200
DEFAULT_MAX_IFETCHES_IN_FLIGHT=3
DEFAULT_BTB_ENTRIES=16
DEFAULT_MULTIPLY_ENABLE=1
DEFAULT_DIVIDE_ENABLE=1
DEFAULT_SHIFTER_MAX_CYCLES=1
DEFAULT_ENABLE_EXCEPTIONS=1
DEFAULT_PIPELINE_STAGES=5
DEFAULT_VCP_ENABLE=0
DEFAULT_ENABLE_EXT_INTERRUPTS=1
DEFAULT_NUM_EXT_INTERRUPTS=2
DEFAULT_POWER_OPTIMIZED=0

DEFAULT_LOG2_BURSTLENGTH=4
DEFAULT_AXI_ID_WIDTH=2

DEFAULT_AUX_MEMORY_REGIONS=1
DEFAULT_AMR0_ADDR_BASE=0x00000000
DEFAULT_AMR0_ADDR_LAST=0xFFFFFFFF

DEFAULT_UC_MEMORY_REGIONS=0
DEFAULT_UMR0_ADDR_BASE=0x00000000
DEFAULT_UMR0_ADDR_LAST=0x00000000

DEFAULT_ICACHE_SIZE=0
DEFAULT_ICACHE_LINE_SIZE=32
DEFAULT_ICACHE_EXTERNAL_WIDTH=32

DEFAULT_INSTRUCTION_REQUEST_REGISTER=0
DEFAULT_INSTRUCTION_RETURN_REGISTER=0
DEFAULT_IUC_REQUEST_REGISTER=1
DEFAULT_IUC_RETURN_REGISTER=0
DEFAULT_IAUX_REQUEST_REGISTER=1
DEFAULT_IAUX_RETURN_REGISTER=0
DEFAULT_IC_REQUEST_REGISTER=1
DEFAULT_IC_RETURN_REGISTER=0

DEFAULT_DCACHE_SIZE=0
DEFAULT_DCACHE_WRITEBACK=1
DEFAULT_DCACHE_LINE_SIZE=32
DEFAULT_DCACHE_EXTERNAL_WIDTH=32

DEFAULT_DATA_REQUEST_REGISTER=0
DEFAULT_DATA_RETURN_REGISTER=0
DEFAULT_DUC_REQUEST_REGISTER=2
DEFAULT_DUC_RETURN_REGISTER=1
DEFAULT_DAUX_REQUEST_REGISTER=2
DEFAULT_DAUX_RETURN_REGISTER=1
DEFAULT_DC_REQUEST_REGISTER=1
DEFAULT_DC_RETURN_REGISTER=0

##########################################################################
class Alt_ORCA_BuildCfg(ORCA_BuildCfgBase):

    ######################################################################
    def __init__(self,
                 system,
                 reset_vector=DEFAULT_RESET_VECTOR,
                 interrupt_vector=DEFAULT_INTERRUPT_VECTOR,
                 max_ifetches_in_flight=DEFAULT_MAX_IFETCHES_IN_FLIGHT,
                 btb_entries=DEFAULT_BTB_ENTRIES,
                 multiply_enable=DEFAULT_MULTIPLY_ENABLE,
                 divide_enable=DEFAULT_DIVIDE_ENABLE,
                 shifter_max_cycles=DEFAULT_SHIFTER_MAX_CYCLES,
                 enable_exceptions=DEFAULT_ENABLE_EXCEPTIONS,
                 pipeline_stages=DEFAULT_PIPELINE_STAGES,
                 vcp_enable=DEFAULT_VCP_ENABLE,
                 enable_ext_interrupts=DEFAULT_ENABLE_EXT_INTERRUPTS,
                 num_ext_interrupts=DEFAULT_NUM_EXT_INTERRUPTS,
                 power_optimized=DEFAULT_POWER_OPTIMIZED,
                 log2_burstlength=DEFAULT_LOG2_BURSTLENGTH,
                 axi_id_width=DEFAULT_AXI_ID_WIDTH,
                 aux_memory_regions=DEFAULT_AUX_MEMORY_REGIONS,
                 amr0_addr_base=DEFAULT_AMR0_ADDR_BASE,
                 amr0_addr_last=DEFAULT_AMR0_ADDR_LAST,
                 uc_memory_regions=DEFAULT_UC_MEMORY_REGIONS,
                 umr0_addr_base=DEFAULT_UMR0_ADDR_BASE,
                 umr0_addr_last=DEFAULT_UMR0_ADDR_LAST,
                 icache_size=DEFAULT_ICACHE_SIZE,
                 icache_line_size=DEFAULT_ICACHE_LINE_SIZE,
                 icache_external_width=DEFAULT_ICACHE_EXTERNAL_WIDTH,
                 instruction_request_register=DEFAULT_INSTRUCTION_REQUEST_REGISTER,
                 instruction_return_register=DEFAULT_INSTRUCTION_RETURN_REGISTER,
                 iuc_request_register=DEFAULT_IUC_REQUEST_REGISTER,
                 iuc_return_register=DEFAULT_IUC_RETURN_REGISTER,
                 iaux_request_register=DEFAULT_IAUX_REQUEST_REGISTER,
                 iaux_return_register=DEFAULT_IAUX_RETURN_REGISTER,
                 ic_request_register=DEFAULT_IC_REQUEST_REGISTER,
                 ic_return_register=DEFAULT_IC_RETURN_REGISTER,
                 dcache_size=DEFAULT_DCACHE_SIZE,
                 dcache_writeback=DEFAULT_DCACHE_WRITEBACK,
                 dcache_line_size=DEFAULT_DCACHE_LINE_SIZE,
                 dcache_external_width=DEFAULT_DCACHE_EXTERNAL_WIDTH,
                 data_request_register=DEFAULT_DATA_REQUEST_REGISTER,
                 data_return_register=DEFAULT_DATA_RETURN_REGISTER,
                 duc_request_register=DEFAULT_DUC_REQUEST_REGISTER,
                 duc_return_register=DEFAULT_DUC_RETURN_REGISTER,
                 daux_request_register=DEFAULT_DAUX_REQUEST_REGISTER,
                 daux_return_register=DEFAULT_DAUX_RETURN_REGISTER,
                 dc_request_register=DEFAULT_DC_REQUEST_REGISTER,
                 dc_return_register=DEFAULT_DC_RETURN_REGISTER,
                 opt_sysid='',
                 dstdir='',
                 skip_sw_tests=False,
                 iterate_bsp_opt_flags=False,
                 use_lic=False,
                 pgm_cable='',
                 qsf_opts=None):

        build_id = '%s%s' % \
            (system,
             opt_sysid)
        if reset_vector != DEFAULT_RESET_VECTOR:
            build_id += '_rv%X' % reset_vector
        if interrupt_vector != DEFAULT_INTERRUPT_VECTOR:
            build_id += '_iv%X' % interrupt_vector
        if max_ifetches_in_flight != DEFAULT_MAX_IFETCHES_IN_FLIGHT:
            build_id += '_mif%d' % max_ifetches_in_flight
        if btb_entries != DEFAULT_BTB_ENTRIES:
            build_id += '_btb%d' % btb_entries
        if multiply_enable != DEFAULT_MULTIPLY_ENABLE:
            build_id += '_me%d' % multiply_enable
        if divide_enable != DEFAULT_DIVIDE_ENABLE:
            build_id += '_de%d' % divide_enable
        if shifter_max_cycles != DEFAULT_SHIFTER_MAX_CYCLES:
            build_id += '_smc%d' % shifter_max_cycles
        if enable_exceptions != DEFAULT_ENABLE_EXCEPTIONS:
            build_id += '_ex%d' % enable_exceptions
        if pipeline_stages != DEFAULT_PIPELINE_STAGES:
            build_id += '_ps%d' % pipeline_stages
        if vcp_enable != DEFAULT_VCP_ENABLE:
            build_id += '_vcp%d' % vcp_enable
        if enable_ext_interrupts != DEFAULT_ENABLE_EXT_INTERRUPTS:
            build_id += '_int%d' % enable_ext_interrupts
        if num_ext_interrupts != DEFAULT_NUM_EXT_INTERRUPTS:
            build_id += '_%d' % num_ext_interrupts
        if power_optimized != DEFAULT_POWER_OPTIMIZED:
            build_id += '_po%d' % power_optimized
        if log2_burstlength != DEFAULT_LOG2_BURSTLENGTH:
            build_id += '_l2b%d' % log2_burstlength
        if axi_id_width != DEFAULT_AXI_ID_WIDTH:
            build_id += '_aid%d' % axi_id_width
        if aux_memory_regions != DEFAULT_AUX_MEMORY_REGIONS:
            build_id += '_amr%d' % aux_memory_regions
        if amr0_addr_base != DEFAULT_AMR0_ADDR_BASE:
            build_id += '_amrb%X' % amr0_addr_base
        if amr0_addr_last != DEFAULT_AMR0_ADDR_LAST:
            build_id += '_amrl%X' % amr0_addr_last
        if uc_memory_regions != DEFAULT_UC_MEMORY_REGIONS:
            build_id += '_umr%d' % uc_memory_regions
        if umr0_addr_base != DEFAULT_UMR0_ADDR_BASE:
            build_id += '_umrb%X' % umr0_addr_base
        if umr0_addr_last != DEFAULT_UMR0_ADDR_LAST:
            build_id += '_umrl%X' % umr0_addr_last
        if icache_size != DEFAULT_ICACHE_SIZE:
            build_id += '_ics%d' % icache_size
        if icache_line_size != DEFAULT_ICACHE_LINE_SIZE:
            build_id += '_icl%d' % icache_line_size
        if icache_external_width != DEFAULT_ICACHE_EXTERNAL_WIDTH:
            build_id += '_ice%d' % icache_external_width
        if instruction_request_register != DEFAULT_INSTRUCTION_REQUEST_REGISTER:
            build_id += '_irqr%d' % instruction_request_register
        if instruction_return_register != DEFAULT_INSTRUCTION_RETURN_REGISTER:
            build_id += '_irtr%d' % instruction_return_register
        if iuc_request_register != DEFAULT_IUC_REQUEST_REGISTER:
            build_id += '_iucrqr%d' % iuc_request_register
        if iuc_return_register != DEFAULT_IUC_RETURN_REGISTER:
            build_id += '_iucrtr%d' % iuc_return_register
        if iaux_request_register != DEFAULT_IAUX_REQUEST_REGISTER:
            build_id += '_iauxrqr%d' % iaux_request_register
        if iaux_return_register != DEFAULT_IAUX_RETURN_REGISTER:
            build_id += '_iauxrtr%d' % iaux_return_register
        if ic_request_register != DEFAULT_IC_REQUEST_REGISTER:
            build_id += '_icrqr%d' % ic_request_register
        if ic_return_register != DEFAULT_IC_RETURN_REGISTER:
            build_id += '_icrtr%d' % ic_return_register
        if dcache_size != DEFAULT_DCACHE_SIZE:
            build_id += '_dcs%d' % dcache_size
        if dcache_writeback != DEFAULT_DCACHE_WRITEBACK:
            build_id += '_dcw%d' % dcache_writeback
        if dcache_line_size != DEFAULT_DCACHE_LINE_SIZE:
            build_id += '_dcl%d' % dcache_line_size
        if dcache_external_width != DEFAULT_DCACHE_EXTERNAL_WIDTH:
            build_id += '_dce%d' % dcache_external_width
        if data_request_register != DEFAULT_DATA_REQUEST_REGISTER:
            build_id += '_drqr%d' % data_request_register
        if data_return_register != DEFAULT_DATA_RETURN_REGISTER:
            build_id += '_drtr%d' % data_return_register
        if duc_request_register != DEFAULT_DUC_REQUEST_REGISTER:
            build_id += '_ducrqr%d' % duc_request_register
        if duc_return_register != DEFAULT_DUC_RETURN_REGISTER:
            build_id += '_ducrtr%d' % duc_return_register
        if daux_request_register != DEFAULT_DAUX_REQUEST_REGISTER:
            build_id += '_dauxrqr%d' % daux_request_register
        if daux_return_register != DEFAULT_DAUX_RETURN_REGISTER:
            build_id += '_dauxrtr%d' % daux_return_register
        if dc_request_register != DEFAULT_DC_REQUEST_REGISTER:
            build_id += '_dcrqr%d' % dc_request_register
        if dc_return_register != DEFAULT_DC_RETURN_REGISTER:
            build_id += '_dcrtr%d' % dc_return_register

        super(Alt_ORCA_BuildCfg, self).__init__(\
              system=system,
              build_id=build_id,
              reset_vector=reset_vector,
              interrupt_vector=interrupt_vector,
              max_ifetches_in_flight=max_ifetches_in_flight,
              btb_entries=btb_entries,
              multiply_enable=multiply_enable,
              divide_enable=divide_enable,
              shifter_max_cycles=shifter_max_cycles,
              enable_exceptions=enable_exceptions,
              pipeline_stages=pipeline_stages,
              vcp_enable=vcp_enable,
              enable_ext_interrupts=enable_ext_interrupts,
              num_ext_interrupts=num_ext_interrupts,
              power_optimized=power_optimized,
              log2_burstlength=log2_burstlength,
              axi_id_width=axi_id_width,
              aux_memory_regions=aux_memory_regions,
              amr0_addr_base=amr0_addr_base,
              amr0_addr_last=amr0_addr_last,
              uc_memory_regions=uc_memory_regions,
              umr0_addr_base=umr0_addr_base,
              umr0_addr_last=umr0_addr_last,
              icache_size=icache_size,
              icache_line_size=icache_line_size,
              icache_external_width=icache_external_width,
              instruction_request_register=instruction_request_register,
              instruction_return_register=instruction_return_register,
              iuc_request_register=iuc_request_register,
              iuc_return_register=iuc_return_register,
              iaux_request_register=iaux_request_register,
              iaux_return_register=iaux_return_register,
              ic_request_register=ic_request_register,
              ic_return_register=ic_return_register,
              dcache_size=dcache_size,
              dcache_writeback=dcache_writeback,
              dcache_line_size=dcache_line_size,
              dcache_external_width=dcache_external_width,
              data_request_register=data_request_register,
              data_return_register=data_return_register,
              duc_request_register=duc_request_register,
              duc_return_register=duc_return_register,
              daux_request_register=daux_request_register,
              daux_return_register=daux_return_register,
              dc_request_register=dc_request_register,
              dc_return_register=dc_return_register,
              opt_sysid=opt_sysid,
              dstdir=dstdir,
              skip_sw_tests=skip_sw_tests,
              iterate_bsp_opt_flags=iterate_bsp_opt_flags,
              family='altera')

        # Request consumable resource quartus_license from GridEngine.
        self.use_quartus_lic = use_lic

        self.pgm_cable = pgm_cable

        self.qsf_opts = qsf_opts

        if self.qsf_opts:
            if self.qsf_opts.opt_id:
                self.build_id += '_' + self.qsf_opts.opt_id

    ######################################################################
    def setup_sw_build_dirs(self, sw_build_dirs, test_ignore_list):
        self.sw_build_dirs = \
            [Alt_ORCA_SWBuildDir(self, swbd, test_ignore_list) for swbd in sw_build_dirs]
        

    ######################################################################
    def setup_build(self, build_root, keep_existing=False,
                    recopy_software_dir=False, test_ignore_list=[],
                    sw_build_dirs=[], make_hw=True):

        self.dstdir = '%s/%s' % (build_root, self.build_id)

        self.setup_sw_build_dirs(sw_build_dirs, test_ignore_list)

        if keep_existing and os.path.isdir(self.dstdir):
            logging.info("Keeping existing build directory %s", self.dstdir)
            if recopy_software_dir:
                logging.info("But recopying software directory.")
                shutil.rmtree(self.dstdir+'/'+'software', ignore_errors=True)
                self.copy_software_dir()
                logging.info('Modifying RISC-V tests...')
                self.fix_rv_tests()
                self.create_compile_script(make_hw=False)
            return

        logging.info("Creating %s...", self.dstdir)

        shutil.rmtree(self.dstdir, ignore_errors=True)

        # Copy contents of systems/$(self.system) to dstdir.
        # (Could use symlinks for most of these files...)
        # Note: dstdir must not already exist!
        # Note: ignore the software directory, as that will be different
        # in this test suite than it is in the systems project.
        shutil.copytree('../systems'+'/'+self.system, self.dstdir,
            ignore=shutil.ignore_patterns('software', 'output_files', '*_system', 'db', 'incremental_db', '*~', '#*', '.#*'))

        # Symlink to the and scripts dir for all test builds.
        rel_symlink('../scripts', self.dstdir)

        # Create config.mk and program.mk
        cwd = os.getcwd()
        os.chdir(self.dstdir)

        f = open('config.mk', 'w')
        f.write('SYSTEM=%s\n' % self.system)
        f.write('OPTIONAL_SYSID=%s\n' % self.opt_sysid)
        f.write('RESET_VECTOR=%s\n' % self.reset_vector)
        f.write('INTERRUPT_VECTOR=%s\n' % self.interrupt_vector)
        f.write('MAX_IFETCHES_IN_FLIGHT=%s\n' % self.max_ifetches_in_flight)
        f.write('BTB_ENTRIES=%s\n' % self.btb_entries)
        f.write('MULTIPLY_ENABLE=%s\n' % self.multiply_enable)
        f.write('DIVIDE_ENABLE=%s\n' % self.divide_enable)
        f.write('SHIFTER_MAX_CYCLES=%s\n' % self.shifter_max_cycles)
        f.write('ENABLE_EXCEPTIONS=%s\n' % self.enable_exceptions)
        f.write('PIPELINE_STAGES=%s\n' % self.pipeline_stages)
        f.write('VCP_ENABLE=%s\n' % self.vcp_enable)
        f.write('ENABLE_EXT_INTERRUPTS=%s\n' % self.enable_ext_interrupts)
        f.write('NUM_EXT_INTERRUPTS=%s\n' % self.num_ext_interrupts)
        f.write('POWER_OPTIMIZED=%s\n' % self.power_optimized)
        f.write('LOG2_BURSTLENGTH=%s\n' % self.log2_burstlength)
        f.write('AXI_ID_WIDTH=%s\n' % self.axi_id_width)
        f.write('AUX_MEMORY_REGIONS=%s\n' % self.aux_memory_regions)
        f.write('AMR0_ADDR_BASE=%s\n' % self.amr0_addr_base)
        f.write('AMR0_ADDR_LAST=%s\n' % self.amr0_addr_last)
        f.write('UC_MEMORY_REGIONS=%s\n' % self.uc_memory_regions)
        f.write('UMR0_ADDR_BASE=%s\n' % self.umr0_addr_base)
        f.write('UMR0_ADDR_LAST=%s\n' % self.umr0_addr_last)
        f.write('ICACHE_SIZE=%s\n' % self.icache_size)
        f.write('ICACHE_LINE_SIZE=%s\n' % self.icache_line_size)
        f.write('ICACHE_EXTERNAL_WIDTH=%s\n' % self.icache_external_width)
        f.write('INSTRUCTION_REQUEST_REGISTER=%s\n' % self.instruction_request_register)
        f.write('INSTRUCTION_RETURN_REGISTER=%s\n' % self.instruction_return_register)
        f.write('IUC_REQUEST_REGISTER=%s\n' % self.iuc_request_register)
        f.write('IUC_RETURN_REGISTER=%s\n' % self.iuc_return_register)
        f.write('IAUX_REQUEST_REGISTER=%s\n' % self.iaux_request_register)
        f.write('IAUX_RETURN_REGISTER=%s\n' % self.iaux_return_register)
        f.write('IC_REQUEST_REGISTER=%s\n' % self.ic_request_register)
        f.write('IC_RETURN_REGISTER=%s\n' % self.ic_return_register)
        f.write('DCACHE_SIZE=%s\n' % self.dcache_size)
        f.write('DCACHE_WRITEBACK=%s\n' % self.dcache_writeback)
        f.write('DCACHE_LINE_SIZE=%s\n' % self.dcache_line_size)
        f.write('DCACHE_EXTERNAL_WIDTH=%s\n' % self.dcache_external_width)
        f.write('DATA_REQUEST_REGISTER=%s\n' % self.data_request_register)
        f.write('DATA_RETURN_REGISTER=%s\n' % self.data_return_register)
        f.write('DUC_REQUEST_REGISTER=%s\n' % self.duc_request_register)
        f.write('DUC_RETURN_REGISTER=%s\n' % self.duc_return_register)
        f.write('DAUX_REQUEST_REGISTER=%s\n' % self.daux_request_register)
        f.write('DAUX_RETURN_REGISTER=%s\n' % self.daux_return_register)
        f.write('DC_REQUEST_REGISTER=%s\n' % self.dc_request_register)
        f.write('DC_RETURN_REGISTER=%s\n' % self.dc_return_register)
        f.close()

        os.chdir(cwd)

        self.copy_software_dir()

        logging.info('Modifying RISC-V tests...')
        self.fix_rv_tests()

        self.create_compile_script(make_hw)

        if self.qsf_opts:
            self.munge_qsf()

    ###########################################################################
    def munge_qsf(self):
        cmd = "make vblox1.qsf"

        try:
            subprocess.check_call(shlex.split(cmd), cwd=self.dstdir)
        except subprocess.CalledProcessError, exc:
            logging.error("Error: returncode = %s from command %s",
                          exc.returncode, exc.cmd)

        qsf_file = self.dstdir + '/vblox1.qsf'

        # First override the values for options that are already in the QSF.
        patt_list = []
        for opt_name, opt_val in self.qsf_opts.opt_list:
            patt = '^\s*set_global_assignment\s+-name\s+%s\s+(.*)$' % opt_name
            repl = '# BUILD: OVERRIDE EXISTING SETTING: \\1\n'
            repl += 'set_global_assignment -name %s ' % opt_name
            # If there's a space in the opt_val string, must enclose in double quotes.
            if ' ' in opt_val:
                repl += '"%s"' % opt_val
            else:
                repl += opt_val
            patt_list.append((patt, repl))

        logging.info('Setting QSF options for %s', self.build_id)

        file_sub(qsf_file, patt_list)

        # Then append any options that are not already in the QSF.
        opt_found = {}
        re_list = []
        for i, opt_tuple in enumerate(self.qsf_opts.opt_list):
            opt_name = opt_tuple[0]
            patt = patt_list[i][0]
            re_list.append((opt_name, re.compile(patt)))
        f = open(qsf_file, 'r')
        for line in f:
            for opt_name, re_opt in re_list:
                if re_opt.match(line):
                    opt_found[opt_name] = True
        f.close()

        new_opts = False
        for opt_name, opt_val in self.qsf_opts.opt_list:
            if opt_name not in opt_found:
                new_opts = True

        if new_opts:
            f = open(qsf_file, 'a')
            s = '\n'
            s += '# BUILD: NEW SETTINGS\n'
            for opt_name, opt_val in self.qsf_opts.opt_list:
                if opt_name not in opt_found:
                    line = 'set_global_assignment -name %s ' % opt_name
                    if ' ' in opt_val:
                        line += '"%s"' % opt_val
                    else:
                        line += opt_val
                    s += line + '\n'
                    logging.info(line)
            f.write(s)
            f.close()

    ###########################################################################
    # Submit a job to GridEngine to run hardware and software compilation.
    def compile_all(self, use_qsub=True, qsub_qlist='main.q'):

        if use_qsub:
            logging.info("Submitting compile job %s", self.build_id)
        else:
            logging.info("Starting local compile of build %s", self.build_id)

        script_name = 'compile_all.sh'

        if use_qsub:
            qopt = ''
            if qsub_qlist:
                qopt += '-q %s' % qsub_qlist
            if self.use_quartus_lic:
                qopt += ' -l quartus_license=1'
            cmd = "qsub %s -m a -M %s -b y -shell n -sync y -j y -o log/qsub_compile_all_log -V "\
                "-cwd -N \"%s\" ./%s" % (qopt, git_user_email(), self.build_id, script_name)
            logging.info("qsub command: %s for %s",
                         cmd, self.build_id)
            args = shlex.split(cmd)
            self.subproc = subprocess.Popen(args, cwd=self.dstdir)
            # Job is submitted; exit this function without waiting for
            # job to finish.
        else:
            cmd = "./%s" % (script_name,)
            args = shlex.split(cmd)
            self.subproc = subprocess.Popen(args, cwd=self.dstdir)
            # Wait for child to finish:
            while 1:
                r = self.subproc.poll()
                # r is the same as self.subproc.returncode
                if r == None:
                    # Child process hasn't terminated yet.
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    time.sleep(5)
                else:
                    # Child process has terminated.
                    # sys.stdout.write('\n')
                    logging.info("compile_all: Subprocess %d of %s ended with code %d.",
                                 self.subproc.pid, self.build_id, r)
                    break

    ######################################################################
    # re_summary = regular expression for summary line
    def common_parse_rpt(self, rptfilename, re_summary):

        rptfile = self.dstdir+'/'+rptfilename

        try:
            f = open(rptfile, 'r')
        except IOError:
            logging.error("%s not found for build %s",
                          rptfilename, self.build_id)
            return ('?', '?', '?')

        num_errors = 0
        num_warnings = 0
        num_crit_warnings = 0
        summary_errors = 0
        summary_warnings = 0
        for line in f:
            m0 = QuartusLog.re_warning.match(line)
            m1 = QuartusLog.re_crit_warning.match(line)
            m2 = QuartusLog.re_error.match(line)
            m3 = re_summary.match(line)
            if m0:
                num_warnings += 1
            elif m1:
                num_warnings += 1
                num_crit_warnings += 1
            elif m2:
                num_errors += 1
            elif m3:
                summary_errors = int(m3.group(1))
                summary_warnings = int(m3.group(2))

        f.close()

        if summary_errors != num_errors:
            logging.error("%s summary errors (%d) != counted errors (%d)",
                          rptfilename, summary_errors, num_errors)
        if summary_warnings != num_warnings:
            logging.error("%s summary warnings (%d) != counted warnings (%d)",
                          rptfilename, summary_warnings, num_warnings)

        return (max(summary_errors, num_errors),
                num_crit_warnings,
                max(summary_warnings, num_warnings))

    ######################################################################
    def parse_map_rpt(self):

        (self.map_errors, self.map_crit_warnings, self.map_warnings) = \
            self.common_parse_rpt('output_files/orca_project.map.rpt',
                                  QuartusLog.re_map_summary)

    ######################################################################
    def parse_fit_rpt(self):

        (self.fit_errors, self.fit_crit_warnings, self.fit_warnings) = \
            self.common_parse_rpt('output_files/orca_project.fit.rpt',
                                  QuartusLog.re_fit_summary)

        # XXX TODO: get resource utilization from fit.rpt, e.g.
        # ; Fitter Resource Utilization by Entity
        #
        # ; Compilation Hierarchy Node ; Combinational ALUTs ; Memory ALUTs ;
        # LUT_REGs ; ALMs ; Dedicated Logic Registers ; I/O Registers ;
        # Block Memory Bits ; M9Ks ; M144Ks ; DSP 18-bit Elements ;
        # DSP 9x9 ; DSP 12x12 ; DSP 18x18 ; DSP 36x36 ;
        # Pins ; Virtual Pins ;
        # Combinational with no register ALUT/register pair ;
        # Register-Only ALUT/register pair ;
        # Combinational with a register ALUT/register pair ;
        # Full Hierarchy Name
        #
        # ; |vblox1_vbx1:vbx1| ; 13588 (0) ; 292 (0) ; 0 (0) ;
        # 12453 (0) ; 11223 (0) ; 0 (0) ; 593056 ; 70   ; 0 ; 64 ; 16 ;
        # 0 ; 8 ; 8 ; 0 ; 0 ; 7462 (0) ; 4835 (0) ; 6430 (0) ;
        # |fpga|vblox1:vblox1_inst|vblox1_vbx1:vbx1

    ######################################################################
    def parse_asm_rpt(self):

        (self.asm_errors, self.asm_crit_warnings, self.asm_warnings) = \
            self.common_parse_rpt('output_files/orca_project.asm.rpt',
                                  QuartusLog.re_asm_summary)

    ######################################################################
    def parse_sta_rpt(self):

        (self.sta_errors, self.sta_crit_warnings, self.sta_warnings) = \
            self.common_parse_rpt('output_files/orca_project.sta.rpt',
                                  QuartusLog.re_sta_summary)
        self.sta_crit_warnings += self.sta_errors
        self.sta_errors = 0

    ######################################################################
    def parse_sta_summary(self):
        rptfile = self.dstdir+'/output_files/orca_project.sta.summary'
        try:
            f = open(rptfile, 'r')
        except IOError:
            logging.error("No sta.summary found for build %s", self.build_id)
            return

        # sta_dict[corner][timing_check_type] =
        #   list of (clock_domain, slack, TNS) results.

        # "Default" Corners:
        # Slow 1200mV 85C
        # Slow 1200mV 0C
        # Fast 1200mV 0C

        # Cyclone V uses:
        # Slow 1100mV 85C
        # Slow 1100mV 0C
        # Fast 1100mV 0C

        S_GET_TYPE  = 0
        S_GET_SLACK = 1
        S_GET_TNS   = 2

        sta_dict = {}

        state = S_GET_TYPE
        for line in f:
            if state == S_GET_TYPE:
                m = QuartusLog.re_sta_type.match(line)
                if m:
                    corner = m.group(1)
                    check_type = m.group(2)
                    clock = m.group(3)
                    state = S_GET_SLACK
            elif state == S_GET_SLACK:
                m = QuartusLog.re_sta_slack.match(line)
                if m:
                    slack = float(m.group(1))
                    state = S_GET_TNS
            elif state == S_GET_TNS:
                m = QuartusLog.re_sta_tns.match(line)
                if m:
                    tns = float(m.group(1))
                    r = STA_Result(corner, check_type, clock, slack, tns)
                    if corner in sta_dict:
                        if check_type in sta_dict[corner]:
                            sta_dict[corner][check_type].append(r)
                        else:
                            sta_dict[corner][check_type] = [r]
                    else:
                        sta_dict[corner] = {check_type : [r]}
                    state = S_GET_TYPE

        self.sta_dict = sta_dict

        self.sta_corners = sta_dict.keys()
        self.sta_corners.sort()

        f.close()

    ######################################################################
    def parse_sta_fmax(self):
        #Default if something fails
        self.fmax = 'ERROR'

        rptfile = self.dstdir+'/output_files/orca_project.sta.rpt'
        try:
            f = open(rptfile, 'r')
        except IOError:
            logging.error("No sta.summary found for build %s", self.build_id)
            self.fmax = '?'
            return

        STATE_LOOK_FOR_FMAX = 0
        STATE_PASS_LINE = 1
        STATE_GET_FMAX = 2

        state = STATE_LOOK_FOR_FMAX

        re_look_for_fmax = re.compile(r'; Restricted Fmax ;')
        re_get_fmax = re.compile(r'; (\d+\.\d+) MHz ; (\d+\.\d+) MHz')

        fmax = '?'
        restricted_fmax = '?'

        for line in f:
            if state == STATE_LOOK_FOR_FMAX:
                if re_look_for_fmax.search(line):
                    state = STATE_PASS_LINE

            elif state == STATE_PASS_LINE:
                # Skip one line.
                state = STATE_GET_FMAX

            elif state == STATE_GET_FMAX:
                match = re_get_fmax.search(line)
                if match:
                    temp1 = float(match.group(1))
                    temp2 = float(match.group(2)) 
                    if fmax == '?' or (temp1 < fmax):
                        fmax = temp1
                    if restricted_fmax == '?' or (temp2 < restricted_fmax):
                        restricted_fmax = temp2

        if (fmax == '?') or (restricted_fmax == '?'):
            logging.error('Error: parse_sta_fmax: Not able to parse fmax from STA.')
            self.fmax = '?'
        else:
            if fmax != restricted_fmax:
                logging.info('parse_sta_fmax: There is a discrepancy between FMAX and Restricted FMAX.')
                logging.info('Please check the project to see if the correct chip was selected.')
                logging.info('If it is the correct chip, consider a faster or larger chip for this design.')
            
            self.fmax = restricted_fmax * 1e6
        

    ######################################################################
    def print_sta_summary(self):
        # Summarize if there are any timing violations in each corner,
        # return worst slack per corner.
        #
        # Provide a separate summary that ignores removal violations in
        # altera_reserved_tck domain.

        def f_worst_slack(result_list):
            return reduce(lambda x, y: x if (x.slack < y.slack) else y,
                          result_list)

        worst_slack = {}
        worst_slack_filt1 = {}
        worst_slack_filt2 = {}

        filt1_clk = 'altera_reserved_tck'
        filt2_clk = \
            'uCCD2RGB|upixclk_pll|altpll_component|auto_generated|pll1|clk[0]'

        for c in self.sta_corners:
            # All STA_Results for this corner
            all_results = reduce(lambda x, y: x+y, self.sta_dict[c].values())
            worst_slack[c] = f_worst_slack(all_results)

            # remove removal violations in altera_reserved_tck domain
            filt1_results = [x for x in all_results if \
                               not ((x.check_type == 'Removal') and
                                    (x.clock == 'altera_reserved_tck'))]
            worst_slack_filt1[c] = f_worst_slack(filt1_results)
            # remove recovery violations for
            # CCD2RGB|upixclk_pll|altpll_component|auto_generated|pll1|clk[0]
            filt2_results = [x for x in filt1_results if \
                               not ((x.check_type == 'Recovery') and
                                    (x.clock == filt2_clk))]
            worst_slack_filt2[c] = f_worst_slack(filt2_results)

        for c in self.sta_corners:
            w = worst_slack[c]
            logging.info("%s: worst slack = %f, %s, %s",
                         c, w.slack, w.check_type, w.clock)

        logging.info("Ignoring altera_reserved_tck removal violations:")
        for c in self.sta_corners:
            w = worst_slack_filt1[c]
            logging.info("%s: worst slack = %f, %s, %s",
                         c, w.slack, w.check_type, w.clock)

        logging.info("Ignoring filt2 violations:")
        for c in self.sta_corners:
            w = worst_slack_filt2[c]
            logging.info("%s: worst slack = %f, %s, %s",
                         c, w.slack, w.check_type, w.clock)

        self.worst_slack = worst_slack
        self.worst_slack_filt1 = worst_slack_filt1
        self.worst_slack_filt2 = worst_slack_filt2

    ######################################################################
    # gets hw_compile_time.
    def parse_flow_rpt(self):

        self.hw_compile_time = '?'

        rptfile = self.dstdir+'/output_files/orca_project.flow.rpt'

        try:
            f = open(rptfile, 'r')
        except IOError:
            logging.error("No flow.rpt found for build %s", self.build_id)
            return

        for line in f:
            m = QuartusLog.re_flow_time.match(line)
            if m:
                # Note: kept as a string, not converted to time
                self.hw_compile_time = m.group(1)
                break

        f.close()

    ######################################################################
    def parse_resource_rpt(self):
    # Check "Fitter Resource Utilization by Entity"
        resource_rpt = self.dstdir + '/output_files/orca_project.fit.rpt'
        self.logic_cells = '?'
        self.logic_registers = '?'
        self.m9ks = '?'
        self.dsp_9x9 = '?'
        self.dsp_18x18 = '?'

        re_orca_resource = re.compile(r'\|orca:[^\|]*\|\s+; (\d+) .+ ; (\d+) .+ ; .+ ; .+ ; (\d+) .+; .+ ; (\d+) .+ ; (\d+) .+ ;')
        try:
            resource_file = open(resource_rpt, 'r')
        except IOError:
            logging.error("No orca_project.fit.rpt found for build %s", self.build_id)
            return
        resource_text = resource_file.read()
        resource_file.close()

        for line in resource_text.split('\n'):
            resource_match = re_orca_resource.search(line)
            if resource_match:
                self.logic_cells = resource_match.group(1)
                self.logic_registers = resource_match.group(2)
                self.m9ks = resource_match.group(3)
                self.dsp_9x9 = resource_match.group(4)
                self.dsp_18x18 = resource_match.group(5)

    ######################################################################
    def check_compile_hw_logs(self):
        logging.info("Checking hardware compilation logs for %s",
                     self.build_id)

        self.parse_hw_make_log()

        self.parse_map_rpt()
        self.parse_fit_rpt()
        self.parse_asm_rpt()
        self.parse_sta_rpt()
        self.parse_sta_summary()
        self.parse_sta_fmax()
        self.parse_resource_rpt()
        # get hw_compile_time
        self.parse_flow_rpt()

    ######################################################################
    def parse_bsp_log(self):
        logfile = self.dstdir+'/log/bsp_compile_log'
        try:
            f = open(logfile, 'r')
        except IOError:
            logging.error("No bsp compile log found for build %s",
                          self.build_id)
            self.bsp_warnings = '?'
            self.bsp_errors = '?'
            return

        self.bsp_warnings = 0
        self.bsp_errors = 0
        s = f.readline()
        while s:
            m0 = QuartusLog.re_bsp_gen_err.match(s)
            m1 = ErrWarnMsg.re_gcc_msg.match(s)
            m2 = ErrWarnMsg.re_make_err.match(s)
            if m0:
                self.bsp_errors += 1
            elif m1:
                if m1.group(3) == 'warning':
                    self.bsp_warnings += 1
                elif m1.group(3) == 'error':
                    self.bsp_errors += 1
            elif m2:
                self.bsp_errors += 1
            s = f.readline()
        f.close()

    ######################################################################
    def download_sof(self, pgm_cable=''):
        logging.info("Downloading SOF for %s", self.build_id)
        logging.info("Dest dir: %s", self.dstdir)

        # cmd = "make pgm"
        # With make, get "make: *** [pgm] Terminated" message on termination,
        # so calling quartus_pgm directly.
        cable_opt = ''
        if pgm_cable:
            cable_opt = '--cable "%s"' % (pgm_cable,)
        # If a non-time-limited SOF is available, use it instead.
        if os.path.exists(self.dstdir+'/orca_project.sof'):
            sof_file = 'orca_project.sof'
        else:
            print 'Error: .sof file missing.'

        #Kill any nios2-terminal processes owned by the user that may be hogging the JTAG bus.
        #This is overkill and should get fixed to selectively kill only a process that's actually
        #using the board we need.
        killall_terms_returncode = subprocess.call('killall nios2-terminal', shell=True)
        if not killall_terms_returncode:
            logging.info("Warning, killed a nios2-terminal process before programming .sof", self.dstdir)

        # Configure will work.
        jtagd_output = subprocess.check_output('jtagd', stderr=subprocess.STDOUT)
        cmd = 'jtagconfig'
        tries_left = 2

        while 1:
            try:
                jtag_config_output = subprocess.check_output(cmd, 
                    stderr=subprocess.STDOUT) 
            except subprocess.CalledProcessError as e:
                jtag_config_output = e.output

            logging.info(jtag_config_output)

            if re.match(r'No JTAG', jtag_config_output):
                logging.info('No JTAG connected, reconnect and press enter to try again.')

                try:
                    raw_input()
                except e:
                    pass

            elif re.search(r'\s[0-9A-Z]{8}\s', jtag_config_output):
                logging.info('JTAG configuration successful.')
                break

            elif re.search(r'\sUnable', jtag_config_output): 
                if tries_left == 0:
                    logging.info('Cannot connect to JTAG, reconnect and press enter to try again.')
                    try:
                        raw_input()
                    except e:
                        pass
                else:
                    logging.info('Attempting to reset JTAG, {} tries remaining.'.format(tries_left))
                    s = r"ps aux | grep '[0-9] jtagd' | sed -r 's/^[a-z]*\s*([0-9]+).*[0-9] jtagd/\1/'"
                    pid = re.findall('[0-9]+', subprocess.check_output(s, shell=True))[0]
                    subprocess.Popen('kill -9 {}'.format(pid), shell=True).wait()
                    jtagd_output = subprocess.check_output('jtagd', stderr=subprocess.STDOUT)
                    tries_left -= 1

        cmd = 'quartus_pgm %s -m JTAG -o P;%s' % (cable_opt, sof_file)
        # print cmd
        self.subproc = subprocess.Popen(shlex.split(cmd), cwd=self.dstdir,
                                        stdout=subprocess.PIPE)

        # Must wait until device is programmed.
        # Look for message on stdout.
        # Search for e.g.
        # Info (209011): Successfully performed operation(s)
        # Info (209061): Ended Programmer operation at

        # If another instance of quartus_pgm is already running, will get:
        # Error (209042): Application SLD HUB CLIENT on 127.0.0.1 is using
        #                       the target device
        # Error (209012): Operation failed
        # Info (209061): Ended Programmer operation at

        error = 0
        f = self.subproc.stdout
        line = f.readline()
        while line:
            logging.info(line.strip())
            if line.startswith('Error (209012): Operation failed'):
                error = 1
                break
            elif line.startswith('Info (209061): Ended Programmer operation at'):
                break
            line = f.readline()
        f.close()

        if error:
            logging.error("ERROR: quartus_pgm failed!")
            logging.info("There might be another instance of quartus_pgm "
                         "running.")

        return error

    ######################################################################
    def stop_sof(self):
        # quartus_pgm terminates immediately in the case of a
        # non-time-limited SOF, so it might not be necessary to stop it.
        r = self.subproc.poll()
        if r == None:
            logging.info("Stopping quartus_pgm for %s", self.build_id)
            self.subproc.terminate()
            self.subproc.wait()

    ######################################################################
    def run_sw_tests(self, keep_existing=False, force_test_rerun=False,
                     pgm_cable='', timeout=0, msg_interval=5*60):

        if self.skip_sw_tests:
            logging.info("Skipping SW tests for %s", self.build_id)
            return
        
        logging.info('Programming .sof file...')

        if self.pgm_cable:
            pgm_cable = self.pgm_cable

        pgm_error = self.download_sof(pgm_cable)

        if pgm_error:
            self.stop_sof()
            return

        logging.info("Running SW tests for %s", self.build_id)

        # Iterate over the list of software tests.
        # For each one, first open the nios2-terminal.
        # Next, convert it to a bin file, then program over
        # JTAG.
        saved_working_dir = os.getcwd()
        os.chdir(self.dstdir)
        for swbd in self.sw_build_dirs:
            for t in swbd.test_list:
                test_elf = 'software/'+swbd.name+'/'\
                    +t.test_dir+'/'+t.elf_name
                # Convert the elf into a temp .bin file to write over JTAG.
                cmd = 'riscv32-unknown-elf-objcopy -O binary {} {}'\
                    .format(test_elf, 'test.bin')
                self.subproc = subprocess.Popen(cmd, shell=True)

                while 1:
                    r = self.subproc.poll()
                    # r is the same as self.subproc.returncode
                    if r == None:
                        # Child process hasn't terminated yet.
                        sys.stdout.write('.')
                        sys.stdout.flush()
                        time.sleep(5)
                    else:
                        # Child process has terminated.
                        # sys.stdout.write('\n')
                        logging.info("Running Test {}...".format(t.name))
                        break

                t.run(keep_existing, force_test_rerun, pgm_cable,
                      timeout, msg_interval)

        os.chdir(saved_working_dir)
        self.stop_sof()

##########################################################################
class Alt_ORCA_SWBuildDir(ORCA_SWBuildDir):
    def create_tests(self, test_list_cleaned):
        self.test_list = \
            [Alt_ORCA_SWTest(self.build_cfg, self, t) for t in test_list_cleaned] 

##########################################################################
class Alt_ORCA_SWTest(ORCA_SWTest):

    ######################################################################
    # Return -1 if nios2-download or nios2-terminal failed, to indicate
    # test can be retried.
    def run(self, keep_existing=False, force_test_rerun=False,
            pgm_cable='', timeout=0, msg_interval=60*5):

        test_dir = self.build_cfg.dstdir + '/software/' + self.build_dir.name \
        + '/' + self.test_dir
        output_log = test_dir+'/log/output_log'
        download_log = test_dir+'/log/download_log'
        run_time_log = test_dir+'/log/run_time'

        elf_file = test_dir + '/' + self.elf_name 

        if keep_existing and not force_test_rerun:
            # only re-run a test if:
            # - output.log doesn't exist,
            # - output.log is older than .elf,
            # - output.log has unknown pass/fail status.
            run_test = False
            if not os.path.exists(output_log):
                logging.info("%s: output log does not exist; will re-run "
                             "(build %s)", self.name, self.build_cfg.build_id)
                run_test = True
            elif os.path.exists(elf_file) and \
                    (os.path.getmtime(output_log) < \
                         os.path.getmtime(elf_file)):
                logging.info("%s: output log is older then ELF; will re-run "
                             "(build %s)", self.name, self.build_cfg.build_id)
                run_test = True
            else:
                self.parse_output_log(quiet=False)
                if self.run_errors == '?':
                    logging.info("%s: pass/fail status not found in output "
                                 "log; will re-run (build %s)", self.name,
                                 self.build_cfg.build_id)
                    run_test = True
            if not run_test:
                logging.info("%s: Not re-running as output log appears to be "
                             "up-to-date (build %s)", self.name,
                             self.build_cfg.build_id)
                return 0

        if self.run_count == 0:
            for patt in [download_log,
                         output_log,
                         output_log+'.try*',
                         run_time_log]:
                for f in glob.glob(patt):
                    os.remove(f)

        self.run_count += 1

        logging.info('\n======================================================================\n')
        logging.info('Running test %s for %s', self.name,
                     self.build_cfg.build_id)
        logging.info('\n======================================================================\n')

        self.build_cfg.download_sof(self.build_cfg.pgm_cable)

        cmd = 'date +"%s" > %s' % (DATE_FMT, run_time_log)
        subprocess.check_call(cmd, shell=True)

        # check for existence of ELF.
        if not os.path.exists(elf_file):
            f = open(download_log, 'w')
            logging.error('Error: ELF file does not exist: %s', elf_file)
            f.write('Error: ELF file does not exist: %s\n' % elf_file)
            f.close()
            return 0
        
        cable_opt = ''
        if pgm_cable:
            cable_opt = '--cable "%s"' % (pgm_cable,)

        ## Merge stderr with stdout and redirect stdout to file.
        # It is assumed that the test program will output Ctrl-D when it is
        # finished, causing nios2-terminal to quit.
        #
        # f = open(output_log, 'w')
        # cmd = "nios2-terminal"
        # subprocess.check_call(shlex.split(cmd),
        #                       stdout=f,
        #                       stderr=subprocess.STDOUT)
        # f.close()

        # We want terminal output to be displayed on screen as well, but
        # there's no tee-like functionality built into the Python std library.

        # Use shell and tee instead. This redirects nios2-terminal's
        # stderr and stdout to the same file:
        nios2_terminal_cmd = "set -o pipefail; nios2-terminal %s 2>&1 | tee %s" % \
            (cable_opt, output_log)

        # Attach a session id to shell process so entire process group
        # (shell and child processes) can be killed with one PGID
        # (e.g. in the event of a timeout).
        nios2_terminal_process = subprocess.Popen(nios2_terminal_cmd, shell=True, preexec_fn=os.setsid)

        logging.info("nios2-terminal started in PGID %d.", nios2_terminal_process.pid)
        logging.info("If you need to stop the test, use 'kill -- -%d'.", nios2_terminal_process.pid)

        # Program the .bin file to the device.
        run_cmd = 'BIN_FILE=NONE make -C {} run'.format(self.build_cfg.dstdir)
        subprocess.check_call(run_cmd, shell=True)
        
        start_time = time.time()
        last_msg_time = start_time
        killed_on_timeout = False
        tries_remaining = 2
        while True:
            time.sleep(3)
            r = nios2_terminal_process.poll()
            if r != None:
                if r != 0:
                    logging.error('ERROR: nios2-terminal parent process '
                                  'exited with return code %s.', r)
                    f = open(output_log, 'a')
                    if killed_on_timeout:
                        tries_remaining -= 1
                        f.write('\nERROR: nios2-terminal parent process was '
                                'killed due to timeout and exited with '
                                'return code %s.\n' % r)
                        
                        if tries_remaining == 0:
                            break
                        else:
                            logging.info('Rebuilding bitstream.')
                            logging.info('{} tries left.'.format(tries_remaining))
                            self.build_cfg.download_sof(self.build_cfg.pgm_cable)
                            logging.info('Reprogramming over JTAG.')
                            nios2_terminal_process = subprocess.Popen(nios2_terminal_cmd, shell=True, preexec_fn=os.setsid)
                            subprocess.check_call(run_cmd, shell=True)
                    else:
                        # Something's wrong with nios2-terminal, not the bitstream.
                        f.write('\nERROR: nios2-terminal parent process '
                                'exited with return code %s.\n' % r)
                        break

                    f.close()

                else:
                    break
            else:
                current_time = time.time()
                elapsed_time = current_time - start_time
                elapsed_str = timedelta_str(\
                    datetime.timedelta(seconds=elapsed_time))

                if timeout and (elapsed_time > timeout):
                    logging.error("Timeout has expired after %s!",
                                  elapsed_str)
                    logging.info("Sending SIGTERM to process group %d...",
                                 nios2_terminal_process.pid)
                    os.killpg(nios2_terminal_process.pid, signal.SIGTERM)
                    killed_on_timeout = True

                elif (current_time - last_msg_time > msg_interval):
                    logging.info("Test has been running for %s. "
                                 "To stop test, use 'kill -- -%d'.",
                                 elapsed_str, nios2_terminal_process.pid)
                    last_msg_time = current_time

        cmd = 'date +"%s" >> %s' % (DATE_FMT, run_time_log)
        subprocess.check_call(cmd, shell=True)

        # XXX
        # Occasionally nios2-terminal will exit with return code 0 and
        # the message:
        # "nios2-terminal: exiting due to I/O error communicating with target"
        # (Normal message is "nios2-terminal: exiting due to ^D on remote".)
        # Need to grep output_log for this message and return -1 (to force
        # a retry) if this happens.

        if ((r == 0) and not self.check_for_io_error()) or r == -15:
            # r = -15 means nios2-terminal was likely killed on timeout;
            # so don't allow test to be retried
            return 0
        else:
            return -1

    ######################################################################
    def check_for_io_error(self):

        msg = 'nios2-terminal: ' \
            'exiting due to I/O error communicating with target'

        logfile = self.build_cfg.dstdir + '/software/' + self.build_dir.name + \
            '/' + self.test_dir + '/log/output_log'
        logging.info('check_for_io_error: logfile={}'.format(logfile))
        try:
            f = open(logfile, 'r')
        except IOError:
            logging.error("No output log found for test %s, build %s",
                          self.name, self.build_cfg.build_id)
            # If output_log doesn't exist, don't treat it as
            # nios2-terminal I/O error.
            return False

        got_io_error = False
        for line in f:
            if line.startswith(msg):
                got_io_error = True
                logging.error('ERROR: nios2-terminal exited due to I/O error')
                break
        f.close()

        return got_io_error

###########################################################################
