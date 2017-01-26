#include "printf.h"
#include "vbx.h"


//8x8 input map with padding
//1 BYTE per pixel
//each row is aligned to word size
#define INPUT_MAP_SIZE 8
vbx_byte_t input_map [] = { 0,0,0,0,0,0,0,0,0,0,0,0,
                            0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0,0,0,
                            0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0,0,0,
                            0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0,0,0,
                            0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0,0,0,
                            0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0,0,0,
                            0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0,0,0,
                            0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0,0,0,
                            0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0,0,0,
                            0,0,0,0,0,0,0,0,0,0,0,0};

vbx_word_t output_map [INPUT_MAP_SIZE*INPUT_MAP_SIZE];

vbx_half_t sample_weight=0x1AA; //0b110 101 010

//extra 4 element padding just like the source image
vbx_word_t output_map_check[]={0,0,0,0,0,0,0,0,0,0,0,0,
                               0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x1FE,0,0,0,0,
                               0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x1FE,0,0,0,0,
                               0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x1FE,0,0,0,0,
                               0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x1FE,0,0,0,0,
                               0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x1FE,0,0,0,0,
                               0,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x1FE,0,0,0,0,
                               0,0x1FE,0x1FE,0x1FE,0x1FE,0x1FE,0x1FE,0x1FE,0,0,0,0};

///
// Padding:
//
// Padding rows on the top and bottom work faily straight-forward.
// You need padding on the top and bottom, and the custom instruction does 2 less writes
// than reads so padding rows in the source does not result in padding rows in the destination.
//
// Padding for colunms is slightly more complicated. All rows must be word aligned, every byte of
// Padding in the source results in a byte of padding in the destination.
void vbx_convolve(vbx_byte_t* input_map,vbx_word_t* output_map,int square_size,vbx_half_t weights)
{
	//the weights are the 9 LSBs of the weights parameter
	int col;

	//set up the weights.
	//dest and srcb do not matter;
	vbx_set_vl(1);
	vbx(SVW,VCUSTOM1,0,weights,0);
	vbx_set_vl(square_size+2);

	//stride is square size + 2 bytes for zero padding, + 2 bytes for word alignment
	int stride=square_size+2 +2;

	the_mxp.stride=stride;
	for(col=0;col<square_size;col++){
		vbx(VVWB,VCUSTOM2,output_map+col,input_map+col,input_map+col+4);
	}

}

int test_conolve(){

	vbx_byte_t* v_input_map=SCRATCHPAD_BASE;
	vbx_word_t* v_output_map=(vbx_word_t*)(v_input_map+sizeof(input_map));

	const int PRINT_MATS=0;
	printf("CONVOLVE TEST  start\r\n");
	//copy the static data into the scratchpad
	int i,j;
	for(i=0;i<sizeof(input_map);i++){
		v_input_map[i]=input_map[i];
	}
	if (PRINT_MATS){
		printf("\r\noutput_map_check\r\n");
		for(i=0;i<INPUT_MAP_SIZE;i++){
			for(j=0;j<INPUT_MAP_SIZE;j++){
				printf("%3d ",(int)(output_map_check[i*(INPUT_MAP_SIZE+4)+j]));
				v_output_map[i*INPUT_MAP_SIZE+j]=0;
			}printf("\r\n");
		}
	}
	for(i=0;i<(sizeof(output_map_check)/sizeof(output_map_check[0]));i++){
		v_output_map[i]=0;
	}

	vbx_convolve(v_input_map,v_output_map,INPUT_MAP_SIZE,sample_weight);

	int errors=0;
	for(i=0;i<(sizeof(output_map_check)/sizeof(output_map_check[0]));i++){
		if (output_map_check[i] != v_output_map[i]){
			printf("FAILED i=%d %x !=%x\r\n",i,(int)output_map_check[i],(int)(v_output_map[i]));
			errors++;
		}
	}
 	if(!errors){
		printf("CONVOLVE TEST Passed\r\n");
	}
	if(PRINT_MATS){
		printf("\r\noutput_map\r\n");
		for(i=0;i<INPUT_MAP_SIZE;i++){
			for(j=0;j<INPUT_MAP_SIZE;j++){
				printf("%3d ",(int)(v_output_map[i*(INPUT_MAP_SIZE+4)+j]));
			}printf("\r\n");
		}
	}
	return errors;

}

int test_word_to_byte()
{
	int test_length=1024;;
	vbx_uword_t* v_input=SCRATCHPAD_BASE;
	vbx_ubyte_t* v_output=(vbx_byte_t*)(v_input+test_length);

	int i;
	int errors=0;

#define input_gen(i) (i-test_length/2)
	for(i=0;i<test_length;i++){
		v_input[i] = input_gen(i) ;
	}

	the_mxp.stride=1;
	vbx_set_vl(test_length);

	vbx(VVBWU,VCUSTOM0,v_output,v_input,0);


	for(i=0;i<test_length;i++){
		int test_val= input_gen(i);
		if(test_val<0)
			test_val=0;
		if(test_val>0xFF)
			test_val=255;
		if(test_val != v_output[i]){
			errors++;
			printf("ERROR i=%d %x !=%x\r\n",i,(int)test_val,(int)v_output[i]);
		}
	}
	if(!errors){
		printf("WORD TO BYTE TEST Passed\r\n");
	}
	return errors;
}

int main()
{
	int errors=0;
	errors+= test_conolve();
	errors+= test_word_to_byte();


	printf("DONE -- errors = %d %s\r\n",errors,errors?"FAILED :(":"PASSED :)");

}




/////
//Word to byte conversion sample
/////


void vbx_w2b_convert(vbx_word_t* input_map,vbx_byte_t* output_map,int num_elements)
{
	the_mxp.stride=1;
	vbx_set_vl(num_elements);
	vbx(VVBW,VCUSTOM0,output_map,input_map,0);
}