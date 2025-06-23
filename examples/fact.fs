var res 0
: fact
    1 res !
    begin
        dup 0 != if
            dup
            res @ * res !
            dec
        else
            drop
            exit
        then
    again
;
10 fact
halt