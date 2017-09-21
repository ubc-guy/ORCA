library IEEE;
use IEEE.STD_LOGIC_1164.all;
use IEEE.NUMERIC_STD.all;
use IEEE.std_logic_textio.all;          -- I/O for logic types

library work;
use work.rv_components.all;
use work.utils.all;
use work.constants_pkg.all;

library STD;
use STD.textio.all;                     -- basic I/O

entity execute is
  generic(
    REGISTER_SIZE       : positive;
    SIGN_EXTENSION_SIZE : positive;
    INTERRUPT_VECTOR    : std_logic_vector(31 downto 0);
    POWER_OPTIMIZED     : boolean;
    MULTIPLY_ENABLE     : boolean;
    DIVIDE_ENABLE       : boolean;
    SHIFTER_MAX_CYCLES  : natural;
    COUNTER_LENGTH      : natural;
    ENABLE_EXCEPTIONS   : boolean;
    LVE_ENABLE          : natural;
    SCRATCHPAD_SIZE     : integer;
    FAMILY              : string
    );
  port(
    clk            : in std_logic;
    scratchpad_clk : in std_logic;
    reset          : in std_logic;
    valid_input    : in std_logic;

    br_taken_in  : in std_logic;
    pc_current   : in std_logic_vector(REGISTER_SIZE-1 downto 0);
    instruction  : in std_logic_vector(INSTRUCTION_SIZE-1 downto 0);
    subseq_instr : in std_logic_vector(INSTRUCTION_SIZE-1 downto 0);
    subseq_valid : in std_logic;

    rs1_data       : in std_logic_vector(REGISTER_SIZE-1 downto 0);
    rs2_data       : in std_logic_vector(REGISTER_SIZE-1 downto 0);
    sign_extension : in std_logic_vector(SIGN_EXTENSION_SIZE-1 downto 0);

    wb_sel    : buffer std_logic_vector(REGISTER_NAME_SIZE-1 downto 0);
    wb_data   : buffer std_logic_vector(REGISTER_SIZE-1 downto 0);
    wb_enable : buffer std_logic;

    branch_pred        : out    std_logic_vector((REGISTER_SIZE*2)+3-1 downto 0);
    stall_from_execute : buffer std_logic;

    --Data Orca-internal memory-mapped master
    lsu_oimm_address       : out    std_logic_vector(REGISTER_SIZE-1 downto 0);
    lsu_oimm_byteenable    : out    std_logic_vector((REGISTER_SIZE/8)-1 downto 0);
    lsu_oimm_requestvalid  : buffer std_logic;
    lsu_oimm_readnotwrite  : buffer std_logic;
    lsu_oimm_writedata     : out    std_logic_vector(REGISTER_SIZE-1 downto 0);
    lsu_oimm_readdata      : in     std_logic_vector(REGISTER_SIZE-1 downto 0);
    lsu_oimm_readdatavalid : in     std_logic;
    lsu_oimm_waitrequest   : in     std_logic;

    --Scratchpad memory-mapped slave
    sp_address   : in  std_logic_vector(log2(SCRATCHPAD_SIZE)-1 downto 0);
    sp_byte_en   : in  std_logic_vector((REGISTER_SIZE/8)-1 downto 0);
    sp_write_en  : in  std_logic;
    sp_read_en   : in  std_logic;
    sp_writedata : in  std_logic_vector(REGISTER_SIZE-1 downto 0);
    sp_readdata  : out std_logic_vector(REGISTER_SIZE-1 downto 0);
    sp_ack       : out std_logic;

    external_interrupts : in     std_logic_vector(REGISTER_SIZE-1 downto 0);
    pipeline_empty      : in     std_logic;
    ifetch_next_pc      : in     std_logic_vector(REGISTER_SIZE-1 downto 0);
    fetch_in_flight     : in     std_logic;
    interrupt_pending   : buffer std_logic
    );
end entity execute;

architecture behavioural of execute is
  alias rd is instruction (REGISTER_RD'range);
  alias rs1 is instruction(REGISTER_RS1'range);
  alias rs2 is instruction(REGISTER_RS2'range);
  alias opcode is instruction(MAJOR_OP'range);

  signal predict_corr    : std_logic_vector(REGISTER_SIZE-1 downto 0);
  signal predict_corr_en : std_logic;

  signal stall_to_execute   : std_logic;
  signal stall_from_syscall : std_logic;


  -- various writeback sources
  signal br_data_out  : std_logic_vector(REGISTER_SIZE-1 downto 0);
  signal alu_data_out : std_logic_vector(REGISTER_SIZE-1 downto 0);
  signal ld_data_out  : std_logic_vector(REGISTER_SIZE-1 downto 0);
  signal sys_data_out : std_logic_vector(REGISTER_SIZE-1 downto 0);

  signal br_data_enable     : std_logic;
  signal alu_data_out_valid : std_logic;
  signal ld_data_enable     : std_logic;
  signal sys_data_enable    : std_logic;
  signal less_than          : std_logic;
  signal wb_mux             : std_logic_vector(1 downto 0);

  signal stall_from_alu : std_logic;

  signal br_bad_predict : std_logic;
  signal br_new_pc      : std_logic_vector(REGISTER_SIZE-1 downto 0);

  signal predict_pc     : std_logic_vector(REGISTER_SIZE-1 downto 0);
  signal syscall_en     : std_logic;
  signal syscall_target : std_logic_vector(REGISTER_SIZE-1 downto 0);

  signal rs1_data_fwd : std_logic_vector(REGISTER_SIZE-1 downto 0);
  signal rs2_data_fwd : std_logic_vector(REGISTER_SIZE-1 downto 0);

  signal alu_rs1_data : std_logic_vector(REGISTER_SIZE-1 downto 0);
  signal alu_rs2_data : std_logic_vector(REGISTER_SIZE-1 downto 0);

  signal writeback_stall_from_lsu : std_logic;
  signal stall_from_lsu           : std_logic;

  signal fwd_sel     : std_logic_vector(REGISTER_NAME_SIZE-1 downto 0);
  signal fwd_data    : std_logic_vector(REGISTER_SIZE-1 downto 0);
  signal fwd_en      : std_logic;
  signal fwd_mux     : std_logic;
  signal no_fwd_path : std_logic;

  signal lve_executing        : std_logic;
  signal lve_alu_data1        : std_logic_vector(REGISTER_SIZE-1 downto 0);
  signal lve_alu_data2        : std_logic_vector(REGISTER_SIZE-1 downto 0);
  signal lve_alu_source_valid : std_logic;

  signal valid_instr : std_logic;
  signal wb_valid    : std_logic;

  constant R_ZERO : std_logic_vector(REGISTER_NAME_SIZE-1 downto 0) := (others => '0');

  type fwd_mux_t is (ALU_FWD, NO_FWD);
  signal rs1_mux : fwd_mux_t;
  signal rs2_mux : fwd_mux_t;

  signal finished_instr : std_logic;

  signal entire_pipeline_empty : std_logic;
  signal is_branch             : std_logic;
  signal br_taken_out          : std_logic;

  alias subseq_rs1 : std_logic_vector(REGISTER_NAME_SIZE-1 downto 0) is subseq_instr(19 downto 15);
  alias subseq_rs2 : std_logic_vector(REGISTER_NAME_SIZE-1 downto 0) is subseq_instr(24 downto 20);

  signal use_after_produce_stall : std_logic;

  signal simd_op_size : std_logic_vector(1 downto 0);
begin
  --These stalls happen during the writeback cycle
  stall_to_execute <= use_after_produce_stall or writeback_stall_from_lsu;
  valid_instr      <= valid_input and (not stall_to_execute);
  -----------------------------------------------------------------------------
  -- REGISTER FORWADING
  -- Knowing the next instruction coming downt the pipeline, we can
  -- generate the mux select bits for the next cycle.
  -- there are several functional units that could generate a writeback. ALU,
  -- JAL, Syscalls, load_store. the Alu forward directly to the next
  -- instruction, The others stall the pipeline to wait for the registers to
  -- propogate if the next instruction uses them.
  --
  -----------------------------------------------------------------------------
  with rs1_mux select
    rs1_data_fwd <=
    alu_data_out when ALU_FWD,
    rs1_data     when others;
  with rs2_mux select
    rs2_data_fwd <=
    alu_data_out when ALU_FWD,
    rs2_data     when others;



  alu_rs1_data <= rs1_data_fwd when LVE_ENABLE = 0 else
                  lve_alu_data1 when lve_alu_source_valid = '1' else
                  alu_data_out  when rs1_mux = ALU_FWD else rs1_data;
  alu_rs2_data <= rs2_data_fwd when LVE_ENABLE = 0 else
                  lve_alu_data2 when lve_alu_source_valid = '1' else
                  alu_data_out  when rs2_mux = ALU_FWD else rs2_data;



  -------------------------------------------------------------------------------
  -- This process is useful for finding bugs in simulation
  -------------------------------------------------------------------------------
  process(clk)
  begin
    if rising_edge(clk) then
      if reset = '0' then
        assert (bool_to_int(sys_data_enable) +
                bool_to_int(ld_data_enable) +
                bool_to_int(br_data_enable) +
                bool_to_int(alu_data_out_valid)) <= 1 and reset = '0' report "Multiple Data Enables Asserted" severity failure;
      end if;
    end if;
  end process;

  wb_mux <= "00" when sys_data_enable = '1' else
            "01" when ld_data_enable = '1' else
            "10" when br_data_enable = '1' else
            "11";                       --when alu_data_out_valid = '1'

  with wb_mux select
    wb_data <=
    sys_data_out when "00",
    ld_data_out  when "01",
    br_data_out  when "10",
    alu_data_out when others;

  wb_valid <= (sys_data_enable or
               ld_data_enable or
               br_data_enable or
               (alu_data_out_valid and (not lve_executing)));
  wb_enable <= wb_valid when wb_sel /= R_ZERO else '0';

  fwd_data <= sys_data_out when sys_data_enable = '1' else
              alu_data_out when alu_data_out_valid = '1' else
              br_data_out;

  stall_from_execute <= valid_input and (stall_to_execute or
                                         stall_from_lsu or
                                         stall_from_alu or
                                         lve_executing or
                                         stall_from_syscall);

  use_after_produce_stall <= wb_valid and no_fwd_path when wb_sel = rs1 or wb_sel = rs2 else '0';

  process(clk)
  begin
    if rising_edge(clk) then
      if stall_to_execute = '0' then
        rs1_mux     <= NO_FWD;
        rs2_mux     <= NO_FWD;
        wb_sel      <= rd;
        no_fwd_path <= '0';
        if valid_instr = '1' then
          --load, csr_read, jal[r] are the only instructions that writeback but
          --don't forward. Of these only csr_read and loads don't flush the
          --pipeline so these are the ones we concern ourselves with here.
          if opcode = LOAD_OP or opcode = SYSTEM_OP then
            no_fwd_path <= '1';
          end if;

          if (opcode = LUI_OP or opcode = AUIPC_OP or opcode = ALU_OP or opcode = ALUI_OP) then
            if rd = subseq_rs1 and rd /= R_ZERO then
              rs1_mux <= ALU_FWD;
            end if;
            if rd = subseq_rs2 and rd /= R_ZERO then
              rs2_mux <= ALU_FWD;
            end if;
          end if;
        end if;
      end if;
    end if;
  end process;

  alu : arithmetic_unit
    generic map (
      REGISTER_SIZE       => REGISTER_SIZE,
      SIMD_ENABLE         => false,
      SIGN_EXTENSION_SIZE => SIGN_EXTENSION_SIZE,
      POWER_OPTIMIZED     => POWER_OPTIMIZED,
      MULTIPLY_ENABLE     => MULTIPLY_ENABLE,
      DIVIDE_ENABLE       => DIVIDE_ENABLE,
      SHIFTER_MAX_CYCLES  => SHIFTER_MAX_CYCLES,
      FAMILY              => FAMILY
      )
    port map (
      clk                => clk,
      valid_instr        => valid_instr,
      simd_op_size       => simd_op_size,
      stall_from_execute => stall_from_execute,
      rs1_data           => alu_rs1_data,
      rs2_data           => alu_rs2_data,
      instruction        => instruction,
      sign_extension     => sign_extension,
      program_counter    => pc_current,
      data_out           => alu_data_out,
      data_out_valid     => alu_data_out_valid,
      less_than          => less_than,
      stall_from_alu     => stall_from_alu,

      lve_data1        => lve_alu_data1,
      lve_data2        => lve_alu_data2,
      lve_source_valid => lve_alu_source_valid
      );


  branch : entity work.branch_unit(latch_middle)
    generic map (
      REGISTER_SIZE       => REGISTER_SIZE,
      SIGN_EXTENSION_SIZE => SIGN_EXTENSION_SIZE)
    port map(
      clk            => clk,
      reset          => reset,
      valid          => valid_instr,
      stall          => stall_to_execute,
      rs1_data       => rs1_data_fwd,
      rs2_data       => rs2_data_fwd,
      current_pc     => pc_current,
      br_taken_in    => br_taken_in,
      instr          => instruction,
      less_than      => less_than,
      sign_extension => sign_extension,
      data_out       => br_data_out,
      data_enable    => br_data_enable,
      new_pc         => br_new_pc,
      is_branch      => is_branch,
      br_taken_out   => br_taken_out,
      bad_predict    => br_bad_predict);

  ls_unit : load_store_unit
    generic map(
      REGISTER_SIZE       => REGISTER_SIZE,
      SIGN_EXTENSION_SIZE => SIGN_EXTENSION_SIZE)
    port map(
      clk                      => clk,
      reset                    => reset,
      valid                    => valid_instr,
      rs1_data                 => rs1_data_fwd,
      rs2_data                 => rs2_data_fwd,
      instruction              => instruction,
      sign_extension           => sign_extension,
      writeback_stall_from_lsu => writeback_stall_from_lsu,
      stall_from_lsu           => stall_from_lsu,
      data_out                 => ld_data_out,
      data_enable              => ld_data_enable,

      oimm_address       => lsu_oimm_address,
      oimm_byteenable    => lsu_oimm_byteenable,
      oimm_requestvalid  => lsu_oimm_requestvalid,
      oimm_readnotwrite  => lsu_oimm_readnotwrite,
      oimm_writedata     => lsu_oimm_writedata,
      oimm_readdata      => lsu_oimm_readdata,
      oimm_readdatavalid => lsu_oimm_readdatavalid,
      oimm_waitrequest   => lsu_oimm_waitrequest
      );

  entire_pipeline_empty <= pipeline_empty and not valid_input and not fetch_in_flight;

  syscall : system_calls
    generic map (
      REGISTER_SIZE     => REGISTER_SIZE,
      INTERRUPT_VECTOR  => INTERRUPT_VECTOR,
      POWER_OPTIMIZED   => POWER_OPTIMIZED,
      ENABLE_EXCEPTIONS => ENABLE_EXCEPTIONS,
      COUNTER_LENGTH    => COUNTER_LENGTH
      )
    port map (
      clk   => clk,
      reset => reset,
      valid => valid_instr,

      stall_out => stall_from_syscall,

      rs1_data    => rs1_data_fwd,
      instruction => instruction,
      data_out    => sys_data_out,
      data_enable => sys_data_enable,

      current_pc    => pc_current,
      pc_correction => syscall_target,
      pc_corr_en    => syscall_en,

      interrupt_pending   => interrupt_pending,
      pipeline_empty      => entire_pipeline_empty,
      external_interrupts => external_interrupts,

      instruction_fetch_pc => ifetch_next_pc,
      br_bad_predict       => br_bad_predict,
      br_new_pc            => br_new_pc);

  enable_lve : if LVE_ENABLE /= 0 generate
  begin
    lve : lve_top
      generic map (
        REGISTER_SIZE    => REGISTER_SIZE,
        SCRATCHPAD_SIZE  => SCRATCHPAD_SIZE,
        POWER_OPTIMIZED  => POWER_OPTIMIZED,
        SLAVE_DATA_WIDTH => REGISTER_SIZE,
        FAMILY           => FAMILY
        )
      port map (
        clk            => clk,
        scratchpad_clk => scratchpad_clk,
        reset          => reset,
        instruction    => instruction,
        valid_instr    => valid_instr,
        rs1_data       => rs1_data_fwd,
        rs2_data       => rs2_data_fwd,
        slave_address  => sp_address,
        slave_read_en  => sp_read_en,
        slave_write_en => sp_write_en,
        slave_byte_en  => sp_byte_en,
        slave_data_in  => sp_writedata,
        slave_data_out => sp_readdata,
        slave_ack      => sp_ack,

        lve_executing        => lve_executing,
        lve_alu_data1        => lve_alu_data1,
        lve_alu_data2        => lve_alu_data2,
        lve_alu_op_size      => simd_op_size,
        lve_alu_source_valid => lve_alu_source_valid,
        lve_alu_result       => alu_data_out,
        lve_alu_result_valid => alu_data_out_valid
        );

  end generate enable_lve;

  n_enable_lve : if LVE_ENABLE = 0 generate
    lve_executing        <= '0';
    simd_op_size         <= LVE_WORD_SIZE;
    lve_alu_source_valid <= '0';
    lve_alu_data1        <= (others => '-');
    lve_alu_data2        <= (others => '-');
    sp_readdata          <= (others => '-');
    sp_ack               <= '-';
  end generate n_enable_lve;



  predict_corr_en <= syscall_en or br_bad_predict;
  predict_corr    <= br_new_pc  when syscall_en = '0' else syscall_target;
  predict_pc      <= pc_current when rising_edge(clk);

  branch_pred <= branch_pack_signal(predict_pc,       --this pc
                                    predict_corr,     --branch target
                                    br_taken_out,     --taken
                                    predict_corr_en,  --flush
                                    is_branch);       --is_branch


  -----------------------------------------------------------------------------
  -- This process does some debug printing during simulation,
  -- it should have no impact on synthesis
  -----------------------------------------------------------------------------
--pragma translate_off
  my_print : process(clk)
    variable my_line          : line;   -- type 'line' comes from textio
    variable last_valid_pc    : std_logic_vector(pc_current'range);
    type register_list is array(0 to 31) of std_logic_vector(REGISTER_SIZE-1 downto 0);
    variable shadow_registers : register_list := (others => (others => '0'));

    constant DEBUG_WRITEBACK : boolean := false;

  begin
    if rising_edge(clk) then

      if wb_enable = '1' and DEBUG_WRITEBACK then
        write(my_line, string'("WRITEBACK: PC = "));
        hwrite(my_line, last_valid_pc);
        shadow_registers(to_integer(unsigned(wb_sel))) := wb_data;
        write(my_line, string'(" REGISTERS = {"));
        for i in shadow_registers'range loop
          hwrite(my_line, shadow_registers(i));
          if i /= shadow_registers'right then
            write(my_line, string'(","));
          end if;

        end loop;  -- i
        write(my_line, string'("}"));
        writeline(output, my_line);
      end if;


      if valid_instr = '1' then
        write(my_line, string'("executing pc = "));  -- formatting
        hwrite(my_line, (pc_current));  -- format type std_logic_vector as hex
        write(my_line, string'(" instr =  "));       -- formatting
        hwrite(my_line, (instruction));  -- format type std_logic_vector as hex
        if stall_from_execute = '1' then
          write(my_line, string'(" stalling"));      -- formatting
        else
          last_valid_pc := pc_current;
        end if;
        writeline(output, my_line);     -- write to "output"
      else
      --write(my_line, string'("bubble"));  -- formatting
      --writeline(output, my_line);     -- write to "output"
      end if;

    end if;
  end process my_print;
--pragma translate_on
end architecture;
