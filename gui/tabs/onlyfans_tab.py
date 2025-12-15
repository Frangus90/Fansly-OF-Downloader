"""OnlyFans Tab Layout

Build OnlyFans UI using similar structure to Fansly
"""

import customtkinter as ctk
from gui.layout import build_tools_section


def build_onlyfans_layout(parent, state, handlers, toggle_log_callback=None, check_update_callback=None):
    """Build OnlyFans UI layout (mirrors Fansly structure)"""
    main_frame = ctk.CTkFrame(parent)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Configure 2-column grid (70/30 split)
    main_frame.grid_columnconfigure(0, weight=7)
    main_frame.grid_columnconfigure(1, weight=3)
    main_frame.grid_rowconfigure(0, weight=1)

    sections = {}

    # LEFT COLUMN
    left_frame = ctk.CTkFrame(main_frame)
    left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

    # OF Auth section
    from gui.widgets.onlyfans_auth import OnlyFansAuthSection
    sections["auth"] = OnlyFansAuthSection(left_frame, state.config)
    sections["auth"].pack(fill="x", padx=10, pady=5)

    # Settings (OF-specific - simplified)
    from gui.widgets.onlyfans_settings_section import OnlyFansSettingsSection
    sections["settings"] = OnlyFansSettingsSection(left_frame, state.config)
    sections["settings"].pack(fill="x", padx=10, pady=5)

    # Tools section (reuse - includes Image Crop Tool)
    sections["tools"] = build_tools_section(left_frame, handlers)

    # Progress section (reuse)
    from gui.widgets.progress_section import ProgressSection
    sections["progress"] = ProgressSection(left_frame)
    sections["progress"].pack(fill="x", padx=10, pady=5)

    # Control buttons
    sections["buttons"] = build_of_control_buttons(left_frame, handlers)

    # Status bar (includes log toggle button and update button)
    sections["status"] = build_of_status_bar(left_frame, toggle_log_callback, check_update_callback)

    # RIGHT COLUMN
    right_frame = ctk.CTkFrame(main_frame)
    right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    # Creator section (reuse with OF flag)
    from gui.widgets.creator_section import CreatorSection
    sections["creator"] = CreatorSection(
        right_frame,
        state.config,
        state,
        import_callback=handlers.import_subscriptions
    )
    sections["creator"].pack(fill="both", expand=True, padx=5, pady=5)

    return sections


def build_of_control_buttons(parent, handlers):
    """Build OF start/stop buttons"""
    button_frame = ctk.CTkFrame(parent)
    button_frame.pack(fill="x", padx=10, pady=10)

    start_btn = ctk.CTkButton(
        button_frame,
        text="Start OF Download",
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


def build_of_status_bar(parent, toggle_log_callback=None, check_update_callback=None):
    """Build OF status bar with log toggle button and check for update button"""
    status_frame = ctk.CTkFrame(parent)
    status_frame.pack(fill="x", padx=10, pady=(5, 10))

    # Status label (left)
    status_label = ctk.CTkLabel(
        status_frame,
        text="Ready - OnlyFans",
        font=("Arial", 12),
        anchor="w"
    )
    status_label.pack(side="left", padx=5)

    # Log toggle button (right)
    log_button = None
    if toggle_log_callback:
        log_button = ctk.CTkButton(
            status_frame,
            text="Show Log",
            command=toggle_log_callback,
            width=100,
            height=28
        )
        log_button.pack(side="right", padx=5)

    # Check for Update button (right, before log button)
    update_button = None
    if check_update_callback:
        update_button = ctk.CTkButton(
            status_frame,
            text="Check for Update",
            command=check_update_callback,
            width=130,
            height=28,
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        update_button.pack(side="right", padx=5)

    return {"label": status_label, "log_button": log_button, "update_button": update_button}
