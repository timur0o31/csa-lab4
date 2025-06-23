var len
var i
var j
var ind
var buffer
var data_ready
array myarr 10
: sort
    len @
    begin
        dup i @ != if
            len @ dec
            begin
                dup j @ != if
                    myarr j @ + @
                    myarr j @ + 1 + @
                    > if
                        myarr j @ + @
                        myarr j @ + 1 + @
                        swap
                        myarr j @ + 1 + !
                        myarr j @ + !
                    then
                    j @ inc j !
                else
                    drop
                    0 j !
                    exit
                then
            again
            i @ inc i !
        else
            drop
            exit
        then
    again
;
: length
    0
    begin
        dup myarr + @
        0 != if
        inc
        else
            len !
            exit
        then
    again
;
: print
    0
    begin
        dup len @ != if
        dup myarr + @
        48 +
        out 1
        inc
        else
            exit
        then
    again
;
: read
    begin
        data_ready @
        0 != if
            buffer @
            dup
            0 != if
                48 swap -
                myarr ind @ + !
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
eint
read
myarr
length
sort
print
halt

