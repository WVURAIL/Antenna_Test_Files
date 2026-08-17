"""Interactively acquire antenna S11 measurements from a Keysight FieldFox.

The module is safe to import: hardware is opened only from :func:`main`.
FieldFox SCPI reference:
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


def set_freq_lims(vna, start_hz: float, stop_hz: float) -> None:
    """Set the analyzer sweep limits in hertz."""
    vna.write(f"SENSe:FREQuency:STARt {start_hz}")
    vna.write(f"SENSe:FREQuency:STOp {stop_hz}")


def check_power_mode(vna) -> None:
    """Print the analyzer's automatic-level-control mode."""
    mode = vna.query("SOURce:POWer:ALC:MODE?").strip()
    print(f"Current output power mode is {mode}")


def set_power_mode(vna, output_power: str) -> None:
    """Set and report the analyzer's automatic-level-control mode."""
    print(f"Setting output power mode to {output_power}")
    vna.write(f"SOURce:POWer:ALC:MODE {output_power}")
    check_power_mode(vna)


def _query_trace(vna) -> np.ndarray:
    """Return the selected formatted trace as floating-point values."""
    response = vna.query("CALCulate:DATA:FDaTa?")
    values = [value.strip() for value in response.strip().split(",")]
    return np.asarray([float(value) for value in values if value], dtype=float)


def measure_s_parameter(
    vna,
    measurement: str,
    output_power: str,
    serial_num: str,
    start_hz: float,
    stop_hz: float,
    plot_directory: Path,
    show_plots: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """Acquire the log-magnitude and complex trace for one S-parameter."""
    print("Setting frequency limits")
    set_freq_lims(vna, start_hz, stop_hz)
    set_power_mode(vna, output_power)
    print(f"Measuring {measurement} with output mode {output_power}")

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
        plot_directory / f"{measurement}_{serial_num}.png",
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
    return magnitude_db, real + 1j * imaginary


def _save_antenna_port(
    vna,
    serial_num: str,
    start_hz: float,
    stop_hz: float,
    touchstone_directory: Path,
    s11_plot_directory: Path,
    smith_chart_directory: Path,
    show_plots: bool,
) -> None:
    """Acquire and save one antenna port."""
    _, s11_raw = measure_s_parameter(
        vna=vna,
        measurement="S11",
        output_power="HIGH",
        serial_num=serial_num,
        start_hz=start_hz,
        stop_hz=stop_hz,
        plot_directory=s11_plot_directory,
        show_plots=show_plots,
    )
    frequency_values = np.linspace(start_hz, stop_hz, s11_raw.size)
    frequency = rf.Frequency.from_f(frequency_values, unit="Hz")
    network = rf.Network(
        name=serial_num,
        s=s11_raw[:, np.newaxis, np.newaxis],
        frequency=frequency,
        z0=50,
    )
    print(network)
    network.write_touchstone(filename=serial_num, dir=str(touchstone_directory))

    figure, axis = plt.subplots()
    network.plot_s_smith(ax=axis)
    axis.set_title(f"{serial_num} Smith Chart")
    figure.savefig(smith_chart_directory / f"{serial_num}.jpg", bbox_inches="tight")
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
    """Run the original prompt-driven antenna measurement workflow."""
    output_root = args.output_root.resolve()
    touchstone_directory = output_root / "Results" / "Touchstone_Files"
    s11_plot_directory = output_root / "Results" / "S11_Plots"
    smith_chart_directory = output_root / "Results" / "Smith_Charts"
    for directory in (
        touchstone_directory,
        s11_plot_directory,
        smith_chart_directory,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    confirmation = input(
        "Connect and power on the VNA, then enter y to continue: "
    ).strip().lower()
    if confirmation != "y":
        print("Measurement cancelled.")
        return

    manager, vna = _open_vna(args)
    try:
        while True:
            serial = input("Enter antenna serial number: ").strip()
            if not serial:
                print("A serial number is required.")
                continue
            if "/" in serial or "\\" in serial:
                print("The serial number cannot contain path separators.")
                continue

            for port in ("P1", "P2"):
                input(f"Connect the VNA to {port}, then press Enter: ")
                _save_antenna_port(
                    vna=vna,
                    serial_num=f"{serial}_{port}",
                    start_hz=args.start_hz,
                    stop_hz=args.stop_hz,
                    touchstone_directory=touchstone_directory,
                    s11_plot_directory=s11_plot_directory,
                    smith_chart_directory=smith_chart_directory,
                    show_plots=not args.no_show,
                )

            again = input(
                "Test another antenna? Enter 1 to continue or 0 to finish: "
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
        "--output-root",
        type=Path,
        default=Path.cwd(),
        help="repository/output root containing Results (default: current directory)",
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
