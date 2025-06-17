var res 0x1
start:
	lit 5
	lit fact
	call
	halt
fact:
	dup
	lit loop_end
	swap
	jn 
	dup
	lit loop_end
	swap
	jz 
fact_loop:
	dup
	lit res
	@
	*
	lit res
	!
	dec
	dup
	lit loop_end
	swap
	jz
	lit fact_loop
	jump
loop_end:
	ret


