module SB_PLL40_CORE_wrapper_div3
  (
   input       REFERENCECLK,
   output      PLLOUTCORE,
   output      PLLOUTGLOBAL,
   input       EXTFEEDBACK,
   input [7:0] DYNAMICDELAY,
   output      LOCK,
   input       BYPASS,
   input       RESETB,
   input       LATCHINPUTVALUE,

   //Test Pins
   output      SDO,
   input       SDI,
   input       SCLK
   );
   SB_PLL40_CORE 
     #(
       // .FEEDBACK_PATH("SIMPLE"),
       // .FEEDBACK_PATH("DELAY"),
       // .FEEDBACK_PATH("PHASE_AND_DELAY"),
       .FEEDBACK_PATH("EXTERNAL"),

       .DELAY_ADJUSTMENT_MODE_FEEDBACK("FIXED"),
       // .DELAY_ADJUSTMENT_MODE_FEEDBACK("DYNAMIC"),

       .DELAY_ADJUSTMENT_MODE_RELATIVE("FIXED"),
       // .DELAY_ADJUSTMENT_MODE_RELATIVE("DYNAMIC"),

       .PLLOUT_SELECT("GENCLK"),
       // .PLLOUT_SELECT("GENCLK_HALF"),
       // .PLLOUT_SELECT("SHIFTREG_90deg"),
       // .PLLOUT_SELECT("SHIFTREG_0deg"),

       .SHIFTREG_DIV_MODE(1'b0),
       .FDA_FEEDBACK(4'b0000),
       .FDA_RELATIVE(4'b0000),
       .DIVR(4'b0010),
       .DIVF(7'b0000000),
       .DIVQ(3'b101),
       .FILTER_RANGE(3'b001),
       .ENABLE_ICEGATE(1'b0),
       .TEST_MODE(1'b0)
       ) 
   uut 
     (
      .REFERENCECLK   (REFERENCECLK   ),
      .PLLOUTCORE     (PLLOUTCORE     ),
      .PLLOUTGLOBAL   (PLLOUTGLOBAL   ),
      .EXTFEEDBACK    (EXTFEEDBACK    ),
      .DYNAMICDELAY   (DYNAMICDELAY   ),
      .LOCK           (LOCK           ),
      .BYPASS         (BYPASS         ),
      .RESETB         (RESETB         ),
      .LATCHINPUTVALUE(LATCHINPUTVALUE),
      .SDO            (SDO            ),
      .SDI            (SDI            ),
      .SCLK           (SCLK           )
      );
endmodule
