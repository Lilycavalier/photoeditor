import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageOps, ImageDraw
import cv2
import os


#-----------------------------
# UTILITY
#-----------------------------

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.enabled = True
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if not self.enabled or self.tip_window:
            return
        # Get mouse pointer location instead of relying on widget.bbox("insert")
        x = self.widget.winfo_pointerx() + 20
        y = self.widget.winfo_pointery() + 20

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove window decorations
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("tahoma", "9", "normal")
        )
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False
        self.hide_tip()


class PhotoEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Editor")
        self.root.geometry("800x600")

        # Create menu bar
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open\tCtrl+O", command=self.open_image)
        file_menu.add_command(label="Capture\tCtrl+C", command=self.capture_photo)
        file_menu.add_command(label="Save\tCtrl+S", command=self.save_image)
        file_menu.add_separator()
        file_menu.add_command(label="Exit\tCtrl+Q", command=self.exit_program)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo\tCtrl+Z", command=self.undo)
        edit_menu.add_command(label="Redo\tCtrl+Y", command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Revert to original\tCtrl+G", command=self.revert_to_original)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About\tF1", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        # bind keyboard shortcuts
        self.root.bind_all("<Control-o>", lambda event: self.open_image())
        self.root.bind_all("<Control-c>", lambda event: self.capture_photo())
        self.root.bind_all("<Control-s>", lambda event: self.save_image())
        self.root.bind_all("<Control-z>", lambda event: self.undo())
        self.root.bind_all("<Control-y>", lambda event: self.redo())
        self.root.bind_all("<Control-g>", lambda event: self.revert_to_original())
        self.root.bind_all("<Control-q>", lambda event: self.exit_program())
        self.root.bind_all("<F1>", lambda event: self.show_about())

        # Set the menu bar
        self.root.config(menu=menubar)
        self.image = None
        self.tk_image = None
        self.canvas_image_id = None
        self.history_stack = []  # For undo
        self.history_redo_stack = []  # For redo

        self.start_x = self.start_y = self.rect_id = None

        # Zoom attributes
        self.zoom_factor = 1.0
        self.min_zoom = 0.2
        self.max_zoom = 5.0
        self.canvas_offset = [0, 0]  # [x_offset, y_offset]
        self.brightness = 1.0
        self.contrast = 1.0

        # Canvas
        self.canvas = tk.Canvas(root, width=600, height=400, bg='gray')
        self.canvas.pack(pady=20)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)

        self.canvas.config(cursor="arrow")
        self.canvas_tooltip = ToolTip(self.canvas, "Drag your mouse to crop the image")

        # Bind zoom to mousewheel
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows and Mac
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux scroll down

        self.pending_crop_box = None
        self.crop_overlay_ids = []

        # Drawing attributes
        self.drawing_enabled = False
        self.last_draw_pos = None
        self.brush_size = 3
        self.brush_color = "black"

        # Text attributes
        self.text_mode = False
        self.text_font_size = 20
        self.text_color = "black"
        self.text_overlay = None  # To hold the current text input widget temporarily

        # Radiobuttons
        category_frame = tk.Frame(root)
        category_frame.pack(fill='x')

        button_container = tk.Frame(category_frame)
        button_container.pack(anchor='center')

        # Radiobuttons for categories
        self.option_var = tk.StringVar(value="Transform")
        self.category_buttons = []

        for cat in ["Transform", "Filters", "Tone", "Extra"]:
            rb = tk.Radiobutton(button_container, text=cat, variable=self.option_var, value=cat,
                                command=self.update_button_frame)
            rb.pack(side="left", padx=10)
            self.category_buttons.append(rb)

        # Add a horizontal separator
        separator = ttk.Separator(root, orient='horizontal')
        separator.pack(fill='x', pady=5)

        # Container for tool frames
        self.tool_frames = {}

        self.tools_container = tk.Frame(root)
        self.tools_container.pack()

        # Transform tools
        transform_frame = tk.Frame(self.tools_container)
        button_row = tk.Frame(transform_frame)
        tk.Button(button_row, text="Rotate", command=self.append_rotate).pack(side="left", padx=5)
        tk.Button(button_row, text="Flip Horizontal", command=self.flip_horizontal).pack(side="left", padx=5)
        tk.Button(button_row, text="Flip Vertical", command=self.flip_vertical).pack(side="left", padx=5)
        button_row.pack(pady=(0, 10))
        self.crop_controls = tk.Frame(transform_frame)
        tk.Button(self.crop_controls, text="Apply Crop", command=self.append_crop).pack(side="left", padx=5)
        tk.Button(self.crop_controls, text="Cancel Crop", command=self.cancel_crop).pack(side="left", padx=5)
        self.crop_controls.pack_forget()

        # Aspect ratio lock options
        ratio_frame = tk.Frame(transform_frame)
        tk.Label(ratio_frame, text="Aspect Ratio:").pack(side="left")
        self.aspect_ratio_var = tk.StringVar(value="Free")
        for label in ["Free", "1:1", "4:3", "16:9"]:
            tk.Radiobutton(ratio_frame, text=label, variable=self.aspect_ratio_var, value=label).pack(side="left")
        ratio_frame.pack(pady=(0, 10))

        self.tool_frames["Transform"] = transform_frame

        # Filters
        filters_frame = tk.Frame(self.tools_container)

        self.filter_buttons = {}

        self.filter_buttons["grayscale"] = tk.Button(filters_frame, text="Grayscale", command=self.apply_grayscale)
        self.filter_buttons["grayscale"].config(bg="light gray", fg="black")
        self.filter_buttons["grayscale"].pack(side="left", padx=5)

        self.filter_buttons["sepia"] = tk.Button(filters_frame, text="Sepia", command=self.apply_sepia)
        self.filter_buttons["sepia"].config(bg="light gray", fg="black")
        self.filter_buttons["sepia"].pack(side="left", padx=5)

        self.filter_buttons["invert"] = tk.Button(filters_frame, text="Invert", command=self.apply_invert)
        self.filter_buttons["invert"].config(bg="light gray", fg="black")
        self.filter_buttons["invert"].pack(side="left", padx=5)

        self.filter_buttons["blur"] = tk.Button(filters_frame, text="Blur", command=self.apply_blur)
        self.filter_buttons["blur"].config(bg="light gray", fg="black")
        self.filter_buttons["blur"].pack(side="left", padx=5)

        self.tool_frames["Filters"] = filters_frame

        # Track filter toggle states
        self.filter_states = {
            "grayscale": False,
            "sepia": False,
            "invert": False,
            "blur": False
        }

        # Tone adjustments
        tone_frame = tk.Frame(self.tools_container)

        # Brightness slider
        tk.Label(tone_frame, text="Brightness").pack(side="top", pady=2)
        self.brightness_slider = ttk.Scale(tone_frame, from_=0.5, to=1.5, orient='horizontal', value=1.0)
        self.brightness_slider.pack(side="top", fill="x", padx=10)

        # Contrast slider
        tk.Label(tone_frame, text="Contrast").pack(side="top", pady=2)
        self.contrast_slider = ttk.Scale(tone_frame, from_=0.5, to=1.5, orient='horizontal', value=1.0)
        self.contrast_slider.pack(side="top", fill="x", padx=10)

        # Bind same update logic
        # self.brightness_slider.config(command=self.preview_tone_adjustments)
        # self.contrast_slider.config(command=self.preview_tone_adjustments)
        self.brightness_slider.bind("<ButtonRelease-1>", self.append_tone)
        self.contrast_slider.bind("<ButtonRelease-1>", self.append_tone)

        self.tool_frames["Tone"] = tone_frame

        # Extra tools
        extra_frame = tk.Frame(self.tools_container)
        # Add drawing toggle button
        drawing_frame = tk.Frame(extra_frame)
        self.drawing_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            drawing_frame,
            text="Toggle Drawing",
            variable=self.drawing_var,
            command=self.toggle_drawing
        ).pack(side="left", padx=5)
        # Brush size slider
        tk.Label(drawing_frame, text="Brush Size:").pack(side="left", padx=5)
        self.brush_slider = ttk.Scale(drawing_frame, from_=1, to=20, orient='horizontal', command=self.update_brush_size)
        self.brush_slider.set(self.brush_size)
        self.brush_slider.pack(side="left", padx=5)
        drawing_frame.pack(pady=(0, 10))

        # Add text overlay button
        text_frame = tk.Frame(extra_frame)
        tk.Button(text_frame, text="Add Text", command=self.activate_text_mode).pack(side="left", padx=5)
        # Font size spinbox
        tk.Label(text_frame, text="Font Size:").pack(side="left", padx=5)
        self.font_size_var = tk.IntVar(value=self.text_font_size)
        tk.Spinbox(text_frame, from_=8, to=72, textvariable=self.font_size_var, width=5).pack(side="left", padx=5)
        # Text color entry
        tk.Label(text_frame, text="Text Color:").pack(side="left", padx=5)
        self.text_color_var = tk.StringVar(value=self.text_color)
        tk.Entry(text_frame, textvariable=self.text_color_var, width=8).pack(side="left", padx=5)
        text_frame.pack(pady=(0, 10))

        # confirmation button
        # button_frame = tk.Frame(extra_frame)
        # tk.Button(button_frame, text="Confirm", command=self.confirm_changes).pack(side="left", padx=5)
        # tk.Button(button_frame, text="Reset", command=self.reset_changes).pack(side="left", padx=5)
        # button_frame.pack(pady=(0, 10))
        self.tool_frames["Extra"] = extra_frame

        # Load last session image
        if os.path.exists("last_session_image.jpg"):
            if messagebox.askyesno("Load image", "Do you want to load the image from the last session?"):
                self.image = Image.open("last_session_image.jpg")
                self.original_image = self.image.copy()
                self.pre_overlay_image = self.image.copy()
                self.history_stack.clear()
                self.history_redo_stack.clear()
                self.brightness_slider.set(1.0)
                self.contrast_slider.set(1.0)
                self.reset_filter_states()
                self.update_filter_button_colors()
                self.update_filtered_image()
                self.set_category_buttons_state("normal")
                self.set_all_controls_state("normal")
                self.root.after(100, self.reset_zoom())
            else:
                self.set_category_buttons_state("disabled")
                self.set_all_controls_state("disabled")
                self.canvas_tooltip.disable()
                self.canvas.create_text(300, 200, text="Load or capture an image to begin.", fill="white",
                                        font=("Arial", 16))

        self.update_button_frame()
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # utility functions

    def update_button_frame(self):
        selected = self.option_var.get()
        if selected != "Extra":
            self.canvas.config(cursor="arrow")
        if selected == "Transform":
            self.canvas_tooltip.enable()
        else:
            self.canvas_tooltip.disable()
        for frame in self.tool_frames.values():
            frame.pack_forget()
        self.tool_frames[selected].pack()

    def set_category_buttons_state(self, state):
        for btn in self.category_buttons:
            btn.config(state=state)

    def set_state_recursive(self, widget, state):
        for child in widget.winfo_children():
            if isinstance(child, (tk.Button, ttk.Scale, tk.Radiobutton)):
                child.config(state=state)
            # recurse deeper
            self.set_state_recursive(child, state)

    def set_all_controls_state(self, state):
        for frame in self.tool_frames.values():
            self.set_state_recursive(frame, state)

    def reset_filter_states(self):
        self.filter_states = {
            "grayscale": False,
            "sepia": False,
            "invert": False,
            "blur": False
        }

    # undo/redo logic

    def push_state(self, action_type, data):
        if self.image:
            """
            action_type: 'image' or 'overlay'
            data: For 'image' – dict with image and UI state;
                  For 'overlay' – dict with action info (stroke or text)
            """
            self.history_stack.append({
                "type": action_type,
                "data": data
            })
            self.history_redo_stack.clear()

    def undo(self):
        if not self.history_stack:
            return
        last = self.history_stack.pop()
        self.history_redo_stack.append(last)

        self.apply_all_edits()

    def redo(self):
        if not self.history_redo_stack:
            return
        action = self.history_redo_stack.pop()
        self.history_stack.append(action)

        self.apply_all_edits()

    # menu functions

    def show_about(self):
        messagebox.showinfo("About", "Simple Photo Editor\nCreated with Tkinter and Pillow.")

    def open_image(self):
        self.brightness_slider.set(1.0)
        self.contrast_slider.set(1.0)
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if path:
            self.image = Image.open(path)
            self.original_image = self.image.copy()
            self.pre_overlay_image = self.image.copy()
            self.history_stack.clear()
            self.history_redo_stack.clear()
            self.brightness_slider.set(1.0)
            self.contrast_slider.set(1.0)
            self.reset_filter_states()
            self.update_filter_button_colors()
            self.update_filtered_image()
            self.set_category_buttons_state("normal")
            self.set_all_controls_state("normal")
            if self.option_var.get() == "Transform":
                self.canvas_tooltip.enable()
            self.reset_zoom()

    def capture_photo(self):
        self.brightness_slider.set(1.0)
        self.contrast_slider.set(1.0)
        loading_win = tk.Toplevel()
        loading_win.title("Loading")
        loading_win.geometry("200x100")
        loading_win.resizable(False, False)
        loading_label = tk.Label(loading_win, text="Initializing webcam...", font=("Arial", 12))
        loading_label.pack(expand=True)

        loading_win.grab_set()
        loading_win.update()

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Webcam not found.")
            loading_win.destroy()
            return

        loading_win.destroy()

        messagebox.showinfo("Webcam", "Press SPACE to capture, ESC to cancel.")
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

            # Draw rectangles around detected faces - Make a copy for display (with rectangles)
            display_frame = frame.copy()
            for (x, y, w, h) in faces:
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), (255, 255, 255), 2)

            cv2.imshow("Press SPACE to capture", display_frame)

            key = cv2.waitKey(1)
            if key == 27:  # ESC to cancel
                cap.release()
                cv2.destroyAllWindows()
                return
            elif key == 32:  # SPACE to capture
                cv2.imwrite("captured_webcam_image.jpg", frame)
                cap.release()
                cv2.destroyAllWindows()
                with Image.open("captured_webcam_image.jpg") as img:
                    self.image = img.copy()
                os.remove("captured_webcam_image.jpg")  # delete immediately after loading
                self.original_image = self.image.copy()
                self.pre_overlay_image = self.image.copy()
                self.history_stack.clear()
                self.history_redo_stack.clear()
                self.brightness_slider.set(1.0)
                self.contrast_slider.set(1.0)
                self.reset_filter_states()
                self.update_filter_button_colors()
                self.update_filtered_image()
                self.set_category_buttons_state("normal")
                self.set_all_controls_state("normal")
                if self.option_var.get() == "Transform":
                    self.canvas_tooltip.enable()
                self.reset_zoom()
                return

    def display_image(self):
        if self.image:
            img = self.image.copy()
            img_width, img_height = img.size

            # Resize for zoom
            zoomed_width = int(img_width * self.zoom_factor)
            zoomed_height = int(img_height * self.zoom_factor)
            img = img.resize((zoomed_width, zoomed_height), Image.Resampling.LANCZOS)

            self.tk_image = ImageTk.PhotoImage(img)
            self.canvas.delete("all")

            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 1 or canvas_height <= 1:
                # This ensures the canvas is fully initialized
                canvas_width = 600
                canvas_height = 400

            # Default center if no offset
            if not hasattr(self, "canvas_offset"):
                self.canvas_offset = [canvas_width // 2 - zoomed_width // 2,
                                      canvas_height // 2 - zoomed_height // 2]

            # Draw image at offset
            self.canvas_image_id = self.canvas.create_image(
                self.canvas_offset[0], self.canvas_offset[1],
                anchor="nw", image=self.tk_image
            )

            # Update displayed image info for cropping
            self.displayed_image_info = {
                "x": self.canvas_offset[0],
                "y": self.canvas_offset[1],
                "width": zoomed_width,
                "height": zoomed_height,
                "scale_x": self.image.size[0] / zoomed_width,
                "scale_y": self.image.size[1] / zoomed_height
            }

    # zoom utility functions

    def on_mouse_wheel(self, event):
        if not self.image:
            return

        # Determine zoom direction
        if event.num == 4 or event.delta > 0:
            scale = 1.1
        elif event.num == 5 or event.delta < 0:
            scale = 0.9
        else:
            return

        # Compute new zoom factor within limits
        new_zoom = self.zoom_factor * scale
        if not (self.min_zoom <= new_zoom <= self.max_zoom):
            return

        # Get mouse pointer coordinates relative to canvas
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # Adjust offset so the image zooms around the cursor
        self.canvas_offset[0] = (self.canvas_offset[0] - canvas_x) * scale + canvas_x
        self.canvas_offset[1] = (self.canvas_offset[1] - canvas_y) * scale + canvas_y

        self.zoom_factor = new_zoom
        self.display_image()

    def reset_zoom(self):
        if not self.image:
            return

        img_width, img_height = self.image.size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Calculate zoom factor to fit image inside canvas
        zoom_x = canvas_width / img_width
        zoom_y = canvas_height / img_height
        self.zoom_factor = min(zoom_x, zoom_y, self.max_zoom)

        # Calculate new zoomed image size
        zoomed_width = int(img_width * self.zoom_factor)
        zoomed_height = int(img_height * self.zoom_factor)

        # Center the image
        offset_x = (canvas_width - zoomed_width) // 2
        offset_y = (canvas_height - zoomed_height) // 2
        self.canvas_offset = [offset_x, offset_y]

        self.display_image()

    # mouse-canvas utility functions

    def on_mouse_press(self, event):
        if not self.image:
            return  # Do nothing if no image is loaded
        if self.option_var.get() == "Transform":
            # Cropping mode
            self.start_x = event.x
            self.start_y = event.y

            # Remove existing crop rectangle
            if self.rect_id:
                self.canvas.delete(self.rect_id)
                # self.rect_id = None
            self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y,
                                                        outline='black')
        elif self.option_var.get() == "Extra" and self.drawing_enabled:
            # Drawing mode
            self.last_draw_pos = (event.x, event.y)
            self.current_stroke = []
        elif self.option_var.get() == "Extra" and self.text_mode:
            # Remove previous overlay if any
            if self.text_overlay:
                self.text_overlay.destroy()
                self.text_overlay = None

            try:
                self.text_overlay = tk.Text(
                    self.canvas,
                    height=1,
                    width=20,
                    font=("Arial", self.font_size_var.get()),
                    fg=self.text_color_var.get()
                )
                # Position text input box at click location
                self.text_overlay.place(x=event.x, y=event.y)
                self.text_overlay.focus_set()
                self.text_overlay.bind("<Return>", self.finish_text_overlay)
                self.text_overlay.bind("<Escape>", lambda e: self.text_overlay.destroy())
            except tk.TclError:
                # Show error message and reset to safe default color
                messagebox.showerror("Invalid Color",
                                     "The color you entered is not valid.\nPlease use a valid color name or hex code.")
        else:
            self.last_draw_pos = None

    def on_mouse_drag(self, event):
        if not self.image:
            return  # Do nothing if no image is loaded
        if self.option_var.get() == "Transform":
            end_x = event.x
            end_y = event.y

            # Aspect ratio lock logic
            ar = self.aspect_ratio_var.get()
            dx = end_x - self.start_x
            dy = end_y - self.start_y

            if ar != "Free":
                abs_dx, abs_dy = abs(dx), abs(dy)

                if ar == "1:1":
                    side = min(abs_dx, abs_dy)
                    end_x = self.start_x + side if dx >= 0 else self.start_x - side
                    end_y = self.start_y + side if dy >= 0 else self.start_y - side
                elif ar == "4:3":
                    ratio = 4 / 3
                    if abs_dx > abs_dy:
                        end_y = self.start_y + (abs_dx / ratio if dy >= 0 else -abs_dx / ratio)
                    else:
                        end_x = self.start_x + (abs_dy * ratio if dx >= 0 else -abs_dy * ratio)
                elif ar == "16:9":
                    ratio = 16 / 9
                    if abs_dx > abs_dy:
                        end_y = self.start_y + (abs_dx / ratio if dy >= 0 else -abs_dx / ratio)
                    else:
                        end_x = self.start_x + (abs_dy * ratio if dx >= 0 else -abs_dy * ratio)

            # Draw the main crop rectangle
            if self.rect_id:
                self.canvas.coords(self.rect_id, self.start_x, self.start_y, end_x, end_y)

                # Remove old overlays
                for oid in self.crop_overlay_ids:
                    self.canvas.delete(oid)
                self.crop_overlay_ids.clear()

                # Add new overlay rectangles
                x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
                x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)
                w, h = self.canvas.winfo_width(), self.canvas.winfo_height()

                self.crop_overlay_ids.extend([
                    self.canvas.create_rectangle(0, 0, w, y1, fill="black", stipple="gray25", width=0),
                    self.canvas.create_rectangle(0, y1, x1, y2, fill="black", stipple="gray25", width=0),
                    self.canvas.create_rectangle(x2, y1, w, y2, fill="black", stipple="gray25", width=0),
                    self.canvas.create_rectangle(0, y2, w, h, fill="black", stipple="gray25", width=0)
                ])
        elif self.option_var.get() == "Extra" and self.drawing_enabled and self.last_draw_pos:
            x1, y1 = self.last_draw_pos
            x2, y2 = event.x, event.y
            # Draw line on canvas for preview
            self.canvas.create_line(x1, y1, x2, y2,
                                    width=self.brush_size,
                                    fill=self.brush_color,
                                    capstyle=tk.ROUND, smooth=True)
            # Draw on the PIL image as well
            scale_x = self.image.size[0] / self.displayed_image_info["width"]
            scale_y = self.image.size[1] / self.displayed_image_info["height"]

            # Adjust coords relative to displayed image offset and scale
            adj_x1 = int((x1 - self.displayed_image_info["x"]) * scale_x)
            adj_y1 = int((y1 - self.displayed_image_info["y"]) * scale_y)
            adj_x2 = int((x2 - self.displayed_image_info["x"]) * scale_x)
            adj_y2 = int((y2 - self.displayed_image_info["y"]) * scale_y)

            # Save the stroke as an action
            self.current_stroke.append({
                "type": "stroke",
                "coords": [(adj_x1, adj_y1), (adj_x2, adj_y2)],
                "color": self.brush_color,
                "width": self.brush_size
            })

            self.last_draw_pos = (x2, y2)

    def on_mouse_release(self, event):
        if not self.image: # or not self.rect_id:
            return  # Do nothing if no image or rectangle
        if self.option_var.get() == "Transform" and self.rect_id:
            bbox = self.canvas.bbox(self.rect_id)
            # Keep the black crop rectangle visible — do not delete it here

            # Keep overlay visible — do not delete yet

            if not bbox or bbox[2] - bbox[0] < 10 or bbox[3] - bbox[1] < 10:
                return

            # Limit to image area on canvas
            info = self.displayed_image_info
            x1 = max(bbox[0], info["x"])
            y1 = max(bbox[1], info["y"])
            x2 = min(bbox[2], info["x"] + info["width"])
            y2 = min(bbox[3], info["y"] + info["height"])

            # Convert canvas to image coordinates
            left = int((x1 - info["x"]) * info["scale_x"])
            upper = int((y1 - info["y"]) * info["scale_y"])
            right = int((x2 - info["x"]) * info["scale_x"])
            lower = int((y2 - info["y"]) * info["scale_y"])

            if right - left > 10 and lower - upper > 10:
                self.pending_crop_box = (left, upper, right, lower)
                self.crop_controls.pack(pady=2)
        elif self.option_var.get() == "Extra" and self.drawing_enabled:
            if self.current_stroke:
                self.push_state("overlay", {
                    "action": {
                        "type": "stroke_group",
                        "strokes": self.current_stroke
                    }
                })
                self.apply_all_edits()
            self.last_draw_pos = None

    # cropping utility functions

    def append_crop(self):
        self.push_state("crop", {
                "box": self.pending_crop_box
            })
        self.pending_crop_box = None
        self.crop_controls.pack_forget()
        # Remove overlay artifacts
        self.clear_crop_overlay()
        self.apply_all_edits()

    def apply_crop(self, box):
        if self.image:
            self.image = self.image.crop(box)
            self.pre_overlay_image = self.image.copy()

    def cancel_crop(self):
        self.pending_crop_box = None
        self.crop_controls.pack_forget()
        self.display_image()
        # Remove overlay artifacts
        self.clear_crop_overlay()

    def clear_crop_overlay(self):
        for oid in self.crop_overlay_ids:
            self.canvas.delete(oid)
        self.crop_overlay_ids.clear()

        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None

    # transforming functions

    def append_rotate(self):
        self.push_state("rotate", {
            "angle": 90
        })
        self.apply_all_edits()

    def rotate_image(self, angle):
        if self.image:
            self.image = self.image.rotate(angle, expand=True)
            self.pre_overlay_image = self.image.copy()

    def flip_vertical(self):
        self.push_state("flip", {
            "direction": "vertical"
        })
        self.apply_all_edits()

    def flip_horizontal(self):
        self.push_state("flip", {
            "direction": "horizontal"
        })
        self.apply_all_edits()

    def apply_flip(self, dir):
        if self.image:
            if dir == "vertical":
                self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
            elif dir == "horizontal":
                self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
            self.pre_overlay_image = self.image.copy()

    # filter functions

    def append_filter(self):
        self.push_state("filter", {
            "filters": self.filter_states
        })
        self.apply_all_edits()

    def apply_grayscale(self):
        self.filter_states["grayscale"] = not self.filter_states["grayscale"]
        self.append_filter()

    def apply_sepia(self):
        self.filter_states["sepia"] = not self.filter_states["sepia"]
        self.append_filter()

    def apply_invert(self):
        self.filter_states["invert"] = not self.filter_states["invert"]
        self.append_filter()

    def apply_blur(self):
        self.filter_states["blur"] = not self.filter_states["blur"]
        self.append_filter()

    def update_filter_button_colors(self):
        for name, button in self.filter_buttons.items():
            if self.filter_states.get(name):
                button.config(bg="white", fg="black")
            else:
                button.config(bg="light gray", fg="black")

    def update_filtered_image(self):
        if not hasattr(self, 'original_image') or self.original_image is None:
            return

        img = self.image.copy()

        if self.filter_states["grayscale"]:
            img = img.convert("L").convert("RGB")

        if self.filter_states["sepia"]:
            pixels = img.load()
            for py in range(img.size[1]):
                for px in range(img.size[0]):
                    r, g, b = pixels[px, py]
                    tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                    tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                    tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                    pixels[px, py] = (min(255, tr), min(255, tg), min(255, tb))

        if self.filter_states["invert"]:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img = ImageOps.invert(img)

        if self.filter_states["blur"]:
            img = img.filter(ImageFilter.GaussianBlur(10))

        # print(self.history_stack[-1])

        self.image = img

    # tone functions

    def append_tone(self, event=None):
        self.push_state("tone", {
            "brightness": self.brightness_slider.get(),
            "contrast": self.contrast_slider.get(),
        })
        self.apply_all_edits()

    def apply_tone_adjustments(self, event=None):
        if self.image:
            self.image = ImageEnhance.Brightness(self.image).enhance(self.brightness)
            self.image = ImageEnhance.Contrast(self.image).enhance(self.contrast)

    def preview_tone_adjustments(self, event=None):
        if self.image:
            brightness = float(self.brightness_slider.get())
            contrast = float(self.contrast_slider.get())

            img = ImageEnhance.Brightness(self.original_image).enhance(brightness)
            img = ImageEnhance.Contrast(img).enhance(contrast)

            self.image = img
            self.display_image()

    # extra functions

    def toggle_drawing(self):
        if self.drawing_var.get():
            # Save a backup before drawing starts once
            if not hasattr(self, 'pre_overlay_image'):
                self.pre_overlay_image = self.image.copy()
            self.drawing_enabled = not self.drawing_enabled
            self.text_mode = False  # disable text mode if drawing enabled
            self.last_draw_pos = None
            if self.drawing_enabled:
                self.canvas.config(cursor="pencil")
        else:
            self.drawing_enabled = not self.drawing_enabled
            self.canvas.config(cursor="arrow")

    def update_brush_size(self, val):
        self.brush_size = int(float(val))

    def activate_text_mode(self):
        # Save backup before text if not already defined through drawing
        if not hasattr(self, 'pre_overlay_image'):
            self.pre_overlay_image = self.image.copy()
        self.text_mode = True
        if self.drawing_var.get():
            self.drawing_var.set(False)
            self.drawing_enabled = False
        self.canvas.config(cursor="xterm")

    def finish_text_overlay(self, event=None):
        if not self.text_overlay:
            return "break"

        text = self.text_overlay.get("1.0", "end-1c").strip()
        x, y = self.text_overlay.winfo_x(), self.text_overlay.winfo_y()
        font_size = self.font_size_var.get()
        color = self.text_color_var.get()

        if text:
            # Save action instead of drawing directly to the image
            self.push_state("overlay", {
                "action": {
                    "type": "text",
                    "text": text,
                    "position": (x, y),
                    "font_size": font_size,
                    "color": color
                }
            })

            self.apply_all_edits()

        # Clean up the overlay input
        self.text_overlay.destroy()
        self.text_overlay = None
        self.text_mode = False
        self.canvas.config(cursor="arrow")
        return "break"

    def reapply_overlay_actions(self):
        if not hasattr(self, 'pre_overlay_image') or self.pre_overlay_image is None:
            return

        # Start from a clean image (before overlays)
        self.image = self.pre_overlay_image.copy()
        draw = ImageDraw.Draw(self.image)

        for entry in self.history_stack:
            if entry["type"] != "overlay":
                continue

            action = entry["data"]["action"]

            # if action["type"] == "stroke":
                # draw.line(action["coords"], fill=action["color"], width=action["width"])

            if action["type"] == "stroke_group":
                for stroke in action["strokes"]:
                    draw.line(stroke["coords"], fill=stroke["color"], width=stroke["width"])

            elif action["type"] == "text":
                try:
                    from PIL import ImageFont
                    font = ImageFont.truetype("arial.ttf", action["font_size"]*4)
                except:
                    font = None  # Use default if arial.ttf is not found
                draw.text(action["position"], action["text"], font=font, fill=action["color"])

    def apply_all_edits(self):
        self.image = self.original_image.copy()
        self.reset_filter_states()
        self.brightness = 1.0
        self.contrast = 1.0
        for i in self.history_stack:
            if i["type"] == "crop":
                self.apply_crop(i["data"]["box"])
            elif i["type"] == "rotate":
                self.rotate_image(i["data"]["angle"])
            elif i["type"] == "flip":
                self.apply_flip(i["data"]["direction"])
            elif i["type"] == "filter":
                self.filter_states = i["data"]["filters"]
            elif i["type"] == "tone":
                self.brightness = float(i["data"]["brightness"])
                self.contrast = float(i["data"]["contrast"])
            elif i["type"] == "overlay":
                self.reapply_overlay_actions()
        self.update_filter_button_colors()
        self.update_filtered_image()
        self.apply_tone_adjustments()
        self.brightness_slider.set(self.brightness)
        self.contrast_slider.set(self.contrast)
        self.display_image()

    def revert_to_original(self):
        if self.image and hasattr(self, 'original_image'):
            self.image = self.original_image.copy()
            self.pre_overlay_image = self.image.copy()
            self.history_stack.clear()
            self.history_redo_stack.clear()
            self.display_image()

    # save & exit functions

    def save_image(self):
        if self.image:
            save_path = filedialog.asksaveasfilename(defaultextension=".jpg",
                                                     filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
            if save_path:
                self.image.save(save_path)
                messagebox.showinfo("Saved", f"Image saved to {save_path}")

    def exit_program(self):
        if self.image:
            if messagebox.askyesno("Save", "Do you want to save your changes before exiting?"):
                self.save_image()
            self.image.save("last_session_image.jpg")
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoEditor(root)

    def on_closing():
        if app.image:
            # Save to a hidden temporary file or a known file path
            app.image.save("last_session_image.jpg")
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
