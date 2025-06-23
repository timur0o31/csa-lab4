var h_result
var l_result
var val1
var val2
var value
var len
: print
    begin
        len @ 0 != if
        48 +
        out 1
        len @ dec len !
        else
            exit
        then
    again
;
: int_to_digits
    begin
        dup 0 != if
        dup dup 10 swap /
        10 * swap - swap 10 swap /
        len @ inc len !
        else
            drop
            exit
        then
    again
;
131072 131073 *2
swap
int_to_digits
print
32 out 1
int_to_digits
print
halt