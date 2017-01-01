library IEEE;
use IEEE.STD_LOGIC_1164.all;
use IEEE.numeric_std.all;
use IEEE.STD_LOGIC_TEXTIO.all;
use STD.TEXTIO.all;

library work;
use work.utils.all;
use work.constants_pkg.all;

entity lve_ci is
  generic (
    REGISTER_SIZE : positive := 32
    );
  port (
    clk   : in std_logic;
    reset : in std_logic;

    func3 : in std_logic_vector(2 downto 0);


    valid_in : in std_logic;
    data1_in : in std_logic_vector(REGISTER_SIZE-1 downto 0);
    data2_in : in std_logic_vector(REGISTER_SIZE-1 downto 0);

    align1_in : in std_logic_vector(1 downto 0);
    align2_in : in std_logic_vector(1 downto 0);

    valid_out        : out std_logic;
    write_enable_out : out std_logic;
    data_out         : out std_logic_vector(REGISTER_SIZE-1 downto 0)
    );
end entity;

architecture rtl of lve_ci is
  constant PIPELINE_DEPTH : positive := 3;

  --For testing pipeline the result

  constant VCUSTOM0_FUNC3 : std_logic_vector(2 downto 0) := "101";
  constant VCUSTOM1_FUNC3 : std_logic_vector(2 downto 0) := "110";
  constant VCUSTOM2_FUNC3 : std_logic_vector(2 downto 0) := "111";
  constant VCUSTOM3_FUNC3 : std_logic_vector(2 downto 0) := "000";
  constant VCUSTOM4_FUNC3 : std_logic_vector(2 downto 0) := "001";
  constant VCUSTOM5_FUNC3 : std_logic_vector(2 downto 0) := "010";

  signal cust0_out_data : std_logic_vector(REGISTER_SIZE-1 downto 0);

  signal conv_weights : std_logic_vector(8 downto 0);
  type row_t is array(0 to 2) of signed(7 downto 0);
  type rows_t is array(0 to 2) of row_t;

  signal rows   : rows_t;
  signal in_row : row_t;
  signal align  : std_logic_vector(1 downto 0);

  constant CONV_ADDER_WIDTH : integer := 12;
  function addsub_pix (
    in_pix : signed(7 downto 0);
    weight : std_logic)
    return signed is
  begin  -- function addsub_pix
    if weight = '1' then
      return RESIZE(in_pix, CONV_ADDER_WIDTH);
    end if;
    return -RESIZE(in_pix, CONV_ADDER_WIDTH);
  end function addsub_pix;

  type sum_t is array(0 to 7) of signed(CONV_ADDER_WIDTH-1 downto 0);
  signal conv_sum           : sum_t;
  signal conv_valid_data    : std_logic_vector(2 downto 0);
  signal conv_data_out      : std_logic_vector(REGISTER_SIZE-1 downto 0);
  signal conv_we, conv_done : std_logic;
begin

  -----------------------------------------------------------------------------
  -- WORD to byte saturation conversion
  -----------------------------------------------------------------------------
  cust0_out_data(7 downto 0) <= x"7F" when signed(data1_in) > 127 else
                                x"80" when signed(data1_in) < -128 else
                                data1_in(7 downto 0);
  cust0_out_data(31 downto 8) <= data1_in(31 downto 8);



  -----------------------------------------------------------------------------
  -- CONVOLUTION CUSTOM INSTRUCTION
  -----------------------------------------------------------------------------
  weight_setup : process(clk)
  begin
    if rising_edge(clk) then
      if func3 = VCUSTOM1_FUNC3 and valid_in = '1'then
        conv_weights <= data1_in(8 downto 0);
      end if;
    end if;
  end process;

  with align1_in select
    in_row(0) <=
    signed(data1_in(31 downto 24)) when "00",
    signed(data1_in(23 downto 16)) when "01",
    signed(data1_in(15 downto 8))  when "10",
    signed(data1_in(7 downto 0))   when others;
  with align1_in select
    in_row(1) <=
    signed(data1_in(23 downto 16)) when "00",
    signed(data1_in(15 downto 8))  when "01",
    signed(data1_in(7 downto 0))   when "10",
    signed(data2_in(31 downto 24)) when others;

  with align1_in select
    in_row(2) <=
    signed(data1_in(15 downto 8))  when "00",
    signed(data1_in(7 downto 0))   when "01",
    signed(data2_in(31 downto 24)) when "10",
    signed(data2_in(23 downto 16)) when others;

  --latch some of these if we want better timing
  --Layer 0 ( with 1 extra add)
  conv_sum(0) <= addsub_pix(rows(0)(0), conv_weights(0))+
                 addsub_pix(rows(0)(1), conv_weights(1));
  conv_sum(1) <= addsub_pix(rows(0)(2), conv_weights(2))+
                 addsub_pix(rows(1)(0), conv_weights(3));
  conv_sum(2) <= addsub_pix(rows(1)(1), conv_weights(4))+
                 addsub_pix(rows(1)(2), conv_weights(5));
  conv_sum(3) <= addsub_pix(rows(2)(0), conv_weights(6))+
                 addsub_pix(rows(2)(1), conv_weights(7));
  conv_sum(4) <= addsub_pix(rows(2)(2), conv_weights(8)) +
                 conv_sum(3);
  --layer 1
  conv_sum(5) <= conv_sum(0) + conv_sum(1);
  conv_sum(6) <= conv_sum(2) + conv_sum(4);
  --layer2
  conv_sum(7) <= conv_sum(5) + conv_sum(6);


  process(clk)
  begin
    if rising_edge(clk) then
      --rotatie rows
      conv_valid_data <= conv_valid_data(1 downto 0) & valid_in;
      rows(0)         <= in_row;
      rows(1)         <= rows(0);
      rows(2)         <= rows(1);
      conv_data_out   <= std_logic_vector(RESIZE(conv_sum(7), conv_data_out'length));
      conv_we         <= bool_to_sl(conv_valid_data = "111");
      conv_done       <= conv_valid_data(1);
    end if;
  end process;


  -----------------------------------------------------------------------------
  -- COMMON STUFF
  -----------------------------------------------------------------------------
  process (clk) is
  begin  -- process
    if clk'event and clk = '1' then     -- rising clock edge
      valid_out        <= '0';
      write_enable_out <= '0';
      data_out         <= (others => '0');

      if func3 = VCUSTOM0_FUNC3 then
        --word to byte conversion
        valid_out        <= valid_in;
        write_enable_out <= valid_in;
        data_out         <= cust0_out_data;
      end if;
      if func3 = VCUSTOM1_FUNC3 then
        --setup weights
        valid_out <= valid_in;
      --no writeback
      end if;
      if func3 = VCUSTOM2_FUNC3 then
        --convolution instruction
        valid_out        <= conv_done;
        write_enable_out <= conv_we;
        data_out         <= conv_data_out;
      end if;

    end if;
  end process;

end architecture rtl;
