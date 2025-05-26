import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageOps
import cv2
import os


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

        # Load last session image
        if os.path.exists("last_session_image.jpg"):
            self.image = Image.open("last_session_image.jpg")
            self.push_state()
            self.display_image()

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack()

        tk.Button(btn_frame, text="Grayscale", command=self.apply_grayscale).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Sepia", command=self.apply_sepia).grid(row=0, column=3, padx=5)
        tk.Button(btn_frame, text="Invert", command=self.apply_invert).grid(row=0, column=4, padx=5)
        tk.Button(btn_frame, text="Blur", command=self.apply_blur).grid(row=0, column=5, padx=5)
        tk.Button(btn_frame, text="Rotate", command=lambda: self.rotate_image(90)).grid(row=0, column=1, padx=5)

    def push_state(self):
        if self.image:
            self.image_stack.append(self.image.copy())
            if len(self.image_stack) > 20:  # Keep only the last 20 edits
                self.image_stack.pop(0)
            self.redo_stack.clear()

    def show_about(self):
        messagebox.showinfo("About", "Simple Photo Editor\nCreated with Tkinter and Pillow.")

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if path:
            self.image = Image.open(path)
            self.push_state()
            self.display_image()

    def capture_photo(self):
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

    def undo(self):
        if self.image_stack:
            self.redo_stack.append(self.image.copy())
            self.image = self.image_stack.pop()
            self.display_image()

    def redo(self):
        if self.redo_stack:
            self.image_stack.append(self.image.copy())  # Manual push to undo stack
            self.image = self.redo_stack.pop()
            self.display_image()
        else:
            print("Nothing to redo.")

    def on_mouse_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red')

    def on_mouse_drag(self, event):
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_release(self, event):
        if self.image and self.rect_id:
            bbox = self.canvas.bbox(self.rect_id)
            self.canvas.delete(self.rect_id)
            self.rect_id = None

            if bbox and bbox[2] - bbox[0] > 10 and bbox[3] - bbox[1] > 10:
                img_width, img_height = self.image.size
                canvas_width = 600
                canvas_height = 400
                scale_x = img_width / canvas_width
                scale_y = img_height / canvas_height

                left = int(bbox[0] * scale_x)
                upper = int(bbox[1] * scale_y)
                right = int(bbox[2] * scale_x)
                lower = int(bbox[3] * scale_y)

                self.push_state()
                self.image = self.image.crop((left, upper, right, lower))
                self.display_image()

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
            self.image = ImageOps.invert(self.image)
            self.display_image()

    def apply_blur(self):
        if self.image:
            self.push_state()
            self.image = self.image.filter(ImageFilter.GaussianBlur(2))
            self.display_image()

    def rotate_image(self, angle):
        if self.image:
            self.push_state()  # Add this line
            self.image = self.image.rotate(angle, expand=True)
            self.display_image()

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
# DIFFERENT MENUS BASED ON COMBOBOX SELECTION??
# DISABLE BUTTONS IF NO IMAGE??
# BUTTON TO ENABLE CROPPING?
# IMPROVE SIZING OF CANVAS -> DYNAMICALLY??
