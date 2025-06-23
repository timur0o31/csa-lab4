var result 0
var sum1 0
var sum2 0
var counter 0x0
: sum_of_square
    101
    begin
      dup counter @ != if
      sum1 @
      counter @ dup *
      +
      sum1 !
      counter @ inc counter !
      else
      exit
      then
    again
    drop
;
: sum
    101
    begin
      dup counter @ != if
      sum2 @
      counter @
      +
      sum2 !
      counter @ inc counter !
      else
      exit
      then
    again
    drop
;
sum1 @ sum_of_square
0 counter !
sum2 @ sum
sum2 @ dup *
sum1 @
swap -
result ! drop
halt