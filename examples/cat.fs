var buffer
var data_ready
: cat
    begin
        data_ready @
        0 != if
            buffer @
            0 != if
                buffer @
                out 1
            else
                exit
            then
            0 data_ready !
        then
    again
;
: interrupt_handler
    in 0
    buffer !
    data_ready 1 !
;
0 data_ready !
0 buffer !
eint
cat
halt