#!/bin/sh
TEST_DIR=~/riscv-tools/riscv-tests/isa
SOFTWARE_DIR=../software
#all files that aren't dump or hex (the hex files are not correctly formatted)
FILES=$(ls ${TEST_DIR}/rv32ui-p-* | grep -v dump | grep -v hex)
ORCA_FILES=$(ls ${SOFTWARE_DIR}/* | grep .elf)


if which mif2hex >/dev/null
then
	 :
else
	 echo "ERROR: Cant find command mif2hex, have you loaded nios2 tools? Exiting." >&2
	 exit -1;
fi
mkdir -p test


#MEM files are for lattice boards, the hex files are for altera boards
for f in $FILES
do
	 echo "$f > test/$(basename $f).qex"
	 (
		  BIN_FILE=test/$(basename $f).bin
		  QEX_FILE=test/$(basename $f).qex
		  MEM_FILE=test/$(basename $f).mem
		  MIF_FILE=test/$(basename $f).mif
		  SPLIT_FILE=test/$(basename $f).split2
		  cp $f test/
		  riscv64-unknown-elf-objcopy -O binary $f $BIN_FILE
		  riscv64-unknown-elf-objdump -D $f > test/$(basename $f).dump

		  python ../tools/bin2mif.py $BIN_FILE 0x200 > $MIF_FILE || exit -1
		  mif2hex $MIF_FILE $QEX_FILE >/dev/null 2>&1 || exit -1
		  sed -e 's/://' -e 's/\(..\)/\1 /g'  $QEX_FILE >$SPLIT_FILE
		  awk '{if (NF == 9) print $5$6$7$8}' $SPLIT_FILE > $MEM_FILE
		 # rm -f $MIF_FILE $SPLIT_FILE
	 ) &
done

for f in $ORCA_FILES
do
  FILE=$(basename "$f")
  FILE="${FILE%.*}"
  echo "$f > test/$FILE.qex"
  (
    BIN_FILE=test/$(basename $FILE).bin
    QEX_FILE=test/$(basename $FILE).qex
    MEM_FILE=test/$(basename $FILE).mem
    MIF_FILE=test/$(basename $FILE).mif
    SPLIT_FILE=test/$(basename $FILE).split2
    cp $f test/
    riscv64-unknown-elf-objcopy -O binary $f $BIN_FILE
    riscv64-unknown-elf-objdump -D $f > test/$FILE.dump

    python ../tools/bin2mif.py $BIN_FILE 0x100 > $MIF_FILE || exit -1
    mif2hex $MIF_FILE $QEX_FILE >/dev/null 2>&1 || exit -1
    sed -e 's/://' -e 's/\(..\)/\1 /g'  $QEX_FILE >$SPLIT_FILE
    awk '{if (NF == 9) print $5$6$7$8}' $SPLIT_FILE > $MEM_FILE
  ) &
done
wait
