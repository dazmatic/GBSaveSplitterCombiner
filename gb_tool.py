import os
import shutil
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --- Game ROM Combiner Constants ---
ROM_SIZE_32KB = 32 * 1024
ROM_SIZE_1MB = 1 * 1024 * 1024
ROM_SIZE_2MB = 2 * 1024 * 1024
ROM_SIZE_4MB = 4 * 1024 * 1024
ROM_SIZE_6MB = 6 * 1024 * 1024
TOTAL_ROM_SIZE_8MB = 8 * 1024 * 1024
TOTAL_ROM_SIZE_32MB = 32 * 1024 * 1024

GAME_SLOTS_4 = [
    {"start": ROM_SIZE_1MB, "max_size": ROM_SIZE_1MB, "name": "Game Slot 1 (1MB)"},
    {"start": ROM_SIZE_2MB, "max_size": ROM_SIZE_2MB, "name": "Game Slot 2 (2MB)"},
    {"start": ROM_SIZE_4MB, "max_size": ROM_SIZE_2MB, "name": "Game Slot 3 (2MB)"},
    {"start": ROM_SIZE_6MB, "max_size": ROM_SIZE_2MB, "name": "Game Slot 4 (2MB)"},
]

GAME_SLOTS_3 = [
    {"start": ROM_SIZE_2MB, "max_size": ROM_SIZE_2MB, "name": "Game Slot 1 (2MB)"},
    {"start": ROM_SIZE_4MB, "max_size": ROM_SIZE_2MB, "name": "Game Slot 2 (2MB)"},
    {"start": ROM_SIZE_6MB, "max_size": ROM_SIZE_2MB, "name": "Game Slot 3 (2MB)"},
]

GAME_SLOTS_16 = [
    {"start": ROM_SIZE_1MB, "max_size": ROM_SIZE_1MB, "name": "Game Slot 1 (1MB)"}
] + [
    {
        "start": (i - 1) * ROM_SIZE_2MB,
        "max_size": ROM_SIZE_2MB,
        "name": f"Game Slot {i} (2MB)",
    }
    for i in range(2, 17)
]

MENU_FILES = {
    ("Gameboy", 3): "Daz 3in1.gb",
    ("Gameboy", 4): "Daz 4in1.gb",
    ("Gameboy", 16): "Daz 16in1.gb",
    ("Gameboy Colour", 3): "Daz 3in1.gbc",
    ("Gameboy Colour", 4): "Daz 4in1.gbc",
    ("Gameboy Colour", 16): "Daz 16in1.gbc",
}

CHUNK_SIZE_KB = 32
CHUNK_SIZE_BYTES = CHUNK_SIZE_KB * 1024


def parse_gb_header_lenient(data, offset=0):
    base = offset
    if len(data) < base + 0x150:
        return None, 0, False

    title_raw = data[base + 0x0134 : base + 0x0143]
    ascii_chars = [chr(b) for b in title_raw if 32 <= b <= 126]
    title = "".join(ascii_chars).strip()
    title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()

    if not title or len(ascii_chars) < 2:
        return None, 0, False

    size_code = data[base + 0x0148]
    if size_code <= 0x08:
        actual_size = ROM_SIZE_32KB << size_code
    else:
        actual_size = ROM_SIZE_2MB

    return title, actual_size, True


class MultiFunctionTool(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Game Boy Multi-Function Tool (32MB / 16-ROM Supported)")
        self.geometry("640x840")

        self.temp_dir = tempfile.mkdtemp(prefix="gb_combiner_")

        self.rom_combiner_menu_file_path = None
        self.rom_combiner_game_file_paths = []
        self.rom_combiner_rom_mode = tk.StringVar(value="16")
        self.rom_combiner_device_mode = tk.StringVar(value="Gameboy Colour")
        self.rom_combiner_menu_mode = tk.StringVar(value="Automatic")

        self.savesplit_file_paths = []
        self.savesplit_mode = tk.StringVar(value="16")

        self.setup_ui()

    def destroy(self):
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        super().destroy()

    def setup_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        rom_combiner_frame = tk.Frame(self.notebook)
        save_splitter_frame = tk.Frame(self.notebook)

        self.notebook.add(rom_combiner_frame, text="ROM Combiner")
        self.notebook.add(save_splitter_frame, text="Save Splitter/Combiner")

        self.setup_rom_combiner_ui(rom_combiner_frame)
        self.setup_save_splitter_ui(save_splitter_frame)

    # -------------------------------------------------------------------------
    #                         ROM COMBINER GUI
    # -------------------------------------------------------------------------

    def setup_rom_combiner_ui(self, parent_frame):
        frame = tk.Frame(parent_frame, padx=15, pady=10)
        frame.pack(fill="both", expand=True)

        # 1. ROM Mode
        tk.Label(
            frame, text="1. Select ROM Mode", font=("Helvetica", 11, "bold")
        ).pack(anchor="w", pady=(0, 2))
        rom_mode_frame = tk.Frame(frame)
        rom_mode_frame.pack(anchor="w")
        tk.Radiobutton(
            rom_mode_frame,
            text="3-Game (8MB)",
            variable=self.rom_combiner_rom_mode,
            value="3",
            command=self.rom_combiner_update_ui,
        ).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(
            rom_mode_frame,
            text="4-Game (8MB)",
            variable=self.rom_combiner_rom_mode,
            value="4",
            command=self.rom_combiner_update_ui,
        ).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(
            rom_mode_frame,
            text="16-Game (32MB)",
            variable=self.rom_combiner_rom_mode,
            value="16",
            command=self.rom_combiner_update_ui,
        ).pack(side=tk.LEFT, padx=5)

        # 2. Device Type
        tk.Label(frame, text="-" * 70).pack(pady=5)
        tk.Label(
            frame, text="2. Select Device Type", font=("Helvetica", 11, "bold")
        ).pack(anchor="w", pady=(0, 2))
        device_mode_frame = tk.Frame(frame)
        device_mode_frame.pack(anchor="w")
        tk.Radiobutton(
            device_mode_frame,
            text="Gameboy",
            variable=self.rom_combiner_device_mode,
            value="Gameboy",
            command=self.rom_combiner_update_ui,
        ).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(
            device_mode_frame,
            text="Gameboy Colour",
            variable=self.rom_combiner_device_mode,
            value="Gameboy Colour",
            command=self.rom_combiner_update_ui,
        ).pack(side=tk.LEFT, padx=5)

        # 3. Menu Selection
        tk.Label(frame, text="-" * 70).pack(pady=5)
        tk.Label(
            frame, text="3. Select Menu File", font=("Helvetica", 11, "bold")
        ).pack(anchor="w", pady=(0, 2))
        menu_mode_frame = tk.Frame(frame)
        menu_mode_frame.pack(anchor="w")
        tk.Radiobutton(
            menu_mode_frame,
            text="Automatic",
            variable=self.rom_combiner_menu_mode,
            value="Automatic",
            command=self.rom_combiner_update_ui,
        ).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(
            menu_mode_frame,
            text="Custom",
            variable=self.rom_combiner_menu_mode,
            value="Custom",
            command=self.rom_combiner_update_ui,
        ).pack(side=tk.LEFT, padx=5)

        self.rom_combiner_menu_path_label = tk.Label(
            frame,
            text="No menu file selected.",
            bg="white",
            width=55,
            anchor="w",
            relief="sunken",
        )
        self.rom_combiner_menu_path_label.pack(pady=3)
        self.rom_combiner_select_menu_button = tk.Button(
            frame,
            text="Select Custom Menu File",
            command=self.select_custom_menu_file,
            width=30,
            state="disabled",
        )
        self.rom_combiner_select_menu_button.pack(pady=2)

        # 4. Manage Game ROMs
        tk.Label(frame, text="-" * 70).pack(pady=5)
        tk.Label(
            frame, text="4. Manage Game ROMs", font=("Helvetica", 11, "bold")
        ).pack(anchor="w", pady=(0, 2))

        button_frame = tk.Frame(frame)
        button_frame.pack(anchor="w", pady=2)

        import_rom_button = tk.Button(
            button_frame,
            text="Import Merged ROM",
            command=self.import_merged_rom,
            bg="#d1e7dd",
        )
        import_rom_button.pack(side=tk.LEFT, padx=(0, 10))

        add_game_button = tk.Button(
            button_frame, text="Add Game", command=self.add_game_file
        )
        add_game_button.pack(side=tk.LEFT, padx=5)
        remove_game_button = tk.Button(
            button_frame,
            text="Remove Selected",
            command=self.remove_game_file,
        )
        remove_game_button.pack(side=tk.LEFT, padx=5)

        listbox_frame = tk.Frame(frame)
        listbox_frame.pack(fill="x", pady=5)

        self.rom_combiner_listbox = tk.Listbox(
            listbox_frame, selectmode=tk.SINGLE, width=65, height=7
        )
        scrollbar = tk.Scrollbar(
            listbox_frame,
            orient="vertical",
            command=self.rom_combiner_listbox.yview,
        )
        self.rom_combiner_listbox.config(yscrollcommand=scrollbar.set)

        self.rom_combiner_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.pack(side=tk.RIGHT, fill="y")

        # Context Menu setup for Right Click
        self.context_menu = tk.Menu(self.rom_combiner_listbox, tearoff=0)
        self.context_menu.add_command(label="Replace Game", command=self.replace_game_file)
        self.context_menu.add_command(label="Delete Game", command=self.remove_game_file)

        self.rom_combiner_listbox.bind("<Button-3>", self.show_context_menu)
        self.rom_combiner_listbox.bind("<Button-2>", self.show_context_menu)

        order_frame = tk.Frame(frame)
        order_frame.pack(pady=2)
        move_up_button = tk.Button(
            order_frame, text="Move Up", command=self.move_up
        )
        move_up_button.pack(side=tk.LEFT, padx=5)
        move_down_button = tk.Button(
            order_frame, text="Move Down", command=self.move_down
        )
        move_down_button.pack(side=tk.LEFT, padx=5)

        tk.Label(frame, text="-" * 70).pack(pady=5)

        # --- Stacked Bar Visual Map Frame ---
        status_frame = tk.LabelFrame(
            frame, text="Flash Allocation Visual Map", font=("Helvetica", 10, "bold"), padx=10, pady=5
        )
        status_frame.pack(fill="x", pady=5)

        # Canvas for the stacked segment bar
        self.map_canvas = tk.Canvas(status_frame, height=36, bg="#2b2b2b", highlightthickness=1, highlightbackground="#1e1e1e")
        self.map_canvas.pack(fill="x", pady=5)
        self.map_canvas.bind("<Configure>", lambda e: self.rom_combiner_update_allocation_bar())

        # Legend / Text breakdown
        info_subframe = tk.Frame(status_frame)
        info_subframe.pack(fill="x")

        self.slot_status_label = tk.Label(info_subframe, text="0/16 Slots Used", font=("Helvetica", 9, "bold"))
        self.slot_status_label.pack(side=tk.LEFT)

        self.memory_status_label = tk.Label(info_subframe, text="0.00 MB / 32.00 MB Allocated", font=("Helvetica", 9))
        self.memory_status_label.pack(side=tk.RIGHT)

        create_rom_button = tk.Button(
            frame,
            text="Create Multi-Game ROM",
            command=self.create_rom,
            width=35,
            height=2,
            bg="#e1e1e1",
        )
        create_rom_button.pack(pady=8)

        self.rom_combiner_update_ui()

    def get_active_slots(self):
        mode = self.rom_combiner_rom_mode.get()
        if mode == "16":
            return GAME_SLOTS_16
        elif mode == "4":
            return GAME_SLOTS_4
        return GAME_SLOTS_3

    def show_context_menu(self, event):
        try:
            index = self.rom_combiner_listbox.nearest(event.y)
            self.rom_combiner_listbox.selection_clear(0, tk.END)
            self.rom_combiner_listbox.selection_set(index)
            self.rom_combiner_listbox.activate(index)
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def replace_game_file(self):
        try:
            selected_index = self.rom_combiner_listbox.curselection()[0]
        except IndexError:
            return

        current_slots = self.get_active_slots()
        slot = current_slots[selected_index]

        filepath = filedialog.askopenfilename(
            title=f"Replace Game in Slot {selected_index+1}",
            filetypes=[("ROM Files", "*.gb *.gbc *.gba"), ("All Files", "*.*")],
        )
        if filepath:
            file_size = os.path.getsize(filepath)
            if file_size > slot["max_size"]:
                messagebox.showerror(
                    "Error",
                    f"Selected file exceeds slot limit of {slot['max_size']/1024/1024:.0f}MB.",
                )
                return

            self.rom_combiner_game_file_paths[selected_index] = filepath
            self.rom_combiner_update_listbox()

    def rom_combiner_update_ui(self):
        self.rom_combiner_update_listbox()
        if self.rom_combiner_menu_mode.get() == "Custom":
            self.rom_combiner_select_menu_button.config(state="normal")
            self.rom_combiner_menu_path_label.config(
                text=(
                    os.path.basename(self.rom_combiner_menu_file_path)
                    if self.rom_combiner_menu_file_path
                    else "No custom menu file selected."
                )
            )
        else:
            self.rom_combiner_select_menu_button.config(state="disabled")
            rom_count = int(self.rom_combiner_rom_mode.get())
            device = self.rom_combiner_device_mode.get()
            menu_filename = MENU_FILES.get(
                (device, rom_count), f"Daz {rom_count}in1.gbc"
            )
            self.rom_combiner_menu_path_label.config(
                text=f"Automatic: {menu_filename}"
            )

    def import_merged_rom(self):
        filepath = filedialog.askopenfilename(
            title="Select Merged Multi-Game ROM File",
            filetypes=[("ROM Files", "*.gb *.gbc *.bin"), ("All Files", "*.*")],
        )
        if not filepath:
            return

        file_size = os.path.getsize(filepath)

        if file_size == TOTAL_ROM_SIZE_32MB:
            self.rom_combiner_rom_mode.set("16")
        elif file_size == TOTAL_ROM_SIZE_8MB:
            if self.rom_combiner_rom_mode.get() not in ("3", "4"):
                self.rom_combiner_rom_mode.set("4")

        current_slots = self.get_active_slots()
        debug_log = []

        try:
            with open(filepath, "rb") as f:
                merged_data = f.read()

            self.rom_combiner_game_file_paths.clear()

            # Extract Menu Slot (0x0)
            menu_title, menu_size, menu_valid = parse_gb_header_lenient(merged_data, offset=0)
            if menu_valid or menu_title:
                menu_temp_path = os.path.join(
                    self.temp_dir, f"Extracted_Menu_{menu_title or 'Menu'}.gbc"
                )
                with open(menu_temp_path, "wb") as f_out:
                    f_out.write(merged_data[:ROM_SIZE_1MB])
                self.rom_combiner_menu_file_path = menu_temp_path
                self.rom_combiner_menu_mode.set("Custom")
                debug_log.append(f"Menu Found at 0x00000000 | Title: '{menu_title}'")

            extracted_count = 0
            for i, slot in enumerate(current_slots):
                start_offset = slot["start"]
                if start_offset >= len(merged_data):
                    break

                title, actual_size, valid = parse_gb_header_lenient(merged_data, offset=start_offset)

                if valid:
                    game_bytes = merged_data[start_offset : start_offset + min(actual_size, slot["max_size"])]
                    temp_path = os.path.join(self.temp_dir, f"Slot_{i+1:02d}_{title}.gbc")
                    with open(temp_path, "wb") as f_out:
                        f_out.write(game_bytes)

                    self.rom_combiner_game_file_paths.append(temp_path)
                    extracted_count += 1
                    debug_log.append(f"Slot {i+1:02d} [0x{start_offset:08X}]: VALID -> '{title}' ({actual_size/1024:.0f}KB)")

            # Bank scan fallback if standard offsets returned 0
            if extracted_count == 0:
                scan_offset = 0x100000
                found_scan_idx = 1
                while scan_offset < len(merged_data) and found_scan_idx <= len(current_slots):
                    title, actual_size, valid = parse_gb_header_lenient(merged_data, offset=scan_offset)
                    if valid:
                        game_bytes = merged_data[scan_offset : scan_offset + actual_size]
                        temp_path = os.path.join(self.temp_dir, f"Scan_Slot_{found_scan_idx:02d}_{title}.gbc")
                        with open(temp_path, "wb") as f_out:
                            f_out.write(game_bytes)
                        self.rom_combiner_game_file_paths.append(temp_path)
                        extracted_count += 1
                        debug_log.append(f"Scan Found [0x{scan_offset:08X}]: '{title}' ({actual_size/1024:.0f}KB)")
                        scan_offset += max(actual_size, 0x10000)
                        found_scan_idx += 1
                    else:
                        scan_offset += 0x10000

            self.rom_combiner_update_ui()

            log_summary = "\n".join(debug_log)
            messagebox.showinfo(
                "Import Complete",
                f"Parsed ROM Layout! Extracted {extracted_count} game slot(s).\n\n--- Scan Log ---\n{log_summary}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to import merged ROM: {e}")

    def select_custom_menu_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Custom Menu ROM File (max 1MB)",
            filetypes=[("ROM Files", "*.gb *.gbc *.gba"), ("All Files", "*.*")],
        )
        if not filepath:
            return

        file_size = os.path.getsize(filepath)
        if file_size > ROM_SIZE_1MB:
            messagebox.showerror(
                "Error",
                f"Menu file is {file_size/1024/1024:.2f}MB (max allowed is 1MB).",
            )
            return

        self.rom_combiner_menu_file_path = filepath
        self.rom_combiner_menu_path_label.config(text=os.path.basename(filepath))
        self.rom_combiner_update_allocation_bar()

    def add_game_file(self):
        current_slots = self.get_active_slots()
        max_games = len(current_slots)
        if len(self.rom_combiner_game_file_paths) >= max_games:
            messagebox.showwarning(
                "Warning",
                f"Maximum limit of {max_games} game files reached for this mode.",
            )
            return

        filepaths = filedialog.askopenfilenames(
            title="Select Game File(s)",
            filetypes=[("ROM Files", "*.gb *.gbc *.gba"), ("All Files", "*.*")],
        )
        if filepaths:
            for path in filepaths:
                if len(self.rom_combiner_game_file_paths) < max_games:
                    self.rom_combiner_game_file_paths.append(path)
            self.rom_combiner_update_listbox()

    def remove_game_file(self):
        try:
            selected_index = self.rom_combiner_listbox.curselection()[0]
            del self.rom_combiner_game_file_paths[selected_index]
            self.rom_combiner_update_listbox()
        except IndexError:
            messagebox.showwarning("Warning", "Please select a game to remove.")

    def move_up(self):
        try:
            selected_index = self.rom_combiner_listbox.curselection()[0]
            if selected_index > 0:
                (
                    self.rom_combiner_game_file_paths[selected_index],
                    self.rom_combiner_game_file_paths[selected_index - 1],
                ) = (
                    self.rom_combiner_game_file_paths[selected_index - 1],
                    self.rom_combiner_game_file_paths[selected_index],
                )
                self.rom_combiner_update_listbox()
                self.rom_combiner_listbox.select_set(selected_index - 1)
        except IndexError:
            pass

    def move_down(self):
        try:
            selected_index = self.rom_combiner_listbox.curselection()[0]
            if selected_index < len(self.rom_combiner_game_file_paths) - 1:
                (
                    self.rom_combiner_game_file_paths[selected_index],
                    self.rom_combiner_game_file_paths[selected_index + 1],
                ) = (
                    self.rom_combiner_game_file_paths[selected_index + 1],
                    self.rom_combiner_game_file_paths[selected_index],
                )
                self.rom_combiner_update_listbox()
                self.rom_combiner_listbox.select_set(selected_index + 1)
        except IndexError:
            pass

    def rom_combiner_update_listbox(self):
        self.rom_combiner_listbox.delete(0, tk.END)
        current_slots = self.get_active_slots()

        for i, path in enumerate(self.rom_combiner_game_file_paths):
            if i >= len(current_slots):
                continue
            slot = current_slots[i]
            try:
                file_size_bytes = os.path.getsize(path)
                file_size_mb = file_size_bytes / (1024 * 1024)
                display_text = f"Slot {i+1:02d} (Max {slot['max_size']/1024/1024:.0f}MB): {os.path.basename(path)} ({file_size_mb:.2f}MB)"
                self.rom_combiner_listbox.insert(tk.END, display_text)
                if file_size_bytes > slot["max_size"]:
                    self.rom_combiner_listbox.itemconfig(tk.END, {"fg": "red"})
            except OSError:
                self.rom_combiner_listbox.insert(
                    tk.END, f"Slot {i+1:02d}: ERROR - File missing"
                )
                self.rom_combiner_listbox.itemconfig(tk.END, {"fg": "red"})

        self.rom_combiner_update_allocation_bar()

    def rom_combiner_update_allocation_bar(self):
        canvas = self.map_canvas
        canvas.delete("all")

        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        if canvas_width <= 1:
            canvas_width = 580  # Default fallback width before render
        if canvas_height <= 1:
            canvas_height = 36

        rom_mode = self.rom_combiner_rom_mode.get()
        total_bytes = TOTAL_ROM_SIZE_32MB if rom_mode == "16" else TOTAL_ROM_SIZE_8MB
        current_slots = self.get_active_slots()

        # Menu occupies initial space (0x0 to 1MB or 2MB depending on mode)
        menu_slot_size = ROM_SIZE_2MB if rom_mode == "3" else ROM_SIZE_1MB

        # Define standard color palette
        COLOR_MENU = "#1e88e5"       # Crisp Blue
        COLOR_GAME = "#2ecc71"       # Vibrant Green
        COLOR_OVERSIZE = "#e74c3c"   # Red Error
        COLOR_EMPTY_SLOT = "#3a3a3a" # Dark Grey
        COLOR_BORDER = "#1e1e1e"

        total_allocated_bytes = 0

        # Helper to convert byte offsets to canvas pixel coordinates
        def byte_to_x(b_val):
            return int((b_val / total_bytes) * canvas_width)

        # --- 1. DRAW MENU SEGMENT ---
        menu_actual_size = menu_slot_size
        if self.rom_combiner_menu_mode.get() == "Custom" and self.rom_combiner_menu_file_path:
            try:
                menu_actual_size = os.path.getsize(self.rom_combiner_menu_file_path)
            except OSError:
                pass

        total_allocated_bytes += menu_actual_size
        x0 = 0
        x1 = byte_to_x(menu_slot_size)
        x_filled = byte_to_x(menu_actual_size)

        # Slot Background
        canvas.create_rectangle(x0, 0, x1, canvas_height, fill=COLOR_EMPTY_SLOT, outline=COLOR_BORDER)
        # Filled Portion
        canvas.create_rectangle(x0, 0, x_filled, canvas_height, fill=COLOR_MENU, outline=COLOR_BORDER)
        # Text Label
        if (x1 - x0) > 25:
            canvas.create_text((x0 + x1) / 2, canvas_height / 2, text="Menu", fill="white", font=("Helvetica", 8, "bold"))

        # --- 2. DRAW GAME SLOT SEGMENTS ---
        for i, slot in enumerate(current_slots):
            slot_start = slot["start"]
            slot_max = slot["max_size"]
            slot_end = slot_start + slot_max

            x_start = byte_to_x(slot_start)
            x_end = byte_to_x(slot_end)

            # Draw empty slot boundary container
            canvas.create_rectangle(x_start, 0, x_end, canvas_height, fill=COLOR_EMPTY_SLOT, outline=COLOR_BORDER)

            # Draw filled game ROM block if present
            if i < len(self.rom_combiner_game_file_paths):
                game_path = self.rom_combiner_game_file_paths[i]
                try:
                    game_size = os.path.getsize(game_path)
                    total_allocated_bytes += game_size

                    x_game_end = byte_to_x(slot_start + game_size)
                    fill_color = COLOR_OVERSIZE if game_size > slot_max else COLOR_GAME

                    canvas.create_rectangle(x_start, 0, min(x_game_end, x_end), canvas_height, fill=fill_color, outline=COLOR_BORDER)
                except OSError:
                    pass

            # Dashed dividing line between slots
            canvas.create_line(x_end, 0, x_end, canvas_height, fill="#666666", dash=(2, 2))

            # Draw slot label inside segment (e.g., S1, S2, S3...)
            slot_width = x_end - x_start
            if slot_width > 18:
                canvas.create_text((x_start + x_end) / 2, canvas_height / 2, text=f"S{i+1}", fill="white", font=("Helvetica", 8, "bold"))

        # --- 3. UPDATE TEXT LABELS ---
        used_slots = len(self.rom_combiner_game_file_paths)
        max_slots = len(current_slots)

        allocated_mb = total_allocated_bytes / (1024 * 1024)
        total_mb = total_bytes / (1024 * 1024)
        perc = min(100.0, (total_allocated_bytes / total_bytes) * 100)

        self.slot_status_label.config(text=f"{used_slots}/{max_slots} Slots Used")
        self.memory_status_label.config(text=f"{allocated_mb:.2f} MB / {total_mb:.2f} MB Allocated ({perc:.1f}%)")

    def create_rom(self):
        rom_mode = self.rom_combiner_rom_mode.get()
        rom_count = int(rom_mode)
        current_slots = self.get_active_slots()
        total_rom_bytes = (
            TOTAL_ROM_SIZE_32MB if rom_mode == "16" else TOTAL_ROM_SIZE_8MB
        )

        if self.rom_combiner_menu_mode.get() == "Automatic":
            device = self.rom_combiner_device_mode.get()
            menu_filename = MENU_FILES.get((device, rom_count))
            script_dir = os.path.dirname(os.path.abspath(__file__))
            menu_filepath = os.path.join(script_dir, "menus", menu_filename)

            if not os.path.exists(menu_filepath):
                messagebox.showerror(
                    "Error",
                    f"Could not find menu file: 'menus/{menu_filename}'.\n"
                    "Place it in the 'menus' folder or use Custom Menu mode.",
                )
                return
        else:
            if not self.rom_combiner_menu_file_path:
                messagebox.showerror(
                    "Error", "Please select a custom menu file."
                )
                return
            menu_filepath = self.rom_combiner_menu_file_path

        for i, game_filepath in enumerate(self.rom_combiner_game_file_paths):
            slot = current_slots[i]
            try:
                file_size = os.path.getsize(game_filepath)
                if file_size > slot["max_size"]:
                    messagebox.showerror(
                        "Error",
                        f"'{os.path.basename(game_filepath)}' exceeds slot limit of {slot['max_size']/1024/1024:.0f}MB.",
                    )
                    return
            except OSError:
                messagebox.showerror(
                    "Error", f"Cannot access '{os.path.basename(game_filepath)}'."
                )
                return

        output_filepath = filedialog.asksaveasfilename(
            defaultextension=".gbc",
            title="Save Combined Multi-Game ROM",
            filetypes=[("ROM Files", "*.gbc *.gb"), ("All Files", "*.*")],
        )
        if not output_filepath:
            return

        try:
            final_rom_data = bytearray(b"\xFF" * total_rom_bytes)

            with open(menu_filepath, "rb") as menu_in:
                menu_data = menu_in.read()
                final_rom_data[: len(menu_data)] = menu_data

            for i, game_filepath in enumerate(
                self.rom_combiner_game_file_paths
            ):
                slot = current_slots[i]
                with open(game_filepath, "rb") as game_in:
                    game_data = game_in.read()
                    final_rom_data[
                        slot["start"] : slot["start"] + len(game_data)
                    ] = game_data

            with open(output_filepath, "wb") as f_out:
                f_out.write(final_rom_data)

            messagebox.showinfo(
                "Success",
                f"Created {len(self.rom_combiner_game_file_paths)}-Game ROM ({total_rom_bytes/1024/1024:.0f}MB):\n{output_filepath}",
            )

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    # -------------------------------------------------------------------------
    #                         SAVE SPLITTER/COMBINER GUI
    # -------------------------------------------------------------------------

    def setup_save_splitter_ui(self, parent_frame):
        frame = tk.Frame(parent_frame, padx=15, pady=10)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="Combine & Split Save Files (32KB per slot)",
            font=("Helvetica", 11, "bold"),
        ).pack(anchor="w", pady=(0, 5))

        combine_mode_frame = tk.Frame(frame)
        combine_mode_frame.pack(anchor="w")
        tk.Radiobutton(
            combine_mode_frame,
            text="3-Save (96KB)",
            variable=self.savesplit_mode,
            value="3",
            command=self.savesplit_update_ui,
        ).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(
            combine_mode_frame,
            text="4-Save (128KB)",
            variable=self.savesplit_mode,
            value="4",
            command=self.savesplit_update_ui,
        ).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(
            combine_mode_frame,
            text="16-Save (512KB)",
            variable=self.savesplit_mode,
            value="16",
            command=self.savesplit_update_ui,
        ).pack(side=tk.LEFT, padx=5)

        self.select_combine_button = tk.Button(
            frame,
            text="Select Files to Combine",
            command=self.select_files_to_combine,
            width=30,
        )
        self.select_combine_button.pack(pady=5)

        save_list_frame = tk.Frame(frame)
        save_list_frame.pack(fill="x", pady=5)
        self.savesplit_listbox = tk.Listbox(
            save_list_frame, selectmode=tk.SINGLE, width=65, height=8
        )
        save_scroll = tk.Scrollbar(
            save_list_frame,
            orient="vertical",
            command=self.savesplit_listbox.yview,
        )
        self.savesplit_listbox.config(yscrollcommand=save_scroll.set)

        self.savesplit_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        save_scroll.pack(side=tk.RIGHT, fill="y")

        combine_button = tk.Button(
            frame,
            text="Combine into Single Scratchpad .SAV",
            command=self.combine_files,
            width=35,
        )
        combine_button.pack(pady=5)

        tk.Label(frame, text="-" * 70).pack(pady=10)
        split_button = tk.Button(
            frame,
            text="Split Combined .SAV Scratchpad",
            command=self.split_file,
            width=35,
        )
        split_button.pack(pady=5)

        self.savesplit_update_ui()

    def savesplit_update_ui(self):
        max_files = int(self.savesplit_mode.get())
        self.select_combine_button.config(
            text=f"Select Up To {max_files} Save Files"
        )
        if len(self.savesplit_file_paths) > max_files:
            self.savesplit_file_paths = self.savesplit_file_paths[:max_files]
            self.savesplit_update_listbox()

    def select_files_to_combine(self):
        max_files = int(self.savesplit_mode.get())
        filepaths = filedialog.askopenfilenames(
            title=f"Select up to {max_files} Save Files",
            filetypes=[("Save Files", "*.sav"), ("All Files", "*.*")],
        )
        if filepaths:
            self.savesplit_file_paths = list(filepaths[:max_files])
            self.savesplit_update_listbox()

    def savesplit_update_listbox(self):
        self.savesplit_listbox.delete(0, tk.END)
        for i, path in enumerate(self.savesplit_file_paths):
            self.savesplit_listbox.insert(
                tk.END, f"Slot {i+1:02d}: {os.path.basename(path)}"
            )

    def combine_files(self):
        mode_count = int(self.savesplit_mode.get())
        total_size = (
            mode_count * CHUNK_SIZE_BYTES
            if mode_count != 3
            else 128 * 1024
        )

        output_filepath = filedialog.asksaveasfilename(
            defaultextension=".sav",
            title="Save Combined SRAM Scratchpad",
            filetypes=[("Save Files", "*.sav"), ("All Files", "*.*")],
        )
        if not output_filepath:
            return

        try:
            combined_data = bytearray(b"\x00" * total_size)
            start_offset = 1 if mode_count == 3 else 0

            for i, path in enumerate(self.savesplit_file_paths):
                slot_index = i + start_offset
                with open(path, "rb") as f_in:
                    data = f_in.read()
                    start = slot_index * CHUNK_SIZE_BYTES
                    combined_data[
                        start : start + min(len(data), CHUNK_SIZE_BYTES)
                    ] = data[:CHUNK_SIZE_BYTES]

            with open(output_filepath, "wb") as f_out:
                f_out.write(combined_data)

            messagebox.showinfo(
                "Success", f"Combined SRAM created:\n{output_filepath}"
            )

        except Exception as e:
            messagebox.showerror(
                "Error", f"Failed to combine save files: {e}"
            )

    def split_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Multi-Cart SRAM Scratchpad File",
            filetypes=[("Save Files", "*.sav"), ("All Files", "*.*")],
        )
        if not filepath:
            return

        file_size = os.path.getsize(filepath)
        num_chunks = file_size // CHUNK_SIZE_BYTES
        if num_chunks == 0:
            messagebox.showerror(
                "Error", "File is smaller than a single 32KB slot."
            )
            return

        out_dir = filedialog.askdirectory(
            title="Select Output Directory for Extracted Saves"
        )
        if not out_dir:
            return

        try:
            with open(filepath, "rb") as f_in:
                save_data = f_in.read()

            for i in range(num_chunks):
                chunk = save_data[
                    i * CHUNK_SIZE_BYTES : (i + 1) * CHUNK_SIZE_BYTES
                ]
                out_path = os.path.join(out_dir, f"slot_{i+1:02d}.sav")
                with open(out_path, "wb") as f_out:
                    f_out.write(chunk)

            messagebox.showinfo(
                "Success", f"Extracted {num_chunks} slot(s) to:\n{out_dir}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to split save file: {e}")


if __name__ == "__main__":
    app = MultiFunctionTool()
    app.mainloop()