"""
Utilities for working with a terminal
"""

from typing import Any, List, Optional, Tuple
import shutil
from .color import decolorize

def progress_bar(complete_pct: float,
                 width: Optional[int] = None,
                 done_char: str = "=",
                 undone_char: str = "-",
                 head_char: str = ">") -> str:
    """Format a progress bar showing the given percent complete with the given
    total width

    Args:
        complete_pct (float): Float value in [0, 1] showing percent complete
        width (Optional[int]): The width (in characters) of the full bar.
            Defaults to the width of the current terminal
        done_char (str): The character representing completion
        undone_char (str): The character representing incomplete
        head_char (str): The character representing the head of the completion
            arrow

    Returns:
        progress_bar_str (str): String for the progress bar
    """
    assert len(done_char) == 1
    assert len(undone_char) == 1
    assert len(head_char) == 1
    if width is None:
        width = shutil.get_terminal_size().columns
    n_done = int((width - 3) * complete_pct)
    n_undone = width - 3 - n_done
    return f"[{done_char * n_done}{head_char}{undone_char * n_undone}]"


def box(x: Any,
        char: str = "#",
        width: Optional[int] = None) -> str:
    """Render the content of the given string inside a box frame

    Args:
        x (Any): The printable value to be framed in the box
        char (str): The character to use for the box frame
        width (Optional[int]): The width of the box (defaults to terminal)

    Returns:
        boxed_text (str): The wrapped text inside the box
    """
    if width is None:
        width = shutil.get_terminal_size().columns
    x = str(x)
    raw_lines = x.split("\n")
    lines = []
    longest = 0
    max_len = width - 4
    for line in raw_lines:
        sublines, longest_subline_len = _word_wrap_to_len(line, max_len)
        lines += sublines
        longest = max(longest, longest_subline_len)
    out = f"{char * (longest + 4)}\n"
    for line in lines:
        padding = " " * (longest - _printed_len(line))
        out += f"{char} {line}{padding} {char}\n"
    out += f"{char * (longest + 4)}\n"
    return out


def table(columns: List[List[Any]],
          width: Optional[int] = None,
          max_width: Optional[int] = None,
          min_width: Optional[int] = None,
          row_dividers: bool = True,
          header: bool = True) -> str:
    """Encode the given columns as an ascii table

    Args:
        columns (List[List[Any]]): List of columns, each consisting of a list of
            string entries. The first entry in each column is considered the
            column header
        width (Optional[int]): The width of the table (defaults to terminal)
        max_width (Optional[int]): If no width given, upper bound on computed
            width based on content
        min_width (Optional[int]): If no width given, the lower bound on
            computed width based on content
        row_dividers (bool): Include dividers between rows
        header (bool): Include a special divider between header and rows

    Returns:
        table (str): The formatted table string
    """
    if max_width is None:
        max_width = shutil.get_terminal_size().columns
    if min_width is None:
        min_width = 2 * len(columns) + 1 if width is None else width

    columns = [[str(val) for val in col] for col in columns]

    max_col_width = max_width - 3 - 2 * (len(columns) - 1)
    widths = [
        min(max(_printed_len(x) for x in column), max_col_width) for column in columns
    ]

    total_width = sum([w + 3 for w in widths]) + 1
    table_width = max(min(total_width, max_width), min_width)
    usable_table_width = table_width - 1

    pcts = [float(w) / float(total_width) for w in widths]
    col_widths = [int(p * usable_table_width) + 3 for p in pcts]
    col_widths[-1] = usable_table_width - sum(col_widths[:-1])

    collapsed = [(i, w) for i, w in enumerate(col_widths) if w - 2 < 2]
    extra = sorted(
        [(w, i) for i, w in enumerate(col_widths) if (i, w) not in collapsed],
        key=lambda x: x[0],
    )
    for (i, w) in collapsed:
        assert len(extra) > 0 and extra[0][0] - w > 2, "No extra to borrow from"
        padding = 2 - w
        col_widths[extra[0][1]] = extra[0][0] - padding
        col_widths[i] = w + padding
        extra = sorted(extra, key=lambda x: x[0])

    wrapped_cols = []
    for i, col in enumerate(columns):
        wrapped_cols.append([])
        for entry in col:
            assert col_widths[i] - 2 > 1, f"Column width collapsed for col {i}"
            wrapped, _ = _word_wrap_to_len(entry, col_widths[i] - 2)
            wrapped_cols[-1].append(wrapped)

    out = _make_hline(table_width)
    n_rows = max([len(col) for col in columns])
    for r in range(n_rows):
        entries = [col[r] if r < len(col) else [""] for col in wrapped_cols]
        most_sublines = max([len(e) for e in entries])
        for i in range(most_sublines):
            line = ""
            for c, entry in enumerate(entries):
                val = entry[i] if len(entry) > i else ""
                line += "| {}{}".format(
                    val, " " * (col_widths[c] - _printed_len(val) - 2)
                )
            line += "|\n"
            out += line
        if r == 0:
            if header:
                out += _make_hline(table_width, char="=", edge="|")
            elif row_dividers:
                out += _make_hline(table_width, edge="|")
        elif r < n_rows - 1:
            if row_dividers:
                out += _make_hline(table_width, edge="|")
        else:
            out += _make_hline(table_width)

    return out

def _printed_len(x: str) -> int:
    """Get the length of the given string with non-printed characters removed"""
    return len(decolorize(x))


def _word_wrap_to_len(line: str, max_len: int) -> Tuple[List[str], int]:
    """Wrap the given line into a list of lines, each no longer than max_len
    using whitespace tokenization for word splitting.

    Args:
        line (str): The input line to be wrapped
        max_len (int): The max len for lines in the wrappe doutput

    Returns:
        sublines (List[str]): The lines wrapped to the target length
        longest (int): The length of the longest wrapped line (<= max_len)
    """
    if _printed_len(line) <= max_len:
        return [line], _printed_len(line)
    else:
        longest = 0
        sublines = []
        words = line.split(" ")
        while len(words):
            subline = ""
            while len(words):
                if _printed_len(subline) + _printed_len(words[0]) <= max_len:
                    subline += words[0] + " "
                    words = words[1:]
                elif _printed_len(words[0]) > max_len:
                    cutoff = max_len - _printed_len(subline) - 1
                    if cutoff <= 0:
                        break
                    else:
                        subline += words[0][:cutoff] + "- "
                        words[0] = words[0][cutoff:]
                else:
                    break
            subline = subline[:-1]
            longest = max(longest, _printed_len(subline))
            sublines.append(subline)
        return sublines, longest


def _make_hline(table_width: int, char: str = "-", edge: str = "+") -> str:
    return "{}{}{}\n".format(edge, char * (table_width - 2), edge)
