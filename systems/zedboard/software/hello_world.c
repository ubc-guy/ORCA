#include "uart.h"

int main(void) {

  ChangedPrint("Hello World\r\n");

	while(1){
	}
}

int handle_interrupt(int cause, int epc, int regs[32])
{
	if (!((cause >> 31) & 0x1)) {
		// Handle illegal instruction
    // Nothing implemented yet; just print a debug message and hang.
		ChangedPrint("Unhandled illegal instruction...\r\n");
		for (;;);
	}

	// Handle interrupt
  // Ignore and return for this test
	return epc;
}
