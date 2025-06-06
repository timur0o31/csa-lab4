var res 1 2 3 4 ; смотри чтобы :: такая конструкция не угрохала лейблы
var ret "str"
fact:
	dup lit
fact_loop:
	dup
	lit res
	@
	*
	lit res
	!
	dec
	lit loop_end
	jz
	lit fact_loop
	jump
loop_end:
	;

start:
	lit 5
	lit fact
	call
	halt
