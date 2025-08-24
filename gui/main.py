import tkinter as tk
from PIL import Image, ImageTk, ImageEnhance
import os

# --- Window Setup ---
root = tk.Tk()
root.title("ApexAlytics")
root.geometry("800x600")
root.configure(bg="black")
root.resizable(True, True)

canvas = tk.Canvas(root, highlightthickness=0)
canvas.pack(fill="both", expand=True)

# --- 3-Color Gradient Background Drawer ---
def draw_gradient_three_colors(canvas, width, height, top_color, middle_color, bottom_color):
    r1, g1, b1 = root.winfo_rgb(top_color)
    r2, g2, b2 = root.winfo_rgb(middle_color)
    r3, g3, b3 = root.winfo_rgb(bottom_color)

    if height == 0:
        return  # Nothing to draw

    mid = max(1, height // 2)  # Avoid zero division

    r_ratio1 = (r2 - r1) / mid
    g_ratio1 = (g2 - g1) / mid
    b_ratio1 = (b2 - b1) / mid

    r_ratio2 = (r3 - r2) / (height - mid) if (height - mid) != 0 else 0
    g_ratio2 = (g3 - g2) / (height - mid) if (height - mid) != 0 else 0
    b_ratio2 = (b3 - b2) / (height - mid) if (height - mid) != 0 else 0

    for i in range(height):
        if i < mid:
            nr = int(r1 + r_ratio1 * i) >> 8
            ng = int(g1 + g_ratio1 * i) >> 8
            nb = int(b1 + b_ratio1 * i) >> 8
        else:
            j = i - mid
            nr = int(r2 + r_ratio2 * j) >> 8
            ng = int(g2 + g_ratio2 * j) >> 8
            nb = int(b2 + b_ratio2 * j) >> 8

        hex_color = f"#{nr:02x}{ng:02x}{nb:02x}"
        canvas.create_line(0, i, width, i, fill=hex_color)

# --- Logo Load ---
script_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(script_dir, "assets", "logo1.png")

logo = None
try:
    logo_img = Image.open(logo_path).resize((120, 120))
    logo_img = ImageEnhance.Brightness(logo_img).enhance(1.2)
    logo = ImageTk.PhotoImage(logo_img)
except Exception as e:
    print("Logo load error:", e)

# --- Rounded Button Class WITHOUT BORDER ---
class RoundedButton:
    def __init__(self, canvas, x, y, width, height, radius, bg_color, fg_color, hover_color, text, command):
        self.canvas = canvas
        self.command = command
        self.radius = radius
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_color = hover_color
        self.text = text

        self.draw_button()
        self.bind_events()

    def draw_rounded_rect(self, x, y, w, h, r, color):
        """Draw filled rounded rectangle without border"""
        items = []
        # Four corner arcs (filled)
        items.append(self.canvas.create_arc(x, y, x + 2*r, y + 2*r, start=90, extent=90, fill=color, outline=color))
        items.append(self.canvas.create_arc(x + w - 2*r, y, x + w, y + 2*r, start=0, extent=90, fill=color, outline=color))
        items.append(self.canvas.create_arc(x + w - 2*r, y + h - 2*r, x + w, y + h, start=270, extent=90, fill=color, outline=color))
        items.append(self.canvas.create_arc(x, y + h - 2*r, x + 2*r, y + h, start=180, extent=90, fill=color, outline=color))
        # Rectangles and lines to fill between arcs
        items.append(self.canvas.create_rectangle(x + r, y, x + w - r, y + h, fill=color, outline=color))
        items.append(self.canvas.create_rectangle(x, y + r, x + w, y + h - r, fill=color, outline=color))
        return items

    def draw_button(self):
        x, y, w, h, r = self.x, self.y, self.width, self.height, self.radius
        self.bg_items = self.draw_rounded_rect(x, y, w, h, r, self.bg_color)
        self.text_id = self.canvas.create_text(x + w//2, y + h//2,
                                               text=self.text, fill=self.fg_color,
                                               font=("Segoe UI", 12, "bold"))

    def bind_events(self):
        # Bind events on all parts
        all_items = self.bg_items + [self.text_id]
        for item in all_items:
            self.canvas.tag_bind(item, "<Button-1>", self.on_click)
            self.canvas.tag_bind(item, "<Enter>", self.on_enter)
            self.canvas.tag_bind(item, "<Leave>", self.on_leave)

    def on_click(self, event):
        if self.command:
            self.command()

    def on_enter(self, event):
        # Change bg color to hover color and text color to black
        for item in self.bg_items:
            self.canvas.itemconfig(item, fill=self.hover_color, outline=self.hover_color)
        self.canvas.itemconfig(self.text_id, fill="black")

    def on_leave(self, event):
        # Restore original bg and text colors
        for item in self.bg_items:
            self.canvas.itemconfig(item, fill=self.bg_color, outline=self.bg_color)
        self.canvas.itemconfig(self.text_id, fill=self.fg_color)


# --- Element Placement ---
def place_elements():
    canvas.delete("all")
    draw_gradient_three_colors(canvas, canvas.winfo_width(), canvas.winfo_height(),
                               "#0f2027", "#203a43", "#2c5364")

    w = canvas.winfo_width()
    h = canvas.winfo_height()
    cx, cy = w // 2, h // 2

    # Logo
    if logo:
        canvas.create_image(cx, cy - 170, image=logo)

    # Title
    canvas.create_text(cx, cy - 60, text="ApexAlytics",
                       font=("Segoe UI", 28, "bold"), fill="#eeeeee")

    btn_width = 160
    btn_height = 45
    gap = 20
    radius = 15

    # Login button (blue background, white text, hover lighter blue)
    login_btn = RoundedButton(canvas,
                              cx - btn_width - gap//2, cy + 20,
                              btn_width, btn_height, radius,
                              bg_color="#1e90ff",      # Dodger blue
                              fg_color="white",
                              hover_color="#63b3ff",   # lighter blue on hover
                              text="Login",
                              command=lambda: print("Login Clicked"))

    # Sign up button (green background, white text, hover lighter green)
    signup_btn = RoundedButton(canvas,
                               cx + gap//2, cy + 20,
                               btn_width, btn_height, radius,
                               bg_color="#32cd32",      # Lime green
                               fg_color="white",
                               hover_color="#7ef87e",   # lighter green on hover
                               text="Sign Up",
                               command=lambda: print("Sign Up Clicked"))

    # Footer
    canvas.create_text(cx, cy + 100, text="Empowering insights, beautifully.",
                       font=("Segoe UI", 10), fill="#aaaaaa")


# --- Resize Event Binding ---
canvas.bind("<Configure>", lambda e: place_elements())

# --- Initial Render ---
place_elements()

# --- Run App ---
root.mainloop()
