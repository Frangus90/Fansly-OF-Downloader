"""
UI layout builder
"""

import customtkinter as ctk


def build_layout(parent, state, handlers):
    """Build the complete UI layout with 2-column design"""
    main_frame = ctk.CTkFrame(parent)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Configure 2-column grid (70/30 split) with minimum widths
    main_frame.grid_columnconfigure(0, weight=7, minsize=480)  # Left column: 70%, min 480px
    main_frame.grid_columnconfigure(1, weight=3, minsize=420)  # Right column: 30%, min 420px
    main_frame.grid_rowconfigure(0, weight=1)

    sections = {}

    # LEFT COLUMN FRAME
    left_frame = ctk.CTkFrame(main_frame)
    left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

    # Auth section (left)
    from gui.widgets.auth_section import AuthSection

    sections["auth"] = AuthSection(left_frame, state.config)
    sections["auth"].pack(fill="x", padx=10, pady=5)

    # Settings section (left)
    from gui.widgets.settings_section import SettingsSection

    sections["settings"] = SettingsSection(left_frame, state.config)
    sections["settings"].pack(fill="x", padx=10, pady=5)

    # Tools section (left)
    sections["tools"] = build_tools_section(left_frame, handlers)

    # Progress section (left)
    from gui.widgets.progress_section import ProgressSection

    sections["progress"] = ProgressSection(left_frame)
    sections["progress"].pack(fill="x", padx=10, pady=5)

    # Control buttons (left)
    sections["buttons"] = build_control_buttons(left_frame, handlers)

    # Log section (left, expandable)
    from gui.widgets.log_section import LogSection

    sections["log"] = LogSection(left_frame)
    sections["log"].pack(fill="both", expand=True, padx=10, pady=5)

    # Status bar (left)
    sections["status"] = build_status_bar(left_frame)

    # RIGHT COLUMN FRAME
    right_frame = ctk.CTkFrame(main_frame)
    right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    # Creator section (right, full height)
    from gui.widgets.creator_section import CreatorSection

    sections["creator"] = CreatorSection(
        right_frame,
        state.config,
        state,
        import_callback=handlers.import_subscriptions
    )
    sections["creator"].pack(fill="both", expand=True, padx=5, pady=5)

    return sections


def build_control_buttons(parent, handlers):
    """Build start/stop buttons"""
    button_frame = ctk.CTkFrame(parent)
    button_frame.pack(fill="x", padx=10, pady=10)

    start_btn = ctk.CTkButton(
        button_frame,
        text="Start Download",
        command=handlers.on_start_download,
        height=40,
        font=("Arial", 14, "bold"),
        fg_color="#28a745",
    )
    start_btn.pack(side="left", expand=True, fill="x", padx=5)

    stop_btn = ctk.CTkButton(
        button_frame,
        text="Stop",
        command=handlers.on_stop_download,
        height=40,
        font=("Arial", 14),
        fg_color="#dc3545",
        state="disabled",
    )
    stop_btn.pack(side="left", expand=True, fill="x", padx=5)

    return {"frame": button_frame, "start": start_btn, "stop": stop_btn}


def build_status_bar(parent):
    """Build status bar"""
    status_label = ctk.CTkLabel(parent, text="Status: Idle", anchor="w")
    status_label.pack(fill="x", padx=10, pady=5)

    return status_label


def build_tools_section(parent, handlers):
    """Build tools section with Image Crop Tool button"""
    tools_frame = ctk.CTkFrame(parent)
    tools_frame.pack(fill="x", padx=10, pady=5)

    # Title
    title = ctk.CTkLabel(
        tools_frame,
        text="Tools - Image Crop Tool",
        font=("Arial", 16, "bold"),
        anchor="w"
    )
    title.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

    # Image Crop Tool button
    crop_btn = ctk.CTkButton(
        tools_frame,
        text="Open Image Crop Tool",
        command=handlers.on_open_crop_tool,
        height=35,
        font=("Arial", 12),
        fg_color="#3b8ed0",
    )
    crop_btn.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")

    # Configure grid
    tools_frame.grid_columnconfigure(0, weight=1)

    return tools_frame
