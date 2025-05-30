import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageOps
import cv2
import os
import numpy


#-----------------------------
# UTILITY
#-----------------------------

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return

        # Get mouse pointer location instead of relying on widget.bbox("insert")
        x = self.widget.winfo_pointerx() + 20
        y = self.widget.winfo_pointery() + 20

        self.tipwindow = tw = tk.Toplevel(self.widget)
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
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


class PhotoEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Photo Editor")
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
        self.root.bind_all("<Control-q>", lambda event: self.exit_program())
        self.root.bind_all("<F1>", lambda event: self.show_about())

        # Set the menu bar
        self.root.config(menu=menubar)
        self.image = None
        # self.adjustment_base_image = None  # Used to preserve original state for brightness/contrast adjustments
        self.tk_image = None
        self.canvas_image_id = None
        self.image_stack = []
        self.redo_stack = []

        self.start_x = self.start_y = self.rect_id = None

        # Canvas
        self.canvas = tk.Canvas(root, width=600, height=400, bg='gray')
        self.canvas.pack(pady=20)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        ToolTip(self.canvas, "Drag your mouse to crop the image")

        self.pending_crop_box = None
        self.crop_overlay_ids = []

        # Radiobuttons
        category_frame = tk.Frame(root)
        category_frame.pack(fill='x')

        button_container = tk.Frame(category_frame)
        button_container.pack(anchor='center')

        # Radiobuttons for categories
        self.option_var = tk.StringVar(value="Transform")
        for cat in ["Transform", "Filters", "Tone", "Extra"]:
            rb = tk.Radiobutton(button_container, text=cat, variable=self.option_var, value=cat,
                                command=self.update_button_frame)
            rb.pack(side="left", padx=10)

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
        tk.Button(button_row, text="Rotate", command=lambda: self.rotate_image(90)).pack(side="left", padx=5)
        tk.Button(button_row, text="Flip Horizontal", command=self.flip_horizontal).pack(side="left", padx=5)
        tk.Button(button_row, text="Flip Vertical", command=self.flip_vertical).pack(side="left", padx=5)
        button_row.pack(pady=(0, 10))
        self.crop_controls = tk.Frame(transform_frame)
        tk.Button(self.crop_controls, text="Apply Crop", command=self.apply_crop).pack(side="left", padx=5)
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
        tk.Button(filters_frame, text="Grayscale", command=self.apply_grayscale).pack(side="left", padx=5)
        tk.Button(filters_frame, text="Sepia", command=self.apply_sepia).pack(side="left", padx=5)
        tk.Button(filters_frame, text="Invert", command=self.apply_invert).pack(side="left", padx=5)
        tk.Button(filters_frame, text="Blur", command=self.apply_blur).pack(side="left", padx=5)
        self.tool_frames["Filters"] = filters_frame

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
        self.brightness_slider.config(command=self.preview_tone_adjustments)
        self.contrast_slider.config(command=self.preview_tone_adjustments)
        self.brightness_slider.bind("<ButtonPress-1>", self.prepare_for_tone_adjustment)
        self.contrast_slider.bind("<ButtonPress-1>", self.prepare_for_tone_adjustment)

        self.tool_frames["Tone"] = tone_frame

        # Extra tools
        extra_frame = tk.Frame(self.tools_container)
        tk.Button(extra_frame, text="Detect Faces", command=self.detect_faces).pack(side="left", padx=5)
        tk.Button(extra_frame, text="Reset", command=self.undo).pack(side="left", padx=5)
        self.tool_frames["Extra"] = extra_frame

        # Load last session image
        if os.path.exists("last_session_image.jpg"):
            if messagebox.askyesno("Load image", "Do you want to load the image from the last session?"):
                self.image = Image.open("last_session_image.jpg")
                self.original_image = self.image.copy()
                self.brightness_slider.set(1.0)
                self.contrast_slider.set(1.0)
                self.push_state()
                self.root.after(100, self.display_image)

        self.update_button_frame()
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def update_button_frame(self):
        selected = self.option_var.get()
        for frame in self.tool_frames.values():
            frame.pack_forget()
        self.tool_frames[selected].pack()

    def push_state(self):
        if self.image:
            state = {
                "image": self.image.copy(),
                "brightness": self.brightness_slider.get(),
                "contrast": self.contrast_slider.get()
                # add rotation and flip to make even better
            }
            self.image_stack.append(state)
            if len(self.image_stack) > 20:
                self.image_stack.pop(0)
            self.redo_stack.clear()

    def undo(self):
        if self.image_stack:
            current_state = {
                "image": self.image.copy(),
                "brightness": self.brightness_slider.get(),
                "contrast": self.contrast_slider.get()
            }
            self.redo_stack.append(current_state)

            last_state = self.image_stack.pop()
            self.image = last_state["image"]
            self.brightness_slider.set(last_state["brightness"])
            self.contrast_slider.set(last_state["contrast"])
            self.display_image()

    def redo(self):
        if self.redo_stack:
            current_state = {
                "image": self.image.copy(),
                "brightness": self.brightness_slider.get(),
                "contrast": self.contrast_slider.get()
            }
            self.image_stack.append(current_state)

            next_state = self.redo_stack.pop()
            self.image = next_state["image"]
            self.brightness_slider.set(next_state["brightness"])
            self.contrast_slider.set(next_state["contrast"])
            self.display_image()

    def show_about(self):
        messagebox.showinfo("About", "Simple Photo Editor\nCreated with Tkinter and Pillow.")

    def open_image(self):
        self.brightness_slider.set(1.0)
        self.contrast_slider.set(1.0)
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if path:
            self.image = Image.open(path)
            self.push_state()
            self.original_image = self.image.copy()
            self.display_image()

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

            # Draw rectangles around detected faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)

            cv2.imshow("Press SPACE to capture", frame)
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
                self.push_state()
                self.original_image = self.image.copy()
                self.display_image()
                return

    def display_image(self):
        if self.image:
            # Get original image size
            img = self.image.copy()
            img_width, img_height = img.size

            # Get canvas size
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 1 or canvas_height <= 1:
                # This ensures the canvas is fully initialized
                canvas_width = 600
                canvas_height = 400

            # Calculate the resize ratio while keeping aspect ratio
            ratio = min(canvas_width / img_width, canvas_height / img_height)
            new_size = (int(img_width * ratio), int(img_height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Display image on canvas
            self.tk_image = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            x_center = canvas_width // 2
            y_center = canvas_height // 2
            self.canvas_image_id = self.canvas.create_image(x_center, y_center, image=self.tk_image)

            # Store coordinates of image on canvas for cropping
            self.displayed_image_info = {
                "x": x_center - new_size[0] // 2,
                "y": y_center - new_size[1] // 2,
                "width": new_size[0],
                "height": new_size[1],
                "scale_x": self.image.size[0] / new_size[0],
                "scale_y": self.image.size[1] / new_size[1]
            }

    # cropping utility functions

    def on_mouse_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='black')

    def on_mouse_drag(self, event):
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

    def on_mouse_release(self, event):
        if self.image and self.rect_id:
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

    def apply_crop(self):
        if self.pending_crop_box:
            self.push_state()
            self.image = self.image.crop(self.pending_crop_box)
            self.pending_crop_box = None
            self.crop_controls.pack_forget()
            self.display_image()
            # Remove overlay artifacts
            self.clear_crop_overlay()

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

    def rotate_image(self, angle):
        if self.image:
            self.push_state()
            self.image = self.image.rotate(angle, expand=True)
            self.display_image()

    def flip_horizontal(self):
        if self.image:
            self.push_state()
            self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
            self.display_image()

    def flip_vertical(self):
        if self.image:
            self.push_state()
            self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
            self.display_image()

    # filter functions

    def apply_grayscale(self):
        if self.image:
            self.push_state()
            self.image = self.image.convert("L").convert("RGB")
            self.display_image()

    def apply_sepia(self):
        if self.image:
            self.push_state()
            img = self.image.convert("RGB")
            width, height = img.size
            pixels = img.load()  # create the pixel map

            for py in range(height):
                for px in range(width):
                    r, g, b = pixels[px, py]

                    tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                    tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                    tb = int(0.272 * r + 0.534 * g + 0.131 * b)

                    pixels[px, py] = (min(255, tr), min(255, tg), min(255, tb))

            self.image = img
            self.display_image()

    def apply_invert(self):
        if self.image:
            self.push_state()
            if self.image.mode != 'RGB':
                self.image = self.image.convert('RGB')
            self.image = ImageOps.invert(self.image)
            self.display_image()

    def apply_blur(self):
        if self.image:
            self.push_state()
            self.image = self.image.filter(ImageFilter.GaussianBlur(10))
            self.display_image()

    # tone functions

    def prepare_for_tone_adjustment(self, event=None):
        if self.image:
            self.push_state()

    def preview_tone_adjustments(self, event=None):
        if self.image:
            brightness = float(self.brightness_slider.get())
            contrast = float(self.contrast_slider.get())

            img = ImageEnhance.Brightness(self.original_image).enhance(brightness)
            img = ImageEnhance.Contrast(img).enhance(contrast)

            self.image = img
            self.display_image()

    # extra functions

    def detect_faces(self):
        if self.image:
            img_cv = cv2.cvtColor(numpy.array(self.image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)

            for (x, y, w, h) in faces:
                cv2.rectangle(img_cv, (x, y), (x + w, y + h), (255, 0, 0), 2)

            self.push_state()
            self.image = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
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


# FACE RECOGNITION??
# DISABLE BUTTONS IF NO IMAGE??
# APPLYING FILTER AGAIN RETURNS TO ORIGINAL
# IMPROVE SIZING OF CANVAS -> DYNAMICALLY??
