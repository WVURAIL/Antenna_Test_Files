"""Offline checks for the combined two-port measurement export."""

import ast
from pathlib import Path
import unittest

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]


class CombinedNetworkTests(unittest.TestCase):
    def test_combined_network_retains_complex_measurements(self):
        source = REPO_ROOT / "Measure_S.py"
        tree = ast.parse(source.read_text(), filename=str(source))
        assignments = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == "s":
                assignments.append(node)
            elif (isinstance(target, ast.Subscript)
                  and isinstance(target.value, ast.Name)
                  and target.value.id == "s"):
                assignments.append(node)
        assignments.sort(key=lambda node: node.lineno)
        self.assertEqual(len(assignments), 5)
        traces = {
            "S11_raw": np.array([0.6 + 0.8j, -0.2 + 0.4j]),
            "S12_raw": np.array([0.1 - 0.2j, 0.3 + 0.5j]),
            "S21_raw": np.array([2.0 + 3.0j, 4.0 - 5.0j]),
            "S22_raw": np.array([-0.4 + 0.5j, 0.7 - 0.9j]),
        }
        namespace = {"np": np, "f": np.array([1e7, 2e9]), **traces}
        fragment = ast.Module(body=assignments, type_ignores=[])
        # Only array assignments run; the instrument script is never imported.
        exec(compile(fragment, str(source), "exec"), namespace)
        expected = np.array([
            [[0.6 + 0.8j, 0.1 - 0.2j], [2.0 + 3.0j, -0.4 + 0.5j]],
            [[-0.2 + 0.4j, 0.3 + 0.5j], [4.0 - 5.0j, 0.7 - 0.9j]],
        ])
        np.testing.assert_array_equal(namespace["s"], expected)


if __name__ == "__main__":
    unittest.main()
