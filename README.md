# Python Photo Editor

A desktop photo editor built with **Python**, **Tkinter**, **Pillow**, and **OpenCV**.  
This application allows users to upload images or capture photos using a webcam, then edit them with a variety of tools such as cropping, rotating, filters, tone adjustments, drawing, and text overlays.

---

## Features

### Image Input
- Open images (`.jpg`, `.png`, `.jpeg`)
- Capture photos directly from your webcam
- Automatically loads the last edited image on startup

### Transform Tools
- Crop with optional aspect ratio lock (`Free`, `1:1`, `4:3`, `16:9`)
- Rotate image (90 degrees)
- Flip horizontally or vertically
- Zoom in and out using the mouse wheel

### Filters
- Grayscale
- Sepia
- Invert colors
- Gaussian blur

### Tone Adjustments
- Brightness control
- Contrast control

### Drawing and Text
- Freehand drawing with adjustable brush size
- Add custom text with adjustable font size and custom color

### Undo, Redo, and Saving
- Full undo and redo support for edits
- Save edited images as JPG or PNG
- Automatically saves the last session image on exit

---

## Technologies Used

- Python 3
- Tkinter – GUI framework
- Pillow (PIL) – Image processing
- OpenCV – Webcam capture and face detection
- ttk – Styled Tkinter widgets

---

## Installation

### Clone the Repository
```bash
git clone https://github.com/yourusername/python-photo-editor.git
cd python-photo-editor
```

### Install Dependencies
Make sure Python 3 is installed, then run:
```bash
pip install pillow opencv-python
```

Note: Tkinter is included with most Python installations.

---

## How to Run

```bash
python photo_editor.py
```

---

## Controls and Shortcuts

| Action | Shortcut |
|------|---------|
| Open Image | Ctrl + O |
| Capture Webcam Photo | Ctrl + C |
| Save Image | Ctrl + S |
| Undo | Ctrl + Z |
| Redo | Ctrl + Y |
| Revert to Original | Ctrl + G |
| Exit | Ctrl + Q |
| About | F1 |
| Zoom | Mouse Wheel |

---

## How It Works

- Uses a non-destructive editing pipeline
- All edits are stored in a history stack
- Undo and redo operations work by reapplying actions from the original image
- Drawing and text overlays are dynamically re-rendered

---

## Project Structure

```text
photo_editor.py        # Main application
last_session_image.jpg # Auto-saved image (generated at runtime)
```

---

## Project Status

I’m still working to improve the drawing and text overlay features, as they don’t quite behave the way I want them to yet.

---

## License

This project is open-source and available under the MIT License.

---

## Acknowledgments

- Pillow and OpenCV communities
- Tkinter documentation
