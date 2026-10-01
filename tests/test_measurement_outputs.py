"""Offline checks for measurement labels and per-device output names."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


class MeasurementOutputTests(unittest.TestCase):
    def test_log_magnitude_uses_ratio_units(self):
        for filename in ("Measure_S.py", "Measure_S11.py"):
            with self.subTest(filename=filename):
                source = ROOT / filename
                tree = ast.parse(source.read_text(), filename=str(source))
                functions = [node for node in tree.body
                             if isinstance(node, ast.FunctionDef)]
                instrument = Mock()
                instrument.query.side_effect = lambda command: (
                    "0.5,0.25\n" if command == "CALCulate:DATA:FDaTa?" else "LOW\n")
                plot = Mock()
                namespace = {"np": np, "VNA": instrument, "plt": plot,
                             "time": SimpleNamespace(sleep=Mock())}
                exec(compile(ast.Module(body=functions, type_ignores=[]),
                             str(source), "exec"), namespace)
                with patch("builtins.print"):
                    namespace["measure_s_parameter"](
                        "S11", "LOW", "LNA101", 1e7, 2e9)
                plot.ylabel.assert_called_once_with("dB")

    def test_comparison_plots_preserve_both_device_serials(self):
        source = ROOT / "Measure_S.py"
        tree = ast.parse(source.read_text(), filename=str(source))
        loop = next(node for node in tree.body if isinstance(node, ast.While))
        measurement = next(node for node in loop.body if isinstance(node, ast.If))
        start = next(i for i, node in enumerate(measurement.body)
                     if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "serial_num_2"
                             for target in node.targets))
        # Execute the actual final export/plot block with only output mocks.
        fragment = ast.Module(body=measurement.body[start:], type_ignores=[])
        plot = Mock()
        namespace = {"plt": plot, **{name: Mock() for name in
                     ("nw2", "nw3", "nw4", "nw5", "nw6")}}
        for serial in ("LNA101", "LNA102"):
            namespace["serial_num_1"] = serial
            exec(compile(fragment, str(source), "exec"), namespace)
        paths = [call.args[0] for call in plot.savefig.call_args_list]
        self.assertEqual(len(set(paths)), 2)
        self.assertTrue(paths[0].endswith("LNA101_multi_comparison.jpg"))
        self.assertTrue(paths[1].endswith("LNA102_multi_comparison.jpg"))
        self.assertEqual([call.args[0] for call in plot.title.call_args_list],
                         ["LNA101 S Parameters", "LNA102 S Parameters"])


if __name__ == "__main__":
    unittest.main()
