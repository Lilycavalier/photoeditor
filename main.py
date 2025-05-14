from PIL import Image
from PIL import ImageFilter
from urllib.request import urlopen


def change_type(oldImage):
    while True:
        try:
            change = input("Do you want to change the file type?").upper()
            # Save the image in a different format
            if change == "YES":
                newName = input("type in the new name of the image and the new type(eg. filename.type)")
            # only works if file type in name is spelled correct!!
            elif change == "NO":
                newName = input("Please type in the name you want the image to be saved as")
            oldImage.save(newName)
            print("your edited picture has been saved!")
            break
        except:
            print("invalid input. make sure you used a supported file type")
            continue


def rotate(oldImage):
    while True:
        try:
            deg = int(input("How many degrees do you want to rotate (counter-clockwise)?"))
            rotated = oldImage.rotate(deg)
            rotated.show()
            return rotated
        except:
            print("invalid input. please type in an integer")
            continue


def resize(oldImage):
    while True:
        try:
            width = int(input("What width should your image have?"))
            heigth = int(input("What heigth should your image have?"))
            resized = oldImage.resize((width, heigth))
            resized.show()
            return resized
        except:
            print("invalid input. please type in an integer")
            continue


def change_color(oldImage):
    while True:
        try:
            x1 = int(input("Type in the value of the red band for the color you want to change"))
            y1 = int(input("Type in the value of the green band for the color you want to change"))
            z1 = int(input("Type in the value of the blue band for the color you want to change"))
            x2 = int(input("Type in the value of the red band for the color you want to change it to"))
            y2 = int(input("Type in the value of the green band for the color you want to change it to"))
            z2 = int(input("Type in the value of the blue band for the color you want to change it to"))
            pixels = oldImage.load()  # create the pixel map
            for i in range(oldImage.size[0]):  # for every pixel:
                for j in range(oldImage.size[1]):
                    if pixels[i, j] == (x1, y1, z1):
                        # change to black if not red
                        pixels[i, j] = (x2, y2, z2)
            changed = oldImage
            changed.show()
            return changed
        except:
            print("error. please make sure you typed in everything correctly")
            continue


def apply_filter(oldImage):
    while True:
        try:
            filter = input("What filter do you want to apply? (detail, sharpen, blur, contour or smooth)")
            if filter == "detail":
                filtered = oldImage.filter(ImageFilter.DETAIL)
            elif filter == "sharpen":
                filtered = oldImage.filter(ImageFilter.SHARPEN)
            elif filter == "blur":
                filtered = oldImage.filter(ImageFilter.BLUR)
            elif filter == "smooth":
                filtered = oldImage.filter(ImageFilter.SMOOTH)
            elif filter == "contour":
                filtered = oldImage.filter(ImageFilter.CONTOUR)
            filtered.show()
            return filtered
        except:
            print("invalid input. make sure your spelling is correct")
            continue


kind = input("Do you have your picture saved locally or from the internet?")
if kind == "locally":
    name = input("type in the name of your file (eg. filename.type")
    im = Image.open(name)
elif kind == "internet":
    url = input("copy the url of your selected picture here:")
    im = Image.open(urlopen(url))
else:
    print("invalid input")
print("this is the file type and the size of your selected image")
print(im.format, im.size)

while True:
    inp = input("If you want to edit your image type 'edit', if you want to save your file type 'save'")
    if inp == 'edit':
        edit = input("Do you want to 'rotate', 'resize', 'apply filter' or 'change color'?")
        if edit == "resize":
            im = resize(im)
            continue
        if edit == "rotate":
            im = rotate(im)
            continue
        if edit == "apply filter":
            im = apply_filter(im)
            continue
        if edit == "change color":
            im = change_color(im)
            continue
    elif inp == 'save':
        change_type(im)
        break
im.show()