#ifndef __BSP_H
#define __BSP_H

#define ORCA_CLK 100000000

#define PS7_UART_BASE_ADDRESS  0xE0001000

#define AXI_TIMER_BASE_ADDRESS     0xFFFE0000
#define AXI_GPIO_LEDS_BASE_ADDRESS 0xFFFF0000

#define ORCA_ENABLE_EXCEPTIONS     1
#define ORCA_ENABLE_EXT_INTERRUPTS 1
#define ORCA_NUM_EXT_INTERRUPTS    2

#define AXI_TIMER_CLK 100000000

#endif //#ifndef __BSP_H
