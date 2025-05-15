import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageOps
import cv2
import os


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

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack()

        tk.Button(btn_frame, text="Open Image", command=self.open_image).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Capture Photo", command=self.capture_photo).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Grayscale", command=self.apply_grayscale).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Sepia", command=self.apply_sepia).grid(row=0, column=3, padx=5)
        tk.Button(btn_frame, text="Invert", command=self.apply_invert).grid(row=0, column=4, padx=5)
        tk.Button(btn_frame, text="Blur", command=self.apply_blur).grid(row=0, column=5, padx=5)
        tk.Button(btn_frame, text="Rotate Left", command=lambda: self.rotate_image(-90)).grid(row=1, column=0, padx=5, pady=10)
        tk.Button(btn_frame, text="Rotate Right", command=lambda: self.rotate_image(90)).grid(row=1, column=1, padx=5)
        # tk.Button(btn_frame, text="Crop Center", command=self.crop_image).grid(row=1, column=2, padx=5)
        tk.Button(btn_frame, text="Save Image", command=self.save_image).grid(row=1, column=3, padx=5)

    def push_state(self):
        if self.image:
            self.image_stack.append(self.image.copy())
            self.redo_stack.clear()

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if path:
            self.image = Image.open(path)
            self.push_state()
            self.display_image()

    def display_image(self):
        if self.image:
            img = self.image.copy()
            img.thumbnail((800, 500))
            self.tk_image = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas_image_id = self.canvas.create_image(400, 250, image=self.tk_image)

    def undo(self):
        if self.image_stack:
            self.redo_stack.append(self.image)
            self.image = self.image_stack.pop()
            self.display_image()

    def redo(self):
        if self.redo_stack:
            self.push_state()
            self.image = self.redo_stack.pop()
            self.display_image()

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

    def capture_photo(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Webcam not found.")
            return

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
                self.image = Image.open("captured_webcam_image.jpg")
                self.push_state()
                self.display_image()
                return

    def show_image(self):
        if self.image:
            display = self.image.copy()
            display.thumbnail((600, 400))
            self.display_image = ImageTk.PhotoImage(display)
            self.canvas.create_image(300, 200, image=self.display_image)

    def apply_grayscale(self):
        if self.image:
            self.push_state()
            self.image = self.image.convert("L").convert("RGB")
            self.display_image()

    def apply_sepia(self):
        if self.image:
            sepia = ImageOps.colorize(self.image.convert("L"), '#704214', '#C0A080')
            self.image = sepia
            self.show_image()

    def apply_invert(self):
        if self.image:
            self.push_state()
            self.image = ImageOps.invert(self.image)
            self.display_image()

    def apply_blur(self):
        if self.image:
            self.image = self.image.filter(ImageFilter.GaussianBlur(2))
            self.show_image()

    def rotate_image(self, angle):
        if self.image:
            self.image = self.image.rotate(angle, expand=True)
            self.show_image()

    def save_image(self):
        if self.image:
            save_path = filedialog.asksaveasfilename(defaultextension=".jpg",
                                                     filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
            if save_path:
                self.image.save(save_path)
                messagebox.showinfo("Saved", f"Image saved to {save_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoEditor(root)
    root.mainloop()
