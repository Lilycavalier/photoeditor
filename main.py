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

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack()

        tk.Button(btn_frame, text="Undo", command=self.undo).grid(row=1, column=4, padx=5)
        tk.Button(btn_frame, text="Redo", command=self.redo).grid(row=1, column=5, padx=5)
        tk.Button(btn_frame, text="Grayscale", command=self.apply_grayscale).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Sepia", command=self.apply_sepia).grid(row=0, column=3, padx=5)
        tk.Button(btn_frame, text="Invert", command=self.apply_invert).grid(row=0, column=4, padx=5)
        tk.Button(btn_frame, text="Blur", command=self.apply_blur).grid(row=0, column=5, padx=5)
        tk.Button(btn_frame, text="Rotate", command=lambda: self.rotate_image(90)).grid(row=1, column=1, padx=5)
        tk.Button(btn_frame, text="Save Image", command=self.save_image).grid(row=1, column=3, padx=5)
        tk.Button(root, text='Exit', command=root.destroy).place(relx=1.0, x=-10, y=10, anchor='ne')  # top-right corner with 10px padding

    def push_state(self):
        if self.image:
            self.image_stack.append(self.image.copy())
            if len(self.image_stack) > 20:  # Keep only the last 20 edits
                self.image_stack.pop(0)
            self.redo_stack.clear()

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
                canvas_width = 800
                canvas_height = 500

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
            self.redo_stack.append(self.image)
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
                canvas_width = 800
                canvas_height = 500
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
            sepia = ImageOps.colorize(self.image.convert("L"), '#704214', '#C0A080')
            self.image = sepia
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

def open_or_capture_picture():
    """Ask the user to either open an existing picture or capture a new one."""

    response = simpledialog.askstring(
        "Choose Action",
        "Would you like to open an existing picture or capture a new one with your webcam? (Enter 'open' or 'capture')"
    )

    if response and response.lower() == "open":
        # open existing image
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if path:
            messagebox.showinfo("Success", f"Picture selected: {path}")
            return path
        else:
            messagebox.showinfo("Failure", "No file selected.")
            return None
    elif response and response.lower() == "capture":
        # Step 1: Show a temporary loading window
        loading_win = tk.Toplevel()
        loading_win.title("Loading")
        loading_win.geometry("200x100")
        loading_win.resizable(False, False)
        loading_label = tk.Label(loading_win, text="Initializing webcam...", font=("Arial", 12))
        loading_label.pack(expand=True)

        loading_win.grab_set()
        loading_win.update()

        # Step 2: Initialize webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            loading_win.destroy()
            messagebox.showerror("Error", "Webcam not found.")
            return

        # Warm up webcam with a few frames
        for _ in range(5):
            ret, _ = cap.read()
            if not ret:
                cap.release()
                loading_win.destroy()
                messagebox.showerror("Error", "Could not read from webcam.")
                return

        # Step 3: Close loading window
        loading_win.destroy()

        # Step 4: Show instructions now that webcam is ready
        messagebox.showinfo("Webcam", "Press SPACE to capture, ESC to cancel.")

        # Step 5: Start OpenCV live preview
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            cv2.imshow("Press SPACE to capture", frame)
            key = cv2.waitKey(1)
            if key == 27:  # ESC
                cap.release()
                cv2.destroyAllWindows()
                return
            elif key == 32:  # SPACE
                cv2.imwrite("captured_webcam_image.jpg", frame)
                cap.release()
                cv2.destroyAllWindows()
                return "captured_webcam_image.jpg"
    else:
        messagebox.showwarning("Invalid choice", "Please enter 'open' or 'create'.")
        return None


if __name__ == "__main__":

    # Step 1: Create the root window but keep it hidden
    root = tk.Tk()
    root.withdraw()

    # Step 2: open or capture picture
    photo_path = open_or_capture_picture()
    if not photo_path:
        messagebox.showwarning("Error", "No image selected. Exiting application.")
        exit()  # don't proceed if no image

    # Step 3: Create the app instance
    app = PhotoEditor(root)

    # Step 4: Load the image
    app.image = Image.open(photo_path)
    app.push_state()
    app.display_image()

    # Step 5: Show the GUI
    root.deiconify()
    root.mainloop()


# BUTTON TO ENABLE CROPPING?
# FITTING OF IMAGE INTO CANVAS?
# ADD MENU?? NEW IMAGE??
