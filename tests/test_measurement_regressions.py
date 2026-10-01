"""Offline checks for the combined two-port measurement export."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]


class CombinedNetworkTests(unittest.TestCase):
    def test_combined_network_retains_complex_measurements(self):
        source = REPO_ROOT / "Measure_S.py"
        tree = ast.parse(source.read_text(), filename=str(source))
        definitions = [node for node in tree.body
                       if isinstance(node, ast.FunctionDef)
                       and node.name in {"_one_port_network", "_save_measurement_set"}]
        future_imports = [node for node in tree.body
                          if isinstance(node, ast.ImportFrom)
                          and node.module == "__future__"]
        self.assertEqual(len(definitions), 2)
        created = []

        def network_factory(**kwargs):
            network = Mock()
            network.name = kwargs["name"]
            created.append((kwargs, network))
            return network

        figure, axis = Mock(), Mock()
        frequency = object()
        namespace = {
            "np": np,
            "rf": SimpleNamespace(
                Frequency=SimpleNamespace(from_f=Mock(return_value=frequency)),
                Network=Mock(side_effect=network_factory),
            ),
            "plt": SimpleNamespace(
                subplots=Mock(return_value=(figure, axis)), close=Mock(), show=Mock()),
            "S_PARAMETERS": ("S11", "S12", "S21", "S22"),
        }
        fragment = ast.Module(body=future_imports + definitions, type_ignores=[])
        # Only the export helpers run, with file writers and plotting mocked.
        exec(compile(fragment, str(source), "exec"), namespace)
        traces = {
            "S11": np.array([0.6 + 0.8j, -0.2 + 0.4j]),
            "S12": np.array([0.1 - 0.2j, 0.3 + 0.5j]),
            "S21": np.array([2.0 + 3.0j, 4.0 - 5.0j]),
            "S22": np.array([-0.4 + 0.5j, 0.7 - 0.9j]),
        }
        output = Path("offline-output")
        namespace["_save_measurement_set"]("LNA42", traces, 1e7, 2e9, output, False)
        expected = np.array([
            [[0.6 + 0.8j, 0.1 - 0.2j], [2.0 + 3.0j, -0.4 + 0.5j]],
            [[-0.2 + 0.4j, 0.3 + 0.5j], [4.0 - 5.0j, 0.7 - 0.9j]],
        ])
        self.assertEqual(len(created), 5)
        combined_arguments, combined_network = created[-1]
        np.testing.assert_array_equal(combined_arguments["s"], expected)
        self.assertIs(combined_arguments["frequency"], frequency)
        combined_network.write_touchstone.assert_called_once_with(
            filename="LNA42", dir=str(output))
        for parameter, (arguments, network) in zip(namespace["S_PARAMETERS"], created):
            np.testing.assert_array_equal(arguments["s"][:, 0, 0], traces[parameter])
            network.write_touchstone.assert_called_once_with(
                filename="LNA42_" + parameter, dir=str(output))


if __name__ == "__main__":
    unittest.main()
