; demo.asm
var  TEN  10

var   counter  0         ; изменяемая переменная

start:
        lit TEN           ; положить 10
        lit
        !                 ; counter := 10
        lit counter
        @                 ; взять counter
        dec
        lit counter
        !                 ; counter--
        halt
