"""Offline checks for measurement labels and per-device output names."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def load_functions(filename, namespace):
    source = ROOT / filename
    tree = ast.parse(source.read_text(), filename=str(source))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             or (isinstance(node, ast.ImportFrom) and node.module == "__future__")]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)


class MeasurementOutputTests(unittest.TestCase):
    def test_log_magnitude_uses_ratio_units(self):
        for filename in ("Measure_S.py", "Measure_S11.py"):
            with self.subTest(filename=filename):
                instrument = Mock()
                instrument.query.side_effect = lambda command: (
                    "0.5,0.25\n" if command == "CALCulate:DATA:FDaTa?" else "LOW\n")
                figure, axis = Mock(), Mock()
                plot = Mock()
                plot.subplots.return_value = (figure, axis)
                namespace = {"np": np, "plt": plot,
                             "time": SimpleNamespace(sleep=Mock())}
                load_functions(filename, namespace)
                kwargs = dict(vna=instrument, measurement="S11", serial_num="LNA101",
                              start_hz=1e7, stop_hz=2e9, show_plots=False)
                if filename == "Measure_S.py":
                    kwargs["output_directory"] = Path("offline-output")
                else:
                    kwargs.update(output_power="LOW", plot_directory=Path("offline-output"))
                with patch("builtins.print"):
                    namespace["measure_s_parameter"](**kwargs)
                axis.set_ylabel.assert_called_once_with("S11 magnitude (dB)")

    def test_comparison_plots_preserve_both_device_serials(self):
        figure, axis = Mock(), Mock()
        plot = Mock()
        plot.subplots.return_value = (figure, axis)

        def network_factory(**kwargs):
            network = Mock()
            network.name = kwargs["name"]
            return network

        namespace = {
            "np": np, "plt": plot,
            "rf": SimpleNamespace(Network=Mock(side_effect=network_factory),
                Frequency=SimpleNamespace(from_f=Mock(return_value=object()))),
            "S_PARAMETERS": ("S11", "S12", "S21", "S22"),
        }
        load_functions("Measure_S.py", namespace)
        traces = {name: np.array([0.5 + 0.1j, 0.25 - 0.1j])
                  for name in namespace["S_PARAMETERS"]}
        for serial in ("LNA101", "LNA102"):
            namespace["_save_measurement_set"](
                serial, traces, 1e7, 2e9, Path("offline-output"), False)
        self.assertEqual([call.args[0] for call in figure.savefig.call_args_list],
                         [Path("offline-output/LNA101_multi_comparison.jpg"),
                          Path("offline-output/LNA102_multi_comparison.jpg")])
        self.assertEqual([call.args[0] for call in axis.set_title.call_args_list],
                         ["LNA101 S Parameters", "LNA102 S Parameters"])


if __name__ == "__main__":
    unittest.main()
