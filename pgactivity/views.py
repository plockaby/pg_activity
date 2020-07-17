from textwrap import dedent
from typing import Iterable, Optional, Tuple

from blessed import Terminal
import humanize

from .keys import BINDINGS, MODES
from .types import DBInfo, DurationMode, Host, MemoryInfo, SystemInfo


def help(term: Terminal, version: str) -> None:
    """Render help menu.

    >>> term = Terminal()
    >>> help(term, "2.1")
    pg_activity 2.1 - https://github.com/dalibo/pg_activity
    Released under PostgreSQL License.
    <BLANKLINE>
       Up/Down: scroll process list
             C: activate/deactivate colors
         Space: pause
             r: sort by READ/s desc. (activities)
             v: change display mode
             w: sort by WRITE/s desc. (activities)
             q: quit
             +: increase refresh time (max:5s)
             m: sort by MEM% desc. (activities)
             -: decrease refresh time (min:0.5s)
             t: sort by TIME+ desc. (activities)
             R: force refresh
             T: change duration mode
             D: force refresh database size
    Mode
          F1/1: running queries
          F2/2: waiting queries
          F3/3: blocking queries
    <BLANKLINE>
    Press any key to exit.
    """
    intro = dedent(
        f"""\
    {term.bold_green}pg_activity {version} - https://github.com/dalibo/pg_activity
    {term.normal}Released under PostgreSQL License.
    """
    )

    def render_mapping(keys: Iterable[Tuple[str, str]]) -> str:
        return "\n".join(
            f"{term.bright_cyan}{key.rjust(10)}{term.normal}: {text}"
            for key, text in keys
        )

    footer = "\nPress any key to exit."
    print(term.home + term.clear + intro)
    print(render_mapping(BINDINGS))
    print("Mode")
    print(render_mapping(MODES))
    print(footer)


def header(
    term: Terminal,
    host: Host,
    dbinfo: DBInfo,
    tps: int,
    active_connections: int,
    duration_mode: DurationMode,
    refresh_time: float,
    max_iops: int = 0,
    system_info: Optional[SystemInfo] = None,
) -> None:
    """Display window header.

    >>> from pgactivity.types import IOCounters, LoadAverage
    >>> term = Terminal()

    Remote host:

    >>> host = Host("PostgreSQL 9.6", "server", "pgadm", "server.prod.tld", 5433, "app")
    >>> dbinfo = DBInfo(10203040506070809, 9999)

    >>> header(term, host, dbinfo, 12, 0, DurationMode.backend, refresh_time=10)
    PostgreSQL 9.6 - server - pgadm@server.prod.tld:5433/app - Ref.: 10s
     Size:      10.2 PB -   10.0 kB/s     | TPS:              12      | Active connections:               0      | Duration mode:     backend

    Local host, with priviledged access:

    >>> host = Host("PostgreSQL 13.1", "localhost", "tester", "host", 5432, "postgres")
    >>> dbinfo = DBInfo(123456789, 12)
    >>> vmem = MemoryInfo(total=6175825920, percent=42.5, used=2007146496)
    >>> swap = MemoryInfo(total=6312423424, used=2340, percent=0.0)
    >>> ios = IOCounters(read_bytes=128, write_bytes=8, read_count=6, write_count=9)
    >>> load = LoadAverage(0.25, 0.19, 0.39)
    >>> sysinfo = SystemInfo(vmem, swap, load, ios)

    >>> header(term, host, dbinfo, 1, 79, DurationMode.query, refresh_time=2,
    ...        max_iops=12, system_info=sysinfo)
    PostgreSQL 13.1 - localhost - tester@host:5432/postgres - Ref.: 2s
     Size:     123.5 MB -  12 Bytes/s     | TPS:               1      | Active connections:              79      | Duration mode:       query
     Mem.:     42.5% -    2.0 GB/6.2 GB   | IO Max:                 12/s
     Swap:      0.0% -    2.3 kB/6.3 GB   | Read:     128 Bytes/s -      6/s
     Load:         0.25 0.19 0.39         | Write:       8 Bytes/s -      9/s
    """
    pg_host = f"{host.user}@{host.host}:{host.port}/{host.dbname}"
    print(
        " - ".join(
            [
                host.pg_version,
                f"{term.bold}{host.hostname}{term.normal}",
                f"{term.cyan}{pg_host}{term.normal}",
                f"Ref.: {refresh_time}s",
            ]
        )
    )

    def row(*columns: Tuple[str, str, int]) -> str:
        return " | ".join(
            f"{title}: {value.center(width)}" for title, value, width in columns
        ).rstrip()

    def iprint(text: str, indent: int = 1) -> None:
        print(" " * indent + text)

    total_size = humanize.naturalsize(dbinfo.total_size)
    size_ev = humanize.naturalsize(dbinfo.size_ev)
    iprint(
        row(
            ("Size", f"{total_size.rjust(8)} - {size_ev.rjust(9)}/s", 30),
            ("TPS", f"{term.bold_green}{str(tps).rjust(11)}{term.normal}", 20),
            (
                "Active connections",
                f"{term.bold_green}{str(active_connections).rjust(11)}{term.normal}",
                20,
            ),
            (
                "Duration mode",
                f"{term.bold_green}{duration_mode.name.rjust(11)}{term.normal}",
                5,
            ),
        )
    )

    def render_meminfo(m: MemoryInfo) -> str:
        used, total = humanize.naturalsize(m.used), humanize.naturalsize(m.total)
        return f"{m.percent:6}% - {used.rjust(9)}/{total}"

    def render_ios(nbytes: int, count: int) -> str:
        hbytes = humanize.naturalsize(nbytes)
        return f"{hbytes.rjust(10)}/s - {count:6}/s"

    if system_info is not None:
        col_width = 30  # TODO: use screen size
        iprint(
            row(
                ("Mem.", render_meminfo(system_info.memory), col_width),
                ("IO Max", f"{max_iops:8}/s", col_width),
            )
        )
        iprint(
            row(
                ("Swap", render_meminfo(system_info.swap), col_width),
                (
                    "Read",
                    render_ios(system_info.ios.read_bytes, system_info.ios.read_count),
                    col_width,
                ),
            )
        )
        load = system_info.load
        iprint(
            row(
                ("Load", f"{load.avg1:.2} {load.avg5:.2} {load.avg15:.2}", col_width),
                (
                    "Write",
                    render_ios(
                        system_info.ios.write_bytes, system_info.ios.write_count
                    ),
                    col_width,
                ),
            )
        )
