str s1 "What is your name?"
var buffer
var data_ready
var ind
str s2 "Hello, "
array buf 10
: print_str
    begin
        dup @
        dup 0 != if
            out 1
            inc
        else
            drop
            exit
        then
    again
;
: read
    begin
        data_ready @
        0 != if
            buffer @
            0 != if
                buffer @ buf ind @ + !
                ind @ inc ind !
                0 data_ready !
            else
                exit
            then
        then
    again
;
: interrupt_handler
    in 0
    buffer !
    1 data_ready !
;
0 data_ready !
0 buffer !
0 ind !
eint
s1 print_str
10 out 1
read
s2 print_str
buf print_str
33 out 1
halt
