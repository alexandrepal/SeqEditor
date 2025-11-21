# SeqEditor is a CustomTkinter-based GUI that lets you write simple sequential/combinational logic 
# in a `.seq` DSL and flash it to an ATmega32u4 board (e.g., Adafruit ItsyBitsy 32u4 5V) using Arduino CLI.
# Nov. 2025 - Alexandre Passos de Almeida
# Version 7

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import re
import subprocess
import json
import os
import shutil

class SeqEditorApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        # ---------- Window setup ----------
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("Seq Editor")
        self.geometry("1000x650")

        # Grid layout for main window
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=0)  # hardware
        self.grid_rowconfigure(1, weight=0)  # clock
        self.grid_rowconfigure(2, weight=1)  # code
        self.grid_rowconfigure(3, weight=0)  # bottom buttons

        # ---------- Hardware section ----------
        self._create_hardware_section()

        # ---------- Clock section ----------
        self._create_clock_section()

        # ---------- Code + File Buttons section ----------
        self._create_code_section_with_file_buttons()

        # ---------- Bottom buttons (error label + Check + Flash) ----------
        self._create_bottom_buttons()

        # ---------- Board scan ------------
        self._initial_board_scan()

    # ============================================
    # Hardware section
    # ============================================
    def _create_hardware_section(self):
        hw_frame = ctk.CTkFrame(self)
        hw_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        hw_frame.grid_columnconfigure(1, weight=1)
        hw_frame.grid_columnconfigure(3, weight=1)
        hw_frame.grid_columnconfigure(4, weight=1)
        hw_frame.grid_columnconfigure(5, weight=1)

        # Port label + entry
        lbl_port = ctk.CTkLabel(hw_frame, text="Port:")
        lbl_port.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.entry_port = ctk.CTkEntry(hw_frame, width=180)
        self.entry_port.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Device label + entry
        lbl_dev = ctk.CTkLabel(hw_frame, text="Device:")
        lbl_dev.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        self.entry_device = ctk.CTkEntry(hw_frame, width=220)
        self.entry_device.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # SketchDir label + entry
        lbl_sketch = ctk.CTkLabel(hw_frame, text="SketchDir")
        lbl_sketch.grid(row=0, column=4, padx=5, pady=5, sticky="e")

        self.entry_sketch_dir = ctk.CTkEntry(hw_frame, width=220)
        self.entry_sketch_dir.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        # Default to user's home directory (e.g. /Users/you or C:\Users\you)
        try:
           home_dir = os.path.expanduser("~")
        except Exception:
           home_dir = ""
        self.entry_sketch_dir.insert(0, home_dir)

    # ============================================
    # Clock section
    # ============================================
    def _create_clock_section(self):
        clock_frame = ctk.CTkFrame(self)
        clock_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        for col in range(5):
            clock_frame.grid_columnconfigure(col, weight=0)
        clock_frame.grid_columnconfigure(4, weight=1)

        # Radio buttons: Internal / External (stacked vertically)
        self.clock_mode_var = tk.StringVar(value="internal")

        self.rb_internal = ctk.CTkRadioButton(
            clock_frame, text="Internal",
            variable=self.clock_mode_var, value="internal"
        )
        self.rb_internal.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.rb_external = ctk.CTkRadioButton(
            clock_frame, text="External",
            variable=self.clock_mode_var, value="external"
        )
        self.rb_external.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # ClkPin label + combobox
        clkpin_label = ctk.CTkLabel(clock_frame, text="ClkPin: ")
        clkpin_label.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="e")

        self.pin_var = tk.StringVar(value="4")
        self.pin_combobox = ctk.CTkComboBox(
            clock_frame,
            values=["1", "2", "3", "4"],
            variable=self.pin_var,
            width=40
        )
        self.pin_combobox.grid(row=0, column=2, padx=(0, 5), pady=5, sticky="w")

        # Mirror checkbox
        self.mirror_var = tk.BooleanVar(value=True)
        mirror_checkbox = ctk.CTkCheckBox(
            clock_frame, text="Mirror (on led pin 13)", variable=self.mirror_var
        )
        mirror_checkbox.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Frequency label + slider
        self.freq_var = tk.IntVar(value=2)

        self.freq_label = ctk.CTkLabel(
            clock_frame, text=f"Freq (Hz): {self.freq_var.get()}"
        )
        self.freq_label.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        self.freq_slider = ctk.CTkSlider(
            clock_frame, from_=1, to=10,
            number_of_steps=9,
            width=120,
            command=self._on_freq_slider
        )
        self.freq_slider.set(2)
        self.freq_slider.grid(row=1, column=4, padx=5, pady=5, sticky="we")

    def _on_freq_slider(self, value):
        self.freq_var.set(int(round(float(value))))
        self.freq_label.configure(text=f"Freq (Hz): {self.freq_var.get()}")

    # ============================================
    # Code section with file buttons on the left
    # ============================================
    def _create_code_section_with_file_buttons(self):
        container = ctk.CTkFrame(self)
        container.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        # File button column
        container.grid_columnconfigure(0, weight=0)
        # Code editor stretch
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # --- File buttons ---
        file_frame = ctk.CTkFrame(container)
        file_frame.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="n")

        btn_new = ctk.CTkButton(file_frame, text="New", width=80, command=self.on_new)
        btn_new.grid(row=0, column=0, padx=5, pady=5)

        btn_open = ctk.CTkButton(file_frame, text="Open", width=80, command=self.on_open)
        btn_open.grid(row=1, column=0, padx=5, pady=5)

        btn_save = ctk.CTkButton(file_frame, text="Save", width=80, command=self.on_save)
        btn_save.grid(row=2, column=0, padx=5, pady=5)

        # --- Code textbox ---
        self.code_text = ctk.CTkTextbox(container, width=600, height=300)
        self.code_text.grid(row=0, column=1, pady=5, sticky="nsew")

    # ============================================
    # Bottom buttons + error label
    # ============================================
    def _create_bottom_buttons(self):
        bottom = ctk.CTkFrame(self)
        bottom.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        bottom.grid_columnconfigure(0, weight=1)  # error label expands
        bottom.grid_columnconfigure(1, weight=0)
        bottom.grid_columnconfigure(2, weight=0)
        bottom.grid_rowconfigure(0, weight=1)

        # Error box (empty initially)
        self.error_box = ctk.CTkTextbox(bottom, width=350, height=60)
        self.error_box.grid(row=0, column=0, padx=5, sticky="nsew")

        # Check button
        self.check_button = ctk.CTkButton(bottom, text="Check", command=self.on_check)
        self.check_button.grid(row=0, column=1, padx=10)

        # Flash button
        self.flash_button = ctk.CTkButton(bottom, text="Flash", command=self.on_flash)
        self.flash_button.grid(row=0, column=2)
        self.flash_button.configure(state="disabled")

    # =========================
    # Error handling helpers
    # =========================
    def _clear_error(self):
        """Clear the error/output box."""
        if hasattr(self, "error_box"):
            self.error_box.delete("1.0", "end")

    def _set_error(self, message: str):
        """Write a message into the error/output box."""
        if hasattr(self, "error_box"):
            self.error_box.delete("1.0", "end")
            self.error_box.insert("end", message + "\n")

    def _append_error(self, message: str):
        """Append a line to the error/output box without clearing it."""
        if hasattr(self, "error_box"):
            self.error_box.insert("end", message + "\n")
            self.error_box.see("end")

    # =========================
    # Arduino CLI board detection on startup
    # =========================
    def _initial_board_scan(self):
        """
        Startup scan:
        - Run: arduino-cli board list --format json
        - Pick the best serial port, preferring 'USB' ports over plain 'Serial Port'
        - Populate entry_port
        - Always set entry_device to 'adafruit:avr:itsybitsy32u4_5V'
        - Report status in the error_box
        """
        # Set device string unconditionally
        if hasattr(self, "entry_device"):
            self.entry_device.delete(0, "end")
            self.entry_device.insert(0, "adafruit:avr:itsybitsy32u4_5V")

        if not hasattr(self, "error_box"):
            return

        try:
            result = subprocess.run(
                ["arduino-cli", "board", "list", "--format", "json"],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            self._set_error("arduino-cli not found. Install it or add it to PATH.")
            return

        if result.returncode != 0:
            msg = result.stderr.strip() or "arduino-cli returned an error."
            self._set_error(f"arduino-cli error: {msg}")
            return

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            self._set_error("Failed to parse JSON from arduino-cli output.")
            return

        detected_port = None

        # Newer JSON format: {"detected_ports": [ { "port": {...} }, ... ]}
        if isinstance(data, dict) and "detected_ports" in data:
            best_usb = None
            best_other = None
            for item in data.get("detected_ports", []):
                port_info = item.get("port", {})
                addr = port_info.get("address")
                label = port_info.get("label", "") or ""
                proto_label = port_info.get("protocol_label", "") or ""
                if not addr:
                    continue

                # prefer anything tagged as USB
                combined = (label + " " + proto_label).upper()
                if "USB" in combined:
                    if best_usb is None:
                        best_usb = addr
                else:
                    if best_other is None:
                        best_other = addr

            detected_port = best_usb or best_other

        # Older/alternative JSON format: top-level list
        elif isinstance(data, list):
            best_usb = None
            best_other = None
            for item in data:
                port_info = item.get("port") or item
                addr = port_info.get("address") or port_info.get("port")
                label = (port_info.get("label") or "") + " " + (port_info.get("protocol_label") or "")
                if not addr:
                    continue
                if "USB" in label.upper():
                    if best_usb is None:
                        best_usb = addr
                else:
                    if best_other is None:
                        best_other = addr
            detected_port = best_usb or best_other

        if detected_port:
            if hasattr(self, "entry_port"):
                self.entry_port.delete(0, "end")
                self.entry_port.insert(0, detected_port)
            self._set_error(f"Detected device on port {detected_port}.")
        else:
            self._set_error(
                "No serial ports reported by arduino-cli.\n"
                "If your board is connected, you may enter the port manually."
            )

    # =========================
    # Prepare sketch
    # =========================
    def _prepare_sketch_dir(self):
        """
        Determine the base sketch directory from entry_sketch_dir,
        ensure it exists, and return (base_dir, sketch_dir) where
        sketch_dir is a 'seq_sketch' subfolder.
        """
        # 1) Read base_dir from the UI
        base_dir = ""
        if hasattr(self, "entry_sketch_dir"):
            base_dir = self.entry_sketch_dir.get().strip()

        # Fallback to the user's home directory if empty / invalid
        if not base_dir:
            base_dir = os.path.expanduser("~")

        # Ensure base_dir exists
        try:
            os.makedirs(base_dir, exist_ok=True)
        except OSError as e:
            self._set_error(f"Cannot create base sketch directory '{base_dir}': {e}")
            return None, None

        # 2) Use a 'seq_sketch' subfolder inside base_dir
        sketch_dir = os.path.join(base_dir, "seq_sketch")
        try:
            os.makedirs(sketch_dir, exist_ok=True)
        except OSError as e:
            self._set_error(f"Cannot create sketch directory '{sketch_dir}': {e}")
            return None, None

        return base_dir, sketch_dir

    def _write_sketch_ino(self, sketch_dir: str, ino_source: str) -> str:
        """
        Write the .ino file into the given sketch_dir and return its full path.
        """
        ino_path = os.path.join(sketch_dir, "seq_sketch.ino")
        try:
            with open(ino_path, "w", encoding="utf-8") as f:
                f.write(ino_source)
        except OSError as e:
            self._set_error(f"Error writing .ino file:\n{e}")
            return ""
        return ino_path

    # =========================
    # Expression tokenizer
    # =========================
    def _tokenize_expr(self, text: str):
        """
        Turn an expression like:
            OR(f2, NOT(Q3))
        into a list of tokens: ('IDENT','OR'), ('LPAREN','('), ...
        Returns (tokens, error_message or None).
        """
        tokens = []
        i = 0
        n = len(text)

        while i < n:
            ch = text[i]

            if ch.isspace():
                i += 1
                continue

            if ch.isalpha():
                start = i
                while i < n and (text[i].isalnum() or text[i] == "_"):
                    i += 1
                ident = text[start:i]
                tokens.append(("IDENT", ident))
                continue

            if ch.isdigit():
                start = i
                while i < n and text[i].isdigit():
                    i += 1
                num = text[start:i]
                tokens.append(("NUMBER", num))
                continue

            if ch == "(":
                tokens.append(("LPAREN", ch))
                i += 1
                continue

            if ch == ")":
                tokens.append(("RPAREN", ch))
                i += 1
                continue

            if ch == ",":
                tokens.append(("COMMA", ch))
                i += 1
                continue

            # Unknown character
            return None, f"Invalid character '{ch}' in expression"

        return tokens, None

    # =========================
    # Recursive expression parser
    # =========================
    def _parse_expr_tokens(self, tokens, pos: int):
        """
        expr := IDENT [ '(' args ')' ]
        args := expr [ ',' expr ]
        Rules:
          - NOT must have exactly 1 argument
          - AND / OR / XOR must have exactly 2 arguments
        Returns (new_pos, error_message or None).
        """
        if pos >= len(tokens):
            return None, "Unexpected end of expression"

        tok_type, tok_val = tokens[pos]
        if tok_type != "IDENT":
            return None, f"Expected identifier, got '{tok_val}'"

        name = tok_val
        pos += 1

        # Function call?
        if pos < len(tokens) and tokens[pos][0] == "LPAREN":
            fn = name.upper()
            if fn not in ("NOT", "AND", "OR", "XOR"):
                return None, f"Unknown function '{name}'"

            pos += 1  # consume '('

            # First argument
            if pos < len(tokens) and tokens[pos][0] == "RPAREN":
                return None, f"{fn} requires arguments"

            args_count = 0

            # First arg
            new_pos, err = self._parse_expr_tokens(tokens, pos)
            if err:
                return None, err
            pos = new_pos
            args_count += 1

            # Optional second arg
            if pos < len(tokens) and tokens[pos][0] == "COMMA":
                pos += 1  # consume ','
                new_pos, err = self._parse_expr_tokens(tokens, pos)
                if err:
                    return None, err
                pos = new_pos
                args_count += 1

            # Expect ')'
            if pos >= len(tokens) or tokens[pos][0] != "RPAREN":
                return None, f"Missing ')' in call to {fn}"
            pos += 1  # consume ')'

            # Argument count rules
            if fn == "NOT":
                if args_count != 1:
                    return None, "NOT must have exactly 1 argument"
            else:  # AND/OR/XOR
                if args_count != 2:
                    return None, f"{fn} must have exactly 2 arguments"

            return pos, None

        # Simple variable like f2, y_3, Q3
        return pos, None

    def _check_expr_syntax(self, expr: str, line_no: int):
        """Syntax check for the right-hand side expression."""
        expr = expr.strip()
        if not expr:
            return f"Line {line_no}: missing expression on right-hand side"

        tokens, err = self._tokenize_expr(expr)
        if err:
            return f"Line {line_no}: {err}"

        pos, err = self._parse_expr_tokens(tokens, 0)
        if err:
            return f"Line {line_no}: {err}"

        if pos != len(tokens):
            extra = tokens[pos][1]
            return f"Line {line_no}: unexpected token '{extra}' after expression"

        return None  # no error

    # =========================
    # Expression → C translator
    # =========================
    def _parse_expr_to_c(self, tokens, pos: int):
        """
        Parse tokens into a C expression string.

        Grammar:
          expr := IDENT [ '(' args ')' ]
          args := expr [ ',' expr ]

        Rules:
          - NOT must have exactly 1 argument
          - AND / OR / XOR must have exactly 2 arguments

        Returns (c_expr, new_pos, error_message or None).
        """
        if pos >= len(tokens):
            return None, pos, "Unexpected end of expression"

        tok_type, tok_val = tokens[pos]
        if tok_type != "IDENT":
            return None, pos, f"Expected identifier, got '{tok_val}'"

        name = tok_val
        pos += 1

        # Function call?
        if pos < len(tokens) and tokens[pos][0] == "LPAREN":
            fn = name.upper()
            if fn not in ("NOT", "AND", "OR", "XOR"):
                return None, pos, f"Unknown function '{name}'"

            pos += 1  # consume '('

            # First argument
            arg1, pos, err = self._parse_expr_to_c(tokens, pos)
            if err:
                return None, pos, err
            args_count = 1
            arg2 = None

            # Optional second argument
            if pos < len(tokens) and tokens[pos][0] == "COMMA":
                pos += 1  # consume ','
                arg2, pos, err = self._parse_expr_to_c(tokens, pos)
                if err:
                    return None, pos, err
                args_count = 2

            # Expect closing ')'
            if pos >= len(tokens) or tokens[pos][0] != "RPAREN":
                return None, pos, f"Missing ')' in call to {fn}"
            pos += 1  # consume ')'

            # Argument count rules
            if fn == "NOT":
                if args_count != 1:
                    return None, pos, "NOT must have exactly 1 argument"
                c_expr = f"(!({arg1}))"
            else:  # AND / OR / XOR
                if args_count != 2:
                    return None, pos, f"{fn} must have exactly 2 arguments"
                if fn == "AND":
                    c_expr = f"(({arg1}) && ({arg2}))"
                elif fn == "OR":
                    c_expr = f"(({arg1}) || ({arg2}))"
                else:  # XOR
                    c_expr = f"(({arg1}) ^ ({arg2}))"

            return c_expr, pos, None

        # Simple variable like f2, y_3, Q3
        return name, pos, None

    def _expr_to_c(self, expr: str, line_no: int):
        """
        High-level helper: given a .seq expression string, return
        a C/Arduino expression string.

        Returns (c_expr, error_message_or_None).
        """
        expr = expr.strip()
        if not expr:
            return "0", f"Line {line_no}: missing expression"

        tokens, err = self._tokenize_expr(expr)
        if err:
            return "0", f"Line {line_no}: {err}"

        c_expr, pos, err = self._parse_expr_to_c(tokens, 0)
        if err:
            return "0", f"Line {line_no}: {err}"

        if pos != len(tokens):
            extra = tokens[pos][1]
            return "0", f"Line {line_no}: unexpected token '{extra}' after expression"

        return c_expr, None


    # =========================
    # Identifier extraction for semantic checks
    # =========================
    def _extract_idents_from_expr(self, expr: str):
        """
        Return all identifier-like names from an expression.
        We will later filter out NOT/AND/OR/XOR.
        """
        names = re.findall(r"[A-Za-z][A-Za-z0-9_]*", expr)
        return names

    # =========================
    # Full code checker (syntax + second-pass symbol checks)
    # =========================
    def check_code_syntax(self) -> bool:
        """
        1st pass: line-by-line syntax check.
        2nd pass: ensure every used symbol is either:
            - declared as a pin, or
            - defined on the left-hand side of some equation
              (combinational or sequential Qname.D).
        Stops at the first error and writes it to error_box.
        """
        self._clear_error()

        raw_text = self.code_text.get("1.0", "end")
        lines = raw_text.splitlines()

        # Treat completely empty / whitespace-only code as valid
        if all(not ln.strip() for ln in lines):
            return True

        pin_names = set()
        comb_lhs = set()
        seq_lhs = set()
        used_idents = {}  # ident -> first line where it appears in an expression

        keywords = {"NOT", "AND", "OR", "XOR"}

        # ---------- 1st pass: syntax + collect symbols ----------
        for i, line in enumerate(lines, start=1):
            text = line.strip()
            if not text:
                continue

            # a) PIN definitions: pin Y=8 or PIN Q = 3
            m = re.match(
                r"^(pin|PIN)\s+([A-Za-z][A-Za-z0-9_]*)\s*=\s*(\d+)\s*$",
                text
            )
            if m:
                name = m.group(2)
                pin_names.add(name)
                continue

            # b) Sequential: Qname.D = expr  (Q or q at start)
            m = re.match(
                r"^([qQ][A-Za-z0-9_]*)\.D\s*=\s*(.+)$",
                text
            )
            if m:
                qname = m.group(1)
                rhs = m.group(2)
                err = self._check_expr_syntax(rhs, i)
                if err:
                    self._set_error(err)
                    return False

                seq_lhs.add(qname)

                # Collect identifiers used on RHS
                for ident in self._extract_idents_from_expr(rhs):
                    if ident.upper() in keywords:
                        continue
                    if ident not in used_idents:
                        used_idents[ident] = i

                continue

            # c) Combinational: name = expr
            m = re.match(
                r"^([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.+)$",
                text
            )
            if m:
                lhs = m.group(1)
                rhs = m.group(2)
                err = self._check_expr_syntax(rhs, i)
                if err:
                    self._set_error(err)
                    return False

                comb_lhs.add(lhs)

                # Collect identifiers used on RHS
                for ident in self._extract_idents_from_expr(rhs):
                    if ident.upper() in keywords:
                        continue
                    if ident not in used_idents:
                        used_idents[ident] = i

                continue

            # If none of the patterns matched: invalid syntax
            self._set_error(f"Line {i}: invalid syntax")
            return False

        # ---------- 2nd pass: symbol resolution ----------
        defined = pin_names | comb_lhs | seq_lhs

        for ident, line_no in used_idents.items():
            if ident not in defined:
                self._set_error(
                    f"Line {line_no}: symbol '{ident}' is used but never "
                    f"declared as a pin or defined on the left-hand side"
                )
                return False

        # All good
        return True

    # ============================================
    # Generate .ino source (from .seq content)
    # ============================================

    def _generate_ino_source(self) -> str:
        """
        Build the .ino source using:
          - Clock section configuration
          - .seq code (pin declarations, combinational and sequential equations)
        """
        # ---------------------------------
        # 1. Read clock UI state
        # ---------------------------------
        mode = self.clock_mode_var.get() if hasattr(self, "clock_mode_var") else "internal"
        use_internal = 1 if mode == "internal" else 0

        try:
            clk_pin = int(self.pin_var.get())
        except Exception:
            clk_pin = 4  # fallback

        try:
            freq_hz = int(self.freq_var.get())
        except Exception:
            freq_hz = 2  # fallback

        mirror = 1 if (hasattr(self, "mirror_var") and self.mirror_var.get()) else 0

        # ---------------------------------
        # 2. Parse .seq code into structures
        # ---------------------------------
        raw_text = self.code_text.get("1.0", "end")
        lines = raw_text.splitlines()

        pin_defs = {}        # name -> pin number
        comb_eqs = []        # (lhs_name, rhs_expr, line_no)
        seq_eqs = []         # (qname, rhs_expr, line_no)
        comb_lhs = set()
        seq_lhs = set()

        for i, line in enumerate(lines, start=1):
            text = line.strip()
            if not text:
                continue

            # PIN definitions: pin Y=8 or PIN Q = 3
            m = re.match(
                r"^(pin|PIN)\s+([A-Za-z][A-Za-z0-9_]*)\s*=\s*(\d+)\s*$",
                text
            )
            if m:
                name = m.group(2)
                num = int(m.group(3))
                pin_defs[name] = num
                continue

            # Sequential: Qname.D = expr  (Q or q at start)
            m = re.match(
                r"^([qQ][A-Za-z0-9_]*)\.D\s*=\s*(.+)$",
                text
            )
            if m:
                qname = m.group(1)
                rhs = m.group(2)
                seq_eqs.append((qname, rhs, i))
                seq_lhs.add(qname)
                continue

            # Combinational: name = expr
            m = re.match(
                r"^([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.+)$",
                text
            )
            if m:
                lhs = m.group(1)
                rhs = m.group(2)
                comb_eqs.append((lhs, rhs, i))
                comb_lhs.add(lhs)
                continue

            # If the code reached here, the line is syntactically invalid,
            # but in practice Flash should only be enabled after a successful
            # Check, so we simply ignore it here.
            continue

        # Names of all logic signals
        signal_names = set(pin_defs.keys()) | comb_lhs | seq_lhs

        # Pin classification:
        #  - Inputs: declared as pin, never driven by any equation
        #  - Outputs: declared as pin and driven by some equation
        pin_inputs = {n for n in pin_defs if n not in comb_lhs and n not in seq_lhs}
        pin_outputs = set(pin_defs.keys()) - pin_inputs

        # Sequential register names (Q variables)
        q_names = sorted({q for (q, _, _) in seq_eqs})

        # ---------------------------------
        # 3. Emit .ino code
        # ---------------------------------
        lines_out = []
        o = lines_out.append

        # --- Configuration from clock section ---
        o("// --- Configuration ---")
        o(f"#define USE_INTERNAL_CLOCK   {use_internal}      // 1 = internal Timer1 clock, 0 = external")
        o(f"#define CLOCK_HZ             {freq_hz}      // frequency in Hz")
        o(f"#define PIN_CLK              {clk_pin}      // clock pin")
        o(f"#define CLOCK_LED_MIRROR     {mirror}      // mirror clock to LED (pin 13)")
        o("")
        o('#include "isrClock.h"')
        o("")

        # --- Pin mapping from .seq ---
        if pin_defs:
            o("// --- Pin mapping from .seq ---")
            for name in sorted(pin_defs.keys()):
                num = pin_defs[name]
                o(f"const uint8_t PIN_{name} = {num};")
            o("")

        # --- Signal declarations ---
        if signal_names or q_names:
            o("// --- Logic signals ---")
            for name in sorted(signal_names):
                o(f"uint8_t {name} = 0;")
            for q in q_names:
                o(f"uint8_t D_{q} = 0;")
            o("")

        # Clock edge detection state
        o("int __clk_prev = LOW;")
        o("")

        # --- setup() ---
        o("void setup() {")
        o("  // Initialize clock pin for edge detection")
        o("  pinMode(PIN_CLK, INPUT);")
        o("  __clk_prev = digitalRead(PIN_CLK);")
        o("")

        if pin_defs:
            o("  // Configure user pins from .seq")
            for name in sorted(pin_inputs):
                o(f"  pinMode(PIN_{name}, INPUT);")
            for name in sorted(pin_outputs):
                o(f"  pinMode(PIN_{name}, OUTPUT);")
            o("")

        o("  // Start the hardware Timer1 clock on PIN_CLK if internal mode is enabled")
        o("#if USE_INTERNAL_CLOCK")
        o("  T1Clock_begin(PIN_CLK, CLOCK_HZ);")
        o("#endif")
        o("}")
        o("")

        # --- loop() ---
        o("void loop() {")
        o("  int clk_now = digitalRead(PIN_CLK);")
        o("  bool rising = (__clk_prev == LOW && clk_now == HIGH);")
        o("  __clk_prev = clk_now;")
        o("")

        # Read pin inputs (if any)
        if pin_inputs:
            o("  // Read input pins")
            for name in sorted(pin_inputs):
                o(f"  {name} = (digitalRead(PIN_{name}) == HIGH) ? 1 : 0;")
            o("")

        # Combinational logic
        if comb_eqs:
            o("  // Combinational logic")
            for lhs, rhs, line_no in comb_eqs:
                c_expr, err = self._expr_to_c(rhs, line_no)
                if err:
                    # In theory this should not happen if Check passed,
                    # but fall back to 0 to keep generated code compilable.
                    c_expr = "0"
                o(f"  {lhs} = {c_expr};")
            o("")

        # Sequential next-state logic
        if seq_eqs:
            o("  // Compute D inputs for flip-flops")
            for qname, rhs, line_no in seq_eqs:
                c_expr, err = self._expr_to_c(rhs, line_no)
                if err:
                    c_expr = "0"
                o(f"  D_{qname} = {c_expr};")
            o("")
            o("  if (rising) {")
            for qname in q_names:
                o(f"    {qname} = D_{qname};")
            o("  }")
            o("")

        # Drive outputs
        if pin_outputs:
            o("  // Drive output pins")
            for name in sorted(pin_outputs):
                o(f"  digitalWrite(PIN_{name}, {name} ? HIGH : LOW);")
        o("}")
        o("")

        return "\n".join(lines_out)

    # ============================================
    # Button callbacks (logic to be added later)
    # ============================================
    def on_new(self):
        """Clear the code section. Empty code is considered valid once checked."""
        self.code_text.delete("1.0", "end")
        self._clear_error()
        # Require a fresh Check before allowing Flash
        if hasattr(self, "flash_button"):
            self.flash_button.configure(state="disabled")

    def on_open(self):
        """Open a .seq file and load it into the code section."""
        # Determine initial directory for the dialog
        initial_dir = ""
        if hasattr(self, "entry_sketch_dir"):
            initial_dir = self.entry_sketch_dir.get().strip()
        if not initial_dir or not os.path.isdir(initial_dir):
            initial_dir = os.path.expanduser("~")

        path = filedialog.askopenfilename(
            title="Open .seq file",
            filetypes=[("Sequence files", "*.seq"), ("All files", "*.*")],
            initialdir=initial_dir,
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            self._set_error(f"Error opening file: {e}")
            if hasattr(self, "flash_button"):
                self.flash_button.configure(state="disabled")
            return

        self.code_text.delete("1.0", "end")
        self.code_text.insert("1.0", content)
        self._clear_error()
        if hasattr(self, "flash_button"):
            self.flash_button.configure(state="disabled")

    def on_save(self):
        """Save the code section to a .seq file (ask user for filename)."""
        # Determine initial directory for the dialog
        initial_dir = ""
        if hasattr(self, "entry_sketch_dir"):
            initial_dir = self.entry_sketch_dir.get().strip()
        if not initial_dir or not os.path.isdir(initial_dir):
            initial_dir = os.path.expanduser("~")

        path = filedialog.asksaveasfilename(
            title="Save .seq file",
            defaultextension=".seq",
            filetypes=[("Sequence files", "*.seq"), ("All files", "*.*")],
            initialdir=initial_dir,
        )
        if not path:
            return

        content = self.code_text.get("1.0", "end").rstrip("\n")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            self._set_error(f"Error saving file: {e}")
            return

        self._set_error("Saved successfully.")

    def on_check(self):
        """Check syntax; if ok, enable Flash, else show error and disable Flash."""
        ok = self.check_code_syntax()
        if hasattr(self, "flash_button"):
            if ok:
                self.flash_button.configure(state="normal")
                # Optional: show a success message or leave box empty
                self._set_error("No syntax errors.")
            else:
                self.flash_button.configure(state="disabled")

    def on_flash(self):
        """
        Full Flash sequence:
          1) Prepare sketch directory from entry_sketch_dir (base_dir/seq_sketch)
          2) Ensure isrClock.h is present in the sketch_dir (copy from base_dir if needed)
          3) Generate seq_sketch.ino from the GUI config + .seq code
          4) Write it into the sketch directory
          5) Compile with arduino-cli
          6) Upload with arduino-cli
        """
        self._clear_error()

        # 1) Prepare sketch directory
        base_dir, sketch_dir = self._prepare_sketch_dir()
        if not base_dir or not sketch_dir:
            return

        self._append_error(f"Base directory:  {base_dir}")
        self._append_error(f"Sketch directory: {sketch_dir}")

        # 2) Ensure isrClock.h ends up in sketch_dir
        sketch_hdr = os.path.join(sketch_dir, "isrClock.h")
        base_hdr = os.path.join(base_dir, "isrClock.h")

        lib_found = None
        if os.path.isfile(sketch_hdr):
            lib_found = sketch_hdr
        elif os.path.isfile(base_hdr):
            # Copy from base_dir to sketch_dir
            try:
                shutil.copy2(base_hdr, sketch_hdr)
                lib_found = sketch_hdr
            except OSError as e:
                self._set_error(
                    "Found 'isrClock.h' in base directory but failed to copy it into the sketch directory:\n"
                    f"  from: {base_hdr}\n"
                    f"  to:   {sketch_hdr}\n"
                    f"Error: {e}"
                )
                return

        if lib_found is None:
            self._set_error(
                "Required library 'isrClock.h' was not found.\n"
                "Please copy 'isrClock.h' into the folder specified as SketchDir\n"
                "and try Flash again."
            )
            return

        self._append_error(f"Library used at: {lib_found}")

        # 3) Generate the .ino source based on the current clock + .seq logic
        ino_src = self._generate_ino_source()

        # 4) Write seq_sketch.ino into the sketch_dir
        ino_path = self._write_sketch_ino(sketch_dir, ino_src)
        if not ino_path:
            return

        self._append_error(f"Generated .ino file: {ino_path}")

        # 5) Compile with arduino-cli
        device = ""
        if hasattr(self, "entry_device"):
            device = self.entry_device.get().strip()

        if not device:
            self._set_error("Device (FQBN) is empty. Please fill 'Device' and try again.")
            return

        self._append_error(f"Compiling for device: {device}")

        compile_cmd = ["arduino-cli", "compile", "--fqbn", device, sketch_dir]

        try:
            compile_result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            self._set_error("arduino-cli not found. Install it or add it to PATH.")
            return

        if compile_result.returncode != 0:
            self._append_error("Compile failed.")
            if compile_result.stdout.strip():
                self._append_error("=== compile stdout ===")
                self._append_error(compile_result.stdout.strip())
            if compile_result.stderr.strip():
                self._append_error("=== compile stderr ===")
                self._append_error(compile_result.stderr.strip())
            return
        else:
            self._append_error("Compile succeeded.")
            if compile_result.stdout.strip():
                self._append_error("=== compile stdout ===")
                self._append_error(compile_result.stdout.strip())

        # 6) Upload with arduino-cli
        port = ""
        if hasattr(self, "entry_port"):
            port = self.entry_port.get().strip()

        if not port:
            self._set_error("Port is empty. Please fill 'Port' and try again.")
            return

        self._append_error(f"Uploading to port: {port}")

        upload_cmd = ["arduino-cli", "upload", "-p", port, "--fqbn", device, sketch_dir]

        upload_result = subprocess.run(
            upload_cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if upload_result.returncode != 0:
            self._append_error("Upload failed.")
            if upload_result.stdout.strip():
                self._append_error("=== upload stdout ===")
                self._append_error(upload_result.stdout.strip())
            if upload_result.stderr.strip():
                self._append_error("=== upload stderr ===")
                self._append_error(upload_result.stderr.strip())
            return
        else:
            self._append_error("Upload succeeded.")
            if upload_result.stdout.strip():
                self._append_error("=== upload stdout ===")
                self._append_error(upload_result.stdout.strip())

if __name__ == "__main__":
    app = SeqEditorApp()
    app.mainloop()


