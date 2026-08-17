"""Interactively acquire a complete two-port S-parameter measurement.

This legacy LNA utility is safe to import: hardware is opened only from
:func:`main`. FieldFox SCPI reference:
https://helpfiles.keysight.com/csg/FFProgrammingHelpWebHelp/Programming_the_FieldFox.htm
"""

from __future__ import annotations

import argparse
from pathlib import Path
import time

import matplotlib.pyplot as plt
import numpy as np
import pyvisa
import skrf as rf


DEFAULT_START_HZ = 10_000_000.0
DEFAULT_STOP_HZ = 2_000_000_000.0
S_PARAMETERS = ("S11", "S12", "S21", "S22")


def set_freq_lims(vna, start_hz: float, stop_hz: float) -> None:
    """Set the analyzer sweep limits in hertz."""
    vna.write(f"SENSe:FREQuency:STARt {start_hz}")
    vna.write(f"SENSe:FREQuency:STOp {stop_hz}")


def set_power_mode(vna, output_power: str) -> None:
    """Set and report the analyzer's automatic-level-control mode."""
    print(f"Setting output power mode to {output_power}")
    vna.write(f"SOURce:POWer:ALC:MODE {output_power}")
    mode = vna.query("SOURce:POWer:ALC:MODE?").strip()
    print(f"Current output power mode is {mode}")


def _query_trace(vna) -> np.ndarray:
    """Return the selected formatted trace as floating-point values."""
    response = vna.query("CALCulate:DATA:FDaTa?")
    values = [value.strip() for value in response.strip().split(",")]
    return np.asarray([float(value) for value in values if value], dtype=float)


def measure_s_parameter(
    vna,
    measurement: str,
    serial_num: str,
    start_hz: float,
    stop_hz: float,
    output_directory: Path,
    show_plots: bool,
) -> np.ndarray:
    """Acquire one complex S-parameter trace and save its magnitude plot."""
    set_freq_lims(vna, start_hz, stop_hz)
    set_power_mode(vna, "LOW")
    print(f"Measuring {measurement}")
    vna.write(f":CALCulate:PARameter1:DEFine {measurement}")
    vna.write(":CALCulate:SELected:FORMat MLOGarithmic")
    time.sleep(1)
    vna.write(":DISPlay:WINDow:TRACe:Y:SCALe:AUTO")
    magnitude_db = _query_trace(vna)

    frequencies_mhz = np.linspace(
        start_hz / 1e6, stop_hz / 1e6, magnitude_db.size
    )
    figure, axis = plt.subplots()
    axis.plot(frequencies_mhz, magnitude_db)
    axis.set_xlabel("Frequency (MHz)")
    axis.set_ylabel(f"{measurement} magnitude (dB)")
    axis.set_title(f"{measurement}_{serial_num}")
    figure.savefig(
        output_directory / f"{measurement}_{serial_num}.png",
        bbox_inches="tight",
    )
    if show_plots:
        plt.show()
    plt.close(figure)

    vna.write(":CALCulate:SELected:FORMat REAL")
    time.sleep(1)
    real = _query_trace(vna)
    vna.write(":CALCulate:SELected:FORMat IMAG")
    time.sleep(1)
    imaginary = _query_trace(vna)
    if real.size != imaginary.size:
        raise RuntimeError("VNA returned different REAL and IMAG trace lengths")
    print(f"Done measuring {measurement}")
    return real + 1j * imaginary


def _one_port_network(
    name: str, trace: np.ndarray, frequency: rf.Frequency
) -> rf.Network:
    """Build a one-port network without relying on implicit array reshaping."""
    return rf.Network(
        name=name,
        s=trace[:, np.newaxis, np.newaxis],
        frequency=frequency,
        z0=50,
    )


def _save_measurement_set(
    serial_num: str,
    traces: dict[str, np.ndarray],
    start_hz: float,
    stop_hz: float,
    output_directory: Path,
    show_plots: bool,
) -> None:
    """Write individual traces, a complex two-port file, and a comparison plot."""
    point_counts = {trace.size for trace in traces.values()}
    if len(point_counts) != 1:
        raise RuntimeError("S-parameter traces have different point counts")
    point_count = point_counts.pop()
    frequency_values = np.linspace(start_hz, stop_hz, point_count)
    frequency = rf.Frequency.from_f(frequency_values, unit="Hz")

    networks = {
        parameter: _one_port_network(
            f"{serial_num}_{parameter}", trace, frequency
        )
        for parameter, trace in traces.items()
    }
    for network in networks.values():
        network.write_touchstone(filename=network.name, dir=str(output_directory))

    # Preserve complex phase by declaring the matrix's dtype explicitly.
    s_matrix = np.zeros((point_count, 2, 2), dtype=complex)
    s_matrix[:, 0, 0] = traces["S11"]
    s_matrix[:, 0, 1] = traces["S12"]
    s_matrix[:, 1, 0] = traces["S21"]
    s_matrix[:, 1, 1] = traces["S22"]
    two_port = rf.Network(
        name=serial_num,
        s=s_matrix,
        frequency=frequency,
        z0=50,
    )
    two_port.write_touchstone(filename=serial_num, dir=str(output_directory))

    figure, axis = plt.subplots()
    for parameter in S_PARAMETERS:
        networks[parameter].plot_s_db(
            m=0,
            n=0,
            label=parameter,
            ax=axis,
        )
    axis.set_title(f"{serial_num} S Parameters")
    figure.savefig(
        output_directory / f"{serial_num}_multi_comparison.jpg",
        bbox_inches="tight",
    )
    if show_plots:
        plt.show()
    plt.close(figure)


def _open_vna(args: argparse.Namespace):
    """Open the requested VISA resource and configure network-analyzer mode."""
    manager = (
        pyvisa.ResourceManager(args.visa_library)
        if args.visa_library
        else pyvisa.ResourceManager()
    )
    resources = manager.list_resources()
    resource_name = args.resource or (resources[0] if resources else None)
    if resource_name is None:
        manager.close()
        raise RuntimeError(
            "No VISA instruments found; provide one explicitly with --resource"
        )

    print(f"Opening VISA resource {resource_name}")
    vna = manager.open_resource(resource_name)
    vna.timeout = args.timeout_ms
    print(vna.query("*IDN?").strip())
    print(f"Available modes: {vna.query('INSTrument:CATalog?').strip()}")
    operation_complete = vna.query('INST "NA";*OPC?').strip()
    if not operation_complete.startswith("1"):
        vna.close()
        manager.close()
        raise RuntimeError("The analyzer did not confirm network-analyzer mode")
    return manager, vna


def run_interactive(args: argparse.Namespace) -> None:
    """Run the original prompt-driven two-port measurement workflow."""
    output_directory = args.output_dir.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    confirmation = input(
        "Connect and power on the VNA, then enter y to continue: "
    ).strip().lower()
    if confirmation != "y":
        print("Measurement cancelled.")
        return

    manager, vna = _open_vna(args)
    try:
        while True:
            serial = input("Enter LNA serial number: ").strip()
            if not serial:
                print("A serial number is required.")
                continue
            if "/" in serial or "\\" in serial:
                print("The serial number cannot contain path separators.")
                continue
            input("Connect the VNA to the LNA, then press Enter: ")
            traces = {
                parameter: measure_s_parameter(
                    vna=vna,
                    measurement=parameter,
                    serial_num=serial,
                    start_hz=args.start_hz,
                    stop_hz=args.stop_hz,
                    output_directory=output_directory,
                    show_plots=not args.no_show,
                )
                for parameter in S_PARAMETERS
            }
            _save_measurement_set(
                serial_num=serial,
                traces=traces,
                start_hz=args.start_hz,
                stop_hz=args.stop_hz,
                output_directory=output_directory,
                show_plots=not args.no_show,
            )
            again = input(
                "Test another LNA? Enter 1 to continue or 0 to finish: "
            ).strip()
            if again != "1":
                break
    finally:
        vna.close()
        manager.close()
    print("Thanks for testing with us!")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--visa-library",
        help="VISA shared-library path; omit to let PyVISA select a backend",
    )
    parser.add_argument(
        "--resource",
        help="VISA resource name; omit to use the first discovered instrument",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("Results") / "LNA",
        help="directory for Touchstone files and plots (default: Results/LNA)",
    )
    parser.add_argument("--start-hz", type=float, default=DEFAULT_START_HZ)
    parser.add_argument("--stop-hz", type=float, default=DEFAULT_STOP_HZ)
    parser.add_argument("--timeout-ms", type=int, default=10_000)
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="save plots without opening interactive plot windows",
    )
    return parser


def main() -> None:
    """Parse command-line options and run the interactive acquisition."""
    args = build_parser().parse_args()
    if args.start_hz <= 0 or args.stop_hz <= args.start_hz:
        raise SystemExit("--start-hz must be positive and less than --stop-hz")
    run_interactive(args)


if __name__ == "__main__":
    main()
