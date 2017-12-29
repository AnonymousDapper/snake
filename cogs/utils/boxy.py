import re

class Text:
    """
    ANSI text color codes for easy formatting
    """

    black = "\033[30m"
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    blue = "\033[34m"
    magenta = "\033[35m"
    cyan = "\033[36m"
    white = "\033[37m"

    b_black = "\033[90m"
    b_red = "\033[91m"
    b_green = "\033[92m"
    b_yellow = "\033[93m"
    b_blue = "\033[94m"
    b_magenta = "\033[95m"
    b_cyan = "\033[96m"
    b_white = "\033[97m"

def paint(text, color):
    if hasattr(Text, color):
        return f"{getattr(Text, color)}{text}\033[0m"
    raise ValueError(f"invalid color name: {color}")

class Boxy:
    def __init__(self, **kwargs):
        self.line_def = kwargs.get("lines") or ["═", "║", "╔", "╗", "╚", "╝"]

        self.line_def = ["-", "|", "+", "+", "+", "+"] if str(kwargs.get("line_type")).lower() == "ascii" else self.line_def
        self.line_def = ["━", "┃", "┏", "┓", "┗", "┛"] if str(kwargs.get("line_type")).lower() == "single" else self.line_def
        self.line_def = ["─", "│", "┌", "┐", "└", "┘"] if str(kwargs.get("line_type")).lower() == "thin" else self.line_def
        self.line_def = ["═", "║", "╔", "╗", "╚", "╝"] if str(kwargs.get("line_type")).lower() == "default" else self.line_def

        self.header = kwargs.get("header") or ""
        self.header_sep = kwargs.get("header_sep") or ["[", "]"]

        self.footer = kwargs.get("footer") or ""
        self.footer_sep = kwargs.get("footer_sep") or ["[", "]"]

        color = kwargs.get("color")
        self.color = color if hasattr(Text, str(color)) else "white"

        header_color = kwargs.get("header_color")
        self.header_color = header_color if hasattr(Text, str(header_color)) else "white"

        footer_color = kwargs.get("footer_color")
        self.footer_color = footer_color if hasattr(Text, str(footer_color)) else "white"

        text_color = kwargs.get("text_color")
        self.text_color = text_color if hasattr(Text, str(text_color)) else "white"

        self.max_length = kwargs.get("max_length")

        self.filter_regex = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]")

    def update(self, **kwargs):
        line_type = str(kwargs.get("line_type")).lower()

        if line_type == "ascii":
            self.line_def = ["-", "|", "+", "+", "+", "+"]

        elif line_type == "single":
            self.line_def = ["━", "┃", "┏", "┓", "┗", "┛"]

        elif line_type == "thin":
            self.line_def = ["─", "│", "┌", "┐", "└", "┘"]

        elif line_type == "default":
            self.line_def = ["═", "║", "╔", "╗", "╚", "╝"]

        self.line_def = kwargs.get("lines") or self.line_def

        if "header" in kwargs:
            self.header = kwargs.get("header")

        self.header_sep = kwargs.get("header_sep") or self.header_sep

        if "footer" in kwargs:
            self.footer = kwargs.get("footer")

        self.footer_sep = kwargs.get("footer_sep") or self.footer_sep

        if "color" in kwargs:
            color = kwargs.get("color")
            self.color = color if hasattr(Text, str(color)) else "white"

        if "header_color" in kwargs:
            header_color = kwargs.get("header_color")
            self.header_color = header_color if hasattr(Text, str(header_color)) else "white"

        if "footer_color" in kwargs:
            footer_color = kwargs.get("footer_color")
            self.footer_color = footer_color if hasattr(Text, str(footer_color)) else "white"

        if "text_color" in kwargs:
            text_color = kwargs.get("text_color")
            self.text_color = text_color if hasattr(Text, str(text_color)) else "white"

        self.max_length = kwargs.get("max_length") or self.max_length

    def reset(self):
        self.line_def = ["═", "║", "╔", "╗", "╚", "╝"]

        self.header = ""
        self.header_sep = ["[", "]"]

        self.footer = ""
        self.footer_sep = ["[", "]"]

        self.color = "white"
        self.header_color = "white"
        self.footer_color = "white"
        self.text_color = "white"

        self.max_length = None

    def _filter_data(self, data):
        clean_data = []
        for text in data:
            clean_data.append(self.filter_regex.sub("", text))

        return clean_data


    def build_box(self, raw_data):
        x_char, y_char, nw_corner, ne_corner, sw_corner, se_corner = self.line_def
        box_string = ""

        data_idx = 0

        data = self._filter_data(raw_data)

        if not self.max_length:
            max_length = max(len(line) for line in data)
        else:
            max_length = self.max_length

        total_length = max_length + 2

        # Header line
        if self.header or len(str(self.header)) > max_length:
            header = f" {paint(self.header, self.header_color)} "
            header_length = len(header) - 7

            char_delta = ((total_length - header_length) // 2)

            box_string += f"{getattr(Text, self.color)}{nw_corner}{x_char * char_delta}{self.header_sep[0]}\033[0m{header}{getattr(Text, self.color)}{self.header_sep[1]}{x_char * (char_delta + (0 if (header_length % 2 == max_length % 2) else 1))}{ne_corner}\033[0m\n"
        else:
            box_string += f"{getattr(Text, self.color)}{nw_corner}{x_char * total_length}{ne_corner}\033[0m\n"

        # Content lines
        for line_text in data:
            box_string += f"{getattr(Text, self.color)}{y_char}\033[0m {getattr(Text, self.text_color)}{raw_data[data_idx]}\033[0m {' ' * (max_length - len(line_text))}{getattr(Text, self.color)}{y_char}\033[0m\n"

            data_idx += 1

        # Footer line
        if self.footer or len(str(self.footer)) > max_length:
            footer = f" {paint(self.footer, self.footer_color)} "
            footer_length = len(footer) - 7

            char_delta = ((total_length - footer_length) // 2)

            box_string += f"{getattr(Text, self.color)}{sw_corner}{x_char * char_delta}{self.footer_sep[0]}\033[0m{footer}{getattr(Text, self.color)}{self.footer_sep[1]}{x_char * (char_delta + (0 if (footer_length % 2 == max_length % 2) else 1))}{se_corner}\033[0m\n"
        else:
            box_string += f"{getattr(Text, self.color)}{sw_corner}{x_char * total_length}{se_corner}\033[0m\n"


        return box_string

    def __call__(self, data):
        return self.build_box(data)

    def __repr__(self):
        return f"<Boxy(color={self.color}, text_color={self.text_color}, header_color={self.header_color}, footer_color={self.footer_color}>"

if __name__ == "__main__":
    boxer = Boxy(header="System Info", footer="BETA - unstable", text_color="magenta")
    print(boxer.build_box(["User: Dapper", "Python Version: 3.6.1"]))

    boxer.update(header="Thin Lines", line_type="thin", footer=None, text_color=None)
    print(boxer.build_box(["This is a thin line", "So is this", "And this"]))

    boxer.update(header=None, line_type="ascii")
    print(boxer.build_box(["These lines", "Can be used on a system", "That doesn't support extended Unicode characters"]))

    boxer.update(header="No color", color="green", footer="Maybe cyan?", footer_color="cyan", line_type="single")
    print(boxer.build_box(["We can even do color!", "Separate colors for", "  1) Header", "  2) Body", "  3) And Footer, yay!"]))

    boxer.update(header="Show some school spirit!", color="b_yellow", header_color="blue", footer=None)
    print(boxer.build_box(["These aren't the colors for my school", "They're the colors for my old school"]))

    boxer.update(footer="That's not even a real color", color="NONE is BEST", header="########################")
    print(boxer.build_box(["Yea, it even has some fail-safe features", "This color string is `NONE is BEST`"]))

    boxer.update(header_color="blue", footer_color="blue", header_sep=["<", ">"], footer_sep=["<", ">"], color="blue", text_color="green", header="Buffer Box", footer="Battery Cond: OK", max_length=20)
    print(boxer.build_box(["####################"]))

    boxer.update(text_color="yellow", footer="Battery Cond: Good")
    print(boxer.build_box(["############"]))

    boxer.update(text_color="red", footer="Battery Cond: Poor")
    print(boxer.build_box(["########"]))

    boxer.reset()
    print(boxer.build_box(["This is after a call to `reset()`"]))

    import time

    boxer.update(color="blue", header="Auxiliary Battery", max_length=50)

    def bat(percent):
        amnt = int(50 * (percent / 100))
        amnt_str = "#" * amnt
        color = ""
        status = ""
        if percent < 25:
            status = "Poor"
            color = "red"
        elif percent < 50:
            status = "Fair"
            color = "yellow"
        elif percent < 75:
            status = "Good"
            color = "cyan"
        elif percent < 100:
            status = "OK"
            color = "green"
        elif percent == 100:
            status = "Perfect"
            color = "b_green"
        boxer.update(footer=f"Condition: {status} ({percent}%)", text_color=color)
        return boxer([amnt_str])

    for i in range(100, -1, -1):
        print(bat(i))
        time.sleep(.125)