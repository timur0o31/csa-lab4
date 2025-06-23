"""Golden тесты транслятора и машины.

Конфигурационнфе файлы: "golden/*_bf.yml"
"""

import contextlib
import io
import logging
import os
import tempfile

from src import machine, translator
import pytest

MAX_LOG = 4000


@pytest.mark.golden_test("golden/*.yaml")
def test_translator_and_machine(golden, caplog):
    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdirname:
        source = os.path.join(tmpdirname, "source.fs")
        input_stream = os.path.join(tmpdirname, "input.txt")
        target_instr = os.path.join(tmpdirname, "target_instructions.bin")
        target_data = os.path.join(tmpdirname, "target_data.bin")
        target_instr_hex = os.path.join(tmpdirname, "target_instructions.bin.hex")
        target_data_hex = os.path.join(tmpdirname, "target_data.bin.hex")

        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["in_source"])
        with open(input_stream, "w", encoding="utf-8") as file:
            file.write(golden["in_stdin"])

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.main(source, target_instr, target_data)
            print("============================================================")
            machine.main(target_instr, target_data, input_stream)

        with open(target_instr, "rb") as file:
            instructions = file.read()
        with open(target_instr_hex, encoding="utf-8") as file:
            instructions_hex = file.read()
        with open(target_data, "rb") as file:
            data = file.read()
        with open(target_data_hex, encoding="utf-8") as file:
            data_hex = file.read()

        assert instructions == golden.out["out_instructions"]
        assert instructions_hex == golden.out["out_instructions_hex"]
        assert data_hex == golden.out["out_data_hex"]
        assert data == golden.out["out_data"]
        assert stdout.getvalue() == golden.out["out_stdout"]
        assert caplog.text[0:MAX_LOG] + "EOF" == golden.out["out_log"]
