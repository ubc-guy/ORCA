#include "vbx.h"


int test_2()
{
	vbx_ubyte_t* sp_data = (vbx_ubyte_t*)(SCRATCHPAD_BASE+8*1024);
	vbx_word_t* sp_data_copy = (vbx_word_t*)(SCRATCHPAD_BASE+16*1024);
	vbx_ubyte_t* dummy_buf = (vbx_ubyte_t*)(SCRATCHPAD_BASE+125*1024);
	vbx_ubyte_t* dummy_in = (vbx_ubyte_t*)(SCRATCHPAD_BASE);

	for(int i=0;i<32;i++){
		sp_data[i] = 0;
		dummy_in[i] = 1;
	}

	for(int i=0;i<32;i++){
		dummy_buf[i] = dummy_in[i];
		sp_data_copy[i] = sp_data[i];
	}

	for(int i = 0;i<32;i++){
		if(sp_data_copy[i] != sp_data[i]){
			return 1; //TEST FAIL
		}
	}

	//TEST SUCCESS
	return 0;
}

typedef int (*test_func)(void) ;
test_func test_functions[] = {
	test_2,
	(void*)0,
};
