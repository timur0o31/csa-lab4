# Альметов Тимур Айдарович, P3207
- Вариант:  forth | stack | harv | hw | tick | binary | trap | port | cstr | prob2 | superscalar
## Содержание
1. [Язык программирования](#язык-программирования)
2. [Организация памяти](#организация-памяти)
3. [Система команд](#система-команд)
4. [Транслятор](#транслятор)
5. [Модель процессора](#модель-процессора)
6. [Тестирование](#тестирование)

## Язык программирования
Описание синтаксиса языка в стиле БНФ:
```ebnf
<program> ::= <statement>+ 

<statement> ::= <procedure_def>
                        | <if_statement>
                        | <loop_statement>
			| <interrupt_statement>
                        | <line>
<line> ::= <word>+ "\n"
         | "\n"
         | <var_declaration>
         | <string-declaration>
         | <array-declaration> 

<var_declaration> ::= "var" <name> <number>?

<string-literal-declaration> ::= 'str' <name> literal

<array-declaration> ::= 'array' <name> memory-block-size

<procedure_def> ::= ":" <name> <statement-body>* ";"

<if-statement> ::= <compare_op> 'if' <statement-body> ('then' | ('else' <statement-body> 'then'))

<loop-statement> ::= 'begin' <statement-body> 'exit'? 'again'

<interrupt-statement> ::= ":" 'interrupt_handler' <statement-body>* ";"

<statement-body> ::= <if-statement>
                |  <loop-statement>
                |  <statement-body>
                |  <word>+

<word> ::= <control_instr>
        | <io_instr>
        | <instr>
        | <comment>
<literal> ::= "<name>"
<name> ::= [a-zA-Z_][a-zA-Z0-9_]*
<compare_op> = "!=" | ">" ;
<io_instr> ::= "in" | "out"
<instr> ::= "@" | "!" | "+" | "-" | "*" | "/" | 2* | "and" | "or" | "xor" | "not" |
		"dup" | "drop" | "swap" | "inc" | "dec"
<control_instr> ::= "halt" | "eint" | "dint" | ";" | "iret"

<number> ::= "-"? <digit>+
<digit> ::= [0-9]

<comment> ::= "\" <characters>
<characters> ::= .*

```
### Семантика 
Код выполняется последовательно одна инструкция за другой.
- `number` - положить значение на стек.
- `!` -  взять второй элемент стека и сохранить его по адресу хранящемуся в первом элементе стека. И значение и адрес убираются со стека.
- `@` - взять адрес из первого элемента стека и положить значение, хранящееся по этому адрес на стек. Адрес убирается со стека
- `+` - сложить два верхних элемента стека и положить результат на стек. Элементы снимаются со стека.
- `-` - вычесть второй элемент стека из первого и положить результат на стек. Элементы снимаются со стека.
- `*` - перемножить два верхних элемента стека и положить результат на стек. Элементы снимаются со стека.
- `/` - разделить второй элемент стека на первый и положить результат на стек. Элементы снимаются со стека.
- `2*` - перемножить два верхних элемента стека и положить результат двойной точности на стек. Элементы снимаются со стека.
- `and` - применить побитовое И для первых двух элементов стека и положить результат на стек. Элементы снимаются со стека.
- `or` - применить побитовое ИЛИ для первых двух элементов стека и положить результат на стек. Элементы снимаются со стека.
- `xor` - применить побитовое исключающее ИЛИ для первых двух элементов стека и положить результат на стек. Элементы снимаются со стека.
- `!= if <statement-body> then` -- если два верхних элемента равны выполнить набор инструкций из `statement-body`. Элементы сравнения снимаются со стека.
- `!= if <statement-body1> else <statement-body2> then` - если два верхних элемента равны выполнить набор инструкций из `statement-body1`, иначе из `statement-body2`. Элементы сравнения снимаются со стека.
- `> if <statement-body> then` -- если второй элемент стека больше первого выполнить набор инструкций из `statement-body`. Элементы сравнения снимаются со стека.
- `> if <statement-body1> else <statement-body2> then` - если второй элемент стека больше первого выполнить набор инструкций из `statement-body1`, иначе из `statement-body2`. 
Элементы сравнения снимаются со стека. 
- `begin <statement-body> [exit] again` - `begin` запускает бесконечный цикл: поток управления возвращается к `begin` после выполнения с помощью `again`. Выход из цикла осуществляется только инструкцией `exit`, расположенной внутри `<statement-body>`. При выполнении `exit` управление передаётся на первую команду, следующую за `again`. 
- `var <name> <number>?` - объявить и инициализировать переменную с именем `name`.
- `str <name> <literal>` - объявить строковый литерала с именем `name`. Литерал сохраняется в памяти в C - строки. Переменная указывает на начало строки.
- `array <name> <literal>` - объявить массив с именем `name`. Переменная указывает на адрес начала массива.
- `: <name> <statement-body> ; ` - создать процедуру с именем `name`.
- `<procedure_name>` - вызвать процедуру с именем `procedure_name`
- `<var-name>` - положить на вершину стека адрес переменной с именем `var-name`.
- `en_int`- разрешение прерываний
- `di_int` - запрет прерываний
- `in 0` - прочитать значение из устройство ввода и положить значение на стек.
- `out 1` - взять верхний элемент со стека и вывести его в устройство вывода.
- `halt` - завершение программы.
### Пример программы:
```ebnf
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
```
### Особенности реализации
- Бесконечный цикл begin … again. Вход в цикл — при выполнении begin. Выход — только через инструкцию exit, которая передаёт управление за again. Отсутствие exit делает цикл  бесконечным.
- Метка : interrupt_handler … ; обязана присутствовать ровно один раз. На этапе трансляции её адрес (offset первой инструкции тела) фиксируется и записывается в заголовок бинарного файла памяти инструкций. При загрузке программы загрузчик считывает адрес обработчика и записывает его в регистр INTR_ADDR.
- При сохранении строковых литералов они размещаются по одному символу в ячейку памяти, без плотной упаковки. Поддерживаются строковые литералы произвольной длины. В конце строки ставится символ-ноль \0, в соответствии с вариантом.
- Область видимости переменных - глобальные.
- Программа выполняется последовательно, одна инструкция за другой.
	
## Организация памяти
- Система построена по Гарвардской архитектуре, то есть есть разделение команд и данных.
1. Память данных: 32 бит. 
2. Память команд: 32 бит.
   Обе памяти работают в линейном, адресном пространстве.
- Операнды - знаковые 26-разрядные числа, так как 6 бит используется для кода операции.
- Литералы - это знаковые 32-битные значения, но в машинной инструкции lit они могут быть закодированы только в пределах 26 бит. Для представления полных 32-битных литералов используется чтение из памяти.
- Адресация прямая абсолютная. Только прямая загрузка литерала в ячейку памяти/на вершину стека. Косвенная адресация достижима с использованием стека.
- Строковые литералы и блоки данных хранятся в памяти в формате C-string.
``` 
          Data memory
+------------------------------+
| 00  : var   1                |
|    ...                       |
|  n  : var   n                |
|    ...                       |                                   
+------------------------------+
```
### Организация стека:
- Имеются стек данных и стек возврата.
- Основной стек (stack) реализован как массив с дополнительным регистром TOS, хранящим первое значение вершины стека.
- Стек 32-разрядный и позволяет полностью помещать один операнд одной ячейки памяти. 
### Регистры
Используются следующие регистры:
- PC - регистр команд.
- SCP - указатель стека возврата.
- SP - указатель стека данных.
- AR - указатель адреса памяти.
- INT_ADDR - регистр, содержащий адрес установленного обработчика прерывания.
- RET_ADDR - регистр, содержащий адрес возврата из прерывания. В этот регистр сохраняется PC при переходе на обработку прерывания.
- TOS - вершина стека данных.
## Система команд:
### Особенности процессора:
- Машинное слово - 32 битное число.
- Обработка данных осуществляется в стеке. Данные попадают в стек из памяти, либо из устройств ввода/вывода.
- Доступ к памяти осуществляется через указатель на вершине стека. Установить адрес можно через прямую загрузку.
- Устройство ввода-вывода: port-mapped.
- Ввод происходит через прерывания.
### Набор инструкций:
| №  | Мнемоника | Opcode (bin) | Opcode (hex) | Такты  |
| -- | --------- | ------------ | ------------ | ------ |
| 0  | `lit`     | `00001`      | `0x01`       | 1      |
| 1  | `!`       | `00010`      | `0x02`       | 2      |
| 2  | `@`       | `00011`      | `0x03`       | 2      |
| 3  | `in`      | `00100`      | `0x04`       | 1      |
| 4  | `out`     | `00101`      | `0x05`       | 1      |
| 5  | `+`       | `00110`      | `0x06`       | 1      |
| 6  | `mulh`    | `00111`      | `0x07`       | 1      |
| 7  | `-`       | `01000`      | `0x08`       | 1      |
| 8  | `*`       | `01001`      | `0x09`       | 1      |
| 9  | `div`     | `01010`      | `0x0A`       | 1      |
| 10 | `inc`     | `01011`      | `0x0B`       | 1      |
| 11 | `dec`     | `01100`      | `0x0C`       | 1      |
| 12 | `and`     | `01101`      | `0x0D`       | 1      |
| 13 | `or`      | `01110`      | `0x0E`       | 1      |
| 14 | `xor`     | `01111`      | `0x0F`       | 1      |
| 15 | `not`     | `10000`      | `0x10`       | 1      |
| 16 | `jump`    | `10001`      | `0x11`       | 1      |
| 17 | `call`    | `10010`      | `0x12`       | 1      |
| 18 | `jz`      | `10011`      | `0x13`       | 2      |
| 19 | `jn`      | `10100`      | `0x14`       | 2      |
| 20 | `ret`     | `10101`      | `0x15`       | 1      |
| 21 | `swap`    | `10110`      | `0x16`       | 1      |
| 22 | `dup`     | `10111`      | `0x17`       | 1      |
| 23 | `drop`    | `11000`      | `0x18`       | 1      |
| 24 | `iret`    | `11001`      | `0x19`       | 1      |
| 25 | `eint`    | `11010`      | `0x1A`       | 1      |
| 26 | `dint`    | `11011`      | `0x1B`       | 1      |
| 27 | `halt`    | `11100`      | `0x1C`       | 1      |
| 28 | `nop`     | `11101`      | `0x1D`       | 1      |


Описание: 
- `nop` - нет операции.
- `lit <literal>` - положить значение на вершину стека.
- `@` - загрузить из памяти значение по адресу с вершины стека.
- `!` - положить второе значение с вершины стека в память по указанному адресу, который лежит на вершине стека. 
- `+` - положить на стек результат операции сложения двух верхних значений с вершины стека.
- `-` - положить на стек результат операции вычитания двух верхних значений с вершины стека.
- `*` - положить на стек результат операции умножения двух верхних значений с вершины стека.
- `mulh` - положить на стек результат операции умножения двух верхних значений с вершины стека
- `div` - положить на стек результат операции деления двух верхних значений с вершины стека.
- `inc` - положить на стек результат операции инкремнтирования на 1 значения вершины стека.
- `dec` - положить на стек результат операции декрементирования на 1 значения вершины стека.
- `drop` - удалить элемент из стека.
- `dup` - дублировать элемент на стеке.
- `and` - положить на стек результат операции логического "и" двух верхних значений вершины стека.
- `swap` - поменять местами два верхних значения.
- `or` - положить на стек результат операции логического "или" двух верхних значений вершины стека.
- `xor` - положить на стек результат операции исключающего "или" двух верхних значений вершины стека.
- `not` - положить на стек результат операции логического "не" значения вершины стека.
- `jump` - безусловный переход.
- `call` - вызов подпрограммы.
- `jz` - переход на адрес лежащий на вершине стека, если второе значение с вершины стека равно 0.
- `jn` - переход на адрес лежащий на вершине стека, если второе значение с вершины стека меньше 0.
- `ret` - возврат из подпрограммы.
- `in` - считать символ с устройства ввода.
- `out` - вывести символ на устройство вывода.
- `iret` - возврат в основной ход выполнения программы из прерывания.
- `eint` - разрешение прерываний.
- `dint` -  запрет прерываний .
- `halt` - останов.
###Кодирование инструкций:
Инструкции делятся на два типа:
- с аргументом.
```
┌─────────┬──────────────────────────────────────────────────────────┐
│ 31...26 │                      25...0                              |
├─────────┼──────────────────────────────────────────────────────────┤
│  опкод  |                     аргумент                             │
└─────────┴──────────────────────────────────────────────────────────┘
```
- без аргумента.
```
┌─────────┬──────────────────────────────────────────────────────────┐
│ 31...26 │                      25...0                              |
├─────────┼──────────────────────────────────────────────────────────┤
│  опкод  |                     0x00000                              │
└─────────┴──────────────────────────────────────────────────────────┘
```
## Транслятор
Интерфейс командной строки: translator.py <input_file> <target_instructions_file> <target_data_file>
Реализация транслятора: [translator.py](src/translator.py)
### Этапы трансляции:
- Лексический разбор: удаляются комментарии, выделяются строковые литералы, остальное разбивается на токены.
- Перевод управляющих конструкций в набор инструкций.
- Разбор объявлений данных.
- Анализ кода и связывание меток с адресами
- Генерация машинного кода.
## Модель процессора
- Интерфейс командной строки: machine.py <instructions_bin_file> <data_bin_file> <input_file>.
- Реализация модели процессора: [machine.py](src/machine.py)
### DataPath
Реализован в классе `DataPath`
![Data Path Diagram](diagrams/Data_path_scheme.drawio.svg)
### Сигналы:
- latch_tos - защелкнуть значение в top of the stack. В регистр tos данные могу прийти:
  - ALU - результат из АЛУ. В качестве селектора для АЛУ выступает опкод и тип команды.
  - Data_memory - из памяти.
  - CU_ARG - из аргумента инструкции.
  - IN - из ввода.
  - STACK - из второго элемента стека, например для операции swap.
- latch_sp -  защелкнуть значение регистра SP. Данные приходят из мультиплексора, который выбирает между увеличить указатель на 1 или уменьшить на 1 в зависимости от типа действия над стеком.
- latch_data_address - защелкнуть значение в AR.
- write_port - запись данные из TOS в один из портов I/O.
- latch_stack - защелкнуть верхушку Stack.
### Флаги:
- Z - результат равен 0.
- N - результат отрицательный.
### Control Unit
Реализован в классе `ControlUnit`
![Control Unit Diagram](diagrams/Control_Unit.drawio.svg)
### Сигналы:
- latch_pc - защелкнуть значение в PC. 
- latch_scp - защелкнуть значение SCP.
- enable_interrupts - разрешить прерывания.
- disable_interrupts - запретить прерывания.
- set_intr - установить флаг запроса прерывания.
- reset - снять флаг запроса прерывания.
### Прерывания:
- У процессора есть два состояния. NORMAL и INTERRUPTION. Прерываний разрешены только в состоянии NORMAL.
- Состояние процессора хранится в регистре STATE и по сигналу может меняться.
Обработка прерываний:
  - В начале каждого такта осуществляется проверка текущего номера такта в расписании прерываний. Если обнаружено совпадение, а также если прерывания разрешены и процессор находится в состоянии, допускающем обработку прерываний, устанавливается флаг запроса прерывания.
  - Если step == 0 и установлен флаг, то сохраняем регистр PC в RET_ADDR, и записываем в PC адрес обработчика прерывания из INTR_ADDR. 
  - Этап обработки прерывания будет пропущен, если прерывания запрещены или не поступал соответствующий сигнал.
  - Переход на прерывание не сохраняет значение TOS и флагов состояния. Работа по сохранению TOS идет на программиста при реализации обработчика прерывания.

## Тестирование
- Тестирование выполняется при помощи golden тестов
- Модуль для тестирования: [golden_test.py](golden_test.py)
- Конфигурации:
  - [cat.yaml](test/golden/cat.yaml) — вывод данных, подаваемых на ввод
  - [hello.yaml](test/golden/hello.yaml) — вывести Hello, World!
  - [hello_user.yaml](test/golden/hello_user.yaml) — вывод `What is your name?`, ожидание пользовательского ввода, затем вывод `Hello, <введённое имя>!`
  - [mul_extend.yaml](test/golden/mul_extend.yaml) — умножение с двойной точностью
  - [prob2.yaml](test/golden/prob2.yaml) — задача 6 проекта Эйлера - найти разницу между суммой квадратов первых ста натуральных чисел и квадратом их суммы
  - [sort.yaml](test/golden/sort.yaml) — сортировка чисел, объявленных в секции данных
### Результаты тестирования:
```
poetry run pytest -v
======================================================================= test session starts ========================================================================
platform win32 -- Python 3.10.8, pytest-7.4.4, pluggy-1.6.0 -- C:\Users\almet\AppData\Local\pypoetry\Cache\virtualenvs\csa-lab4-BXh0LHka-py3.10\Scripts\python.exe   
cachedir: .pytest_cache
rootdir: C:\Users\almet\PycharmProjects\csa-lab4-1
configfile: pyproject.toml
plugins: golden-0.2.2
collected 6 items                                                                                                                                                   

test/golden_test.py::test_translator_and_machine[golden/cat.yaml] PASSED                                                                                      [ 16%]
test/golden_test.py::test_translator_and_machine[golden/hello.yaml] PASSED                                                                                    [ 33%]
test/golden_test.py::test_translator_and_machine[golden/hello_user.yaml] PASSED                                                                               [ 50%]
test/golden_test.py::test_translator_and_machine[golden/mul_extend.yaml] PASSED                                                                               [ 66%]
test/golden_test.py::test_translator_and_machine[golden/prob2.yaml] PASSED                                                                                    [ 83%]
test/golden_test.py::test_translator_and_machine[golden/sort.yaml] PASSED                                                                                     [100%]

======================================================================== 6 passed in 2.25s ========================================================================= 
```
