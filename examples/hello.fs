str s1 "hello world!"
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
    10 out 1
;

s1 print_str
halt