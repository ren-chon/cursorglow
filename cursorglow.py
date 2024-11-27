import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, GLib, Gio, Adw
import cairo
import os
import sys
import math
from enum import Enum
import json
import time
from datetime import datetime

APP_ID = "com.renchon.cursorglow"
VERSION = "0.0.1"
GITHUB_USER = "ren-chon"
TWITTER_USER = "prod_ocean"

class DisplayProtocol(Enum):
    X11 = "x11" 
    WAYLAND = "wayland"

class HighlightShape(Enum):
    CIRCLE = "circle"
    ROUNDED_SQUARE = "rounded_square"

class CursorHighlight:
    def __init__(self):
        self.size = 50  # Size of the outer shape
        self.color = (1, 1, 1, 0.8)  # Main color it influences the inner shape's color
        self.inner_opacity = 0.5  # Inner shape opacity
        self.corner_radius = 15
        self.rotation = 0
        self.border_width = 4
        self.inner_padding = 4
        self.glow_size = 10.0  # Glow radius
        self.glow_opacity = 0.3  # Glow opacity
        self.shape = HighlightShape.ROUNDED_SQUARE  # Default shape
        self.inner_stroke_width = 2  
        self.animation_enabled = True  # New animation toggle (broken)
        self.left_press_amount = 0.0  # Animation progress for left click (broken)
        self.right_press_amount = 0.0  # Animation progress for right click (broken)
        self.animation_speed = 5.0  # Increased animation speed constant (broken)
        self.left_press_target = 0.0
        self.right_press_target = 0.0
        self.last_time = time.monotonic()  # Use monotonic time for animations
        
    def update_animations(self):
        current_time = time.monotonic() 
        delta_time = current_time - self.last_time
        self.last_time = current_time
        
        if not self.animation_enabled:
            return
        
        if self.left_press_target > self.left_press_amount:
            self.left_press_amount = min(
                self.left_press_amount + self.animation_speed * delta_time,
                self.left_press_target
            )
        else:
            self.left_press_amount = max(
                self.left_press_amount - self.animation_speed * delta_time,
                self.left_press_target
            )
            
        if self.right_press_target > self.right_press_amount:
            self.right_press_amount = min(
                self.right_press_amount + self.animation_speed * delta_time,
                self.right_press_target
            )
        else:
            self.right_press_amount = max(
                self.right_press_amount - self.animation_speed * delta_time,
                self.right_press_target
            )
    
    def draw(self, ctx, x, y):
        ctx.save()
        
        if self.animation_enabled:
            if self.shape == HighlightShape.CIRCLE:
                #  squeeze effect
                squeeze_factor = 1.0
                if self.left_press_amount > 0:
                    squeeze_factor = 1.0 - (self.left_press_amount * 0.2)
                elif self.right_press_amount > 0:
                    squeeze_factor = 1.0 - (self.right_press_amount * 0.2)
                ctx.translate(x, y)
                ctx.scale(squeeze_factor, 1.0)
                ctx.translate(-x, -y)
            else:
                # For rounded square, apply translation effect
                offset = 0
                if self.left_press_amount > 0:
                    offset = self.left_press_amount * 10
                elif self.right_press_amount > 0:
                    offset = -self.right_press_amount * 10
                ctx.translate(offset, 0)
        
        ctx.translate(x, y)
        ctx.rotate(math.radians(self.rotation))
        ctx.translate(-x, -y)
        
        #  glow
        glow_size_int = int(self.glow_size)
        for i in range(glow_size_int, 0, -2):
            opacity = self.glow_opacity * (i / self.glow_size)
            ctx.set_source_rgba(*self.color[:3], opacity)
            ctx.set_line_width(self.border_width + i*2)
            
            half_size = self.size / 2
            glow_x = x - half_size - i
            glow_y = y - half_size - i
            glow_size = self.size + i*2
            
            if self.shape == HighlightShape.CIRCLE:
                self._draw_circle(ctx, x, y, (glow_size) / 2)
            else:
                self._draw_rounded_rect(ctx, glow_x, glow_y, glow_size, glow_size, self.corner_radius + i)
            ctx.stroke()
        
        #  outer shape
        ctx.set_source_rgba(*self.color)
        ctx.set_line_width(self.border_width)
        
        half_size = self.size / 2
        outer_x = x - half_size
        outer_y = y - half_size
        
        if self.shape == HighlightShape.CIRCLE:
            self._draw_circle(ctx, x, y, half_size)
        else:
            self._draw_rounded_rect(ctx, outer_x, outer_y, self.size, self.size, self.corner_radius)
        ctx.stroke()
        
        #  inner shape
        inner_offset = self.border_width + self.inner_padding
        inner_size = self.size - (inner_offset * 2)
        inner_x = outer_x + inner_offset
        inner_y = outer_y + inner_offset
        inner_radius = max(0, self.corner_radius - inner_offset)
        
        ctx.set_source_rgba(*self.color[:3], self.inner_opacity)
        ctx.set_line_width(self.inner_stroke_width)
        if self.shape == HighlightShape.CIRCLE:
            self._draw_circle(ctx, x, y, inner_size / 2)
        else:
            self._draw_rounded_rect(ctx, inner_x, inner_y, inner_size, inner_size, inner_radius)
        ctx.stroke()
        
        ctx.restore()
    
    def _draw_rounded_rect(self, ctx, x, y, width, height, radius):
        ctx.new_sub_path()
        ctx.arc(x + width - radius, y + radius, radius, -math.pi/2, 0)
        ctx.arc(x + width - radius, y + height - radius, radius, 0, math.pi/2)
        ctx.arc(x + radius, y + height - radius, radius, math.pi/2, math.pi)
        ctx.arc(x + radius, y + radius, radius, math.pi, 3*math.pi/2)
        ctx.close_path()
    
    def _draw_circle(self, ctx, x, y, radius):
        ctx.new_sub_path()
        ctx.arc(x, y, radius, 0, 2 * math.pi)
        ctx.close_path()

class CursorProWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        
        self.set_title("CursorGlow")
        self.set_default_size(1280, 720)
        
        menu_model = Gio.Menu.new()
        menu_model.append("Preferences", "app.preferences")
        menu_model.append("About", "app.about")
        menu_model.append("Quit", "app.quit")
        
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(menu_model)
        
        header_bar = Gtk.HeaderBar()
        header_bar.pack_end(menu_button)
        self.set_titlebar(header_bar)
        
        # display protocol
        self.protocol = (DisplayProtocol.WAYLAND 
                        if os.environ.get('WAYLAND_DISPLAY') 
                        else DisplayProtocol.X11)
        
        # overlay
        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)
        
        self.toast_overlay = Adw.ToastOverlay()
        self.overlay.add_overlay(self.toast_overlay)
        
        welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        welcome_box.set_valign(Gtk.Align.CENTER)
        welcome_box.set_halign(Gtk.Align.CENTER)
        
        welcome_label = Gtk.Label()
        welcome_label.set_markup("<span size='x-large'>Welcome to CursorGlow!</span>")
        welcome_box.append(welcome_label)
        
        hint_label = Gtk.Label(label="Press Ctrl+P to open settings")
        welcome_box.append(hint_label)
        
        self.overlay.add_overlay(welcome_box)
        
        # can't draw outside window
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_draw_func(self.draw)
        self.overlay.add_overlay(self.drawing_area)
        
        self.cursor_x = 0
        self.cursor_y = 0
        self.highlight = CursorHighlight()
        
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("motion", self.on_motion)
        self.add_controller(motion_controller)
        
        GLib.timeout_add(16, self.update_animations)  # ~60 FPS
        
        click_controller = Gtk.GestureClick()
        click_controller.connect("pressed", self.on_button_pressed)
        click_controller.connect("released", self.on_button_released)
        self.add_controller(click_controller)
        
        # keyboard shortcut (preview on the side ctrl+p)
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)
        
        self.last_time = time.monotonic()
        
        self.load_settings()
        
    def load_settings(self):
        try:
            config_dir = GLib.get_user_config_dir()
            app_config_dir = os.path.join(config_dir, "cursorglow")
            os.makedirs(app_config_dir, exist_ok=True)
            settings_path = os.path.join(app_config_dir, "settings.json")
            
            with open(settings_path, "r") as f:
                settings = json.load(f)
                
                # Load shape first since other settings may depend on it
                shape_str = settings.get("shape", HighlightShape.ROUNDED_SQUARE.value)
                self.highlight.shape = HighlightShape(shape_str)
                
                self.highlight.size = settings.get("size", 50)
                self.highlight.color = tuple(settings.get("color", [1, 1, 1, 0.8]))
                self.highlight.corner_radius = settings.get("corner_radius", 15)
                self.highlight.rotation = settings.get("rotation", 0)
                self.highlight.border_width = settings.get("border_width", 4)
                self.highlight.inner_stroke_width = settings.get("inner_stroke_width", 2)
                self.highlight.animation_enabled = settings.get("animation_enabled", True)
                self.highlight.animation_speed = settings.get("animation_speed", 5.0)
                self.highlight.inner_opacity = settings.get("inner_opacity", 0.5)
                self.highlight.glow_size = settings.get("glow_size", 10.0)
                self.highlight.glow_opacity = settings.get("glow_opacity", 0.3)
                
        except FileNotFoundError:
            pass
            
    def save_settings(self):
        config_dir = GLib.get_user_config_dir()
        app_config_dir = os.path.join(config_dir, "cursorglow")
        os.makedirs(app_config_dir, exist_ok=True)
        settings_path = os.path.join(app_config_dir, "settings.json")
        
        settings = {
            "size": self.highlight.size,
            "color": list(self.highlight.color),
            "corner_radius": self.highlight.corner_radius,
            "rotation": self.highlight.rotation,
            "shape": self.highlight.shape.value,
            "border_width": self.highlight.border_width,
            "inner_stroke_width": self.highlight.inner_stroke_width,
            "animation_enabled": self.highlight.animation_enabled,
            "animation_speed": self.highlight.animation_speed,
            "inner_opacity": self.highlight.inner_opacity,
            "glow_size": self.highlight.glow_size,
            "glow_opacity": self.highlight.glow_opacity
        }
        
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
            
        # TODO: fix spam
        toast = Adw.Toast.new("Settings saved")
        toast.set_timeout(1)
        self.toast_overlay.add_toast(toast)
            
    def on_motion(self, controller, x, y):
        self.cursor_x = x
        self.cursor_y = y
        self.drawing_area.queue_draw()
        
    def update_animations(self):
        current_time = time.monotonic()
        self.highlight.update_animations()
        self.drawing_area.queue_draw()
        return True
        
    def draw(self, area, ctx, width, height):
        # Clear the surface
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.set_operator(cairo.OPERATOR_OVER)
        
        # Draw highlight
        self.highlight.draw(ctx, self.cursor_x, self.cursor_y)
    
    def on_button_pressed(self, gesture, n_press, x, y):
        button = gesture.get_current_button()
        if button == 1:  # Left click
            self.highlight.left_press_target = 1.0
        elif button == 3:  # Right click
            self.highlight.right_press_target = 1.0
    
    def on_button_released(self, gesture, n_press, x, y):
        button = gesture.get_current_button()
        if button == 1:  # Left click
            self.highlight.left_press_target = 0.0
        elif button == 3:  # Right click
            self.highlight.right_press_target = 0.0
            
    def on_key_pressed(self, controller, keyval, keycode, state):
        #  ctrl+P to open preferences
        if state & Gdk.ModifierType.CONTROL_MASK and keyval == Gdk.KEY_p:
            self.get_application().activate_action("preferences", None)
            return True
        return False

class PreferencesDialog(Adw.PreferencesWindow):
    def __init__(self, parent):
        super().__init__(title="Preferences", transient_for=parent)
        
        page = Adw.PreferencesPage()
        self.add(page)
        
        #  appearance group
        appearance_group = Adw.PreferencesGroup(title="Appearance")
        page.add(appearance_group)
        
        size_row = Adw.ActionRow(title="Size")
        size_adj = Gtk.Adjustment(value=parent.highlight.size, lower=10, upper=100, step_increment=1)
        size_scale = Gtk.Scale(adjustment=size_adj, orientation=Gtk.Orientation.HORIZONTAL)
        size_scale.set_hexpand(True)
        size_scale.set_draw_value(True)  # Show the current value
        size_scale.set_value_pos(Gtk.PositionType.RIGHT)  # Position value on right
        size_scale.connect("value-changed", self.on_size_changed, parent)
        size_row.add_suffix(size_scale)
        appearance_group.add(size_row)
        
        radius_row = Adw.ActionRow(title="Corner Radius")
        radius_adj = Gtk.Adjustment(value=parent.highlight.corner_radius, lower=0, upper=50, step_increment=1)
        radius_scale = Gtk.Scale(adjustment=radius_adj, orientation=Gtk.Orientation.HORIZONTAL)
        radius_scale.set_hexpand(True)
        radius_scale.set_draw_value(True)  # Show the current value
        radius_scale.set_value_pos(Gtk.PositionType.RIGHT)  # Position value on right
        radius_scale.connect("value-changed", self.on_radius_changed, parent)
        radius_row.add_suffix(radius_scale)
        appearance_group.add(radius_row)
        
        rotation_row = Adw.ActionRow(title="Rotation")
        rotation_adj = Gtk.Adjustment(value=parent.highlight.rotation, lower=0, upper=360, step_increment=1)
        rotation_scale = Gtk.Scale(adjustment=rotation_adj, orientation=Gtk.Orientation.HORIZONTAL)
        rotation_scale.set_hexpand(True)
        rotation_scale.set_draw_value(True)  # Show the current value
        rotation_scale.set_value_pos(Gtk.PositionType.RIGHT)  # Position value on right
        rotation_scale.connect("value-changed", self.on_rotation_changed, parent)
        rotation_row.add_suffix(rotation_scale)
        appearance_group.add(rotation_row)
        
        color_row = Adw.ActionRow(title="Color")
        color_button = Gtk.ColorButton()
        color = Gdk.RGBA()
        color.red = parent.highlight.color[0]
        color.green = parent.highlight.color[1]
        color.blue = parent.highlight.color[2]
        color.alpha = parent.highlight.color[3]
        color_button.set_rgba(color)
        color_button.connect("color-set", self.on_color_changed, parent)
        color_row.add_suffix(color_button)
        appearance_group.add(color_row)
        
        inner_opacity_row = Adw.ActionRow(title="Inner Shape Opacity")
        inner_opacity_adj = Gtk.Adjustment(
            value=parent.highlight.inner_opacity, 
            lower=0.1, 
            upper=1.0, 
            step_increment=0.1
        )
        inner_opacity_scale = Gtk.Scale(
            adjustment=inner_opacity_adj, 
            orientation=Gtk.Orientation.HORIZONTAL
        )
        inner_opacity_scale.set_hexpand(True)
        inner_opacity_scale.set_draw_value(True)
        inner_opacity_scale.set_value_pos(Gtk.PositionType.RIGHT)
        inner_opacity_scale.connect("value-changed", self.on_inner_opacity_changed, parent)
        inner_opacity_row.add_suffix(inner_opacity_scale)
        appearance_group.add(inner_opacity_row)
        
        glow_size_row = Adw.ActionRow(title="Glow Size")
        glow_size_adj = Gtk.Adjustment(
            value=parent.highlight.glow_size, 
            lower=0, 
            upper=30, 
            step_increment=1
        )
        glow_size_scale = Gtk.Scale(
            adjustment=glow_size_adj, 
            orientation=Gtk.Orientation.HORIZONTAL
        )
        glow_size_scale.set_hexpand(True)
        glow_size_scale.set_draw_value(True)
        glow_size_scale.set_value_pos(Gtk.PositionType.RIGHT)
        glow_size_scale.connect("value-changed", self.on_glow_size_changed, parent)
        glow_size_row.add_suffix(glow_size_scale)
        appearance_group.add(glow_size_row)
        
        shape_row = Adw.ActionRow(title="Shape")
        shape_dropdown = Gtk.DropDown.new_from_strings(["Rounded Square", "Circle"])
        shape_dropdown.set_selected(0 if parent.highlight.shape == HighlightShape.ROUNDED_SQUARE else 1)
        shape_dropdown.connect("notify::selected", self.on_shape_changed, parent)
        shape_row.add_suffix(shape_dropdown)
        appearance_group.add(shape_row)
        
        outer_stroke_row = Adw.ActionRow(title="Outer Stroke Width")
        outer_stroke_adj = Gtk.Adjustment(
            value=parent.highlight.border_width,
            lower=1,
            upper=20,
            step_increment=1
        )
        outer_stroke_scale = Gtk.Scale(
            adjustment=outer_stroke_adj,
            orientation=Gtk.Orientation.HORIZONTAL
        )
        outer_stroke_scale.set_hexpand(True)
        outer_stroke_scale.set_draw_value(True)
        outer_stroke_scale.set_value_pos(Gtk.PositionType.RIGHT)
        outer_stroke_scale.connect("value-changed", self.on_outer_stroke_changed, parent)
        outer_stroke_row.add_suffix(outer_stroke_scale)
        appearance_group.add(outer_stroke_row)
        
        inner_stroke_row = Adw.ActionRow(title="Inner Stroke Width")
        inner_stroke_adj = Gtk.Adjustment(
            value=parent.highlight.inner_stroke_width,
            lower=0,
            upper=20,
            step_increment=1
        )
        inner_stroke_scale = Gtk.Scale(
            adjustment=inner_stroke_adj,
            orientation=Gtk.Orientation.HORIZONTAL
        )
        inner_stroke_scale.set_hexpand(True)
        inner_stroke_scale.set_draw_value(True)
        inner_stroke_scale.set_value_pos(Gtk.PositionType.RIGHT)
        inner_stroke_scale.connect("value-changed", self.on_inner_stroke_changed, parent)
        inner_stroke_row.add_suffix(inner_stroke_scale)
        appearance_group.add(inner_stroke_row)
        
        # Make corner radius row sensitive only for rounded square
        self.radius_row = radius_row  # Store reference to update sensitivity
        self.update_radius_sensitivity(parent.highlight.shape)
        
        animation_row = Adw.ActionRow(title="Bend Animation")
        animation_switch = Gtk.Switch()
        animation_switch.set_active(parent.highlight.animation_enabled)
        animation_switch.connect("notify::active", self.on_animation_toggled, parent)
        animation_row.add_suffix(animation_switch)
        appearance_group.add(animation_row)
        
        speed_row = Adw.ActionRow(title="Animation Speed")
        speed_adj = Gtk.Adjustment(
            value=parent.highlight.animation_speed,
            lower=0.05,
            upper=0.5,
            step_increment=0.05
        )
        speed_scale = Gtk.Scale(
            adjustment=speed_adj,
            orientation=Gtk.Orientation.HORIZONTAL
        )
        speed_scale.set_hexpand(True)
        speed_scale.set_draw_value(True)
        speed_scale.set_value_pos(Gtk.PositionType.RIGHT)
        speed_scale.connect("value-changed", self.on_speed_changed, parent)
        speed_row.add_suffix(speed_scale)
        appearance_group.add(speed_row)
    
    def on_size_changed(self, scale, parent):
        parent.highlight.size = scale.get_value()
        parent.save_settings()
        
    def on_radius_changed(self, scale, parent):
        parent.highlight.corner_radius = scale.get_value()
        parent.save_settings()
        
    def on_rotation_changed(self, scale, parent):
        parent.highlight.rotation = scale.get_value()
        parent.save_settings()
        
    def on_color_changed(self, button, parent):
        color = button.get_rgba()
        parent.highlight.color = (color.red, color.green, color.blue, color.alpha)
        parent.save_settings()
        
    def on_inner_opacity_changed(self, scale, parent):
        parent.highlight.inner_opacity = scale.get_value()
        parent.save_settings()
        
    def on_glow_size_changed(self, scale, parent):
        parent.highlight.glow_size = scale.get_value()
        parent.save_settings()
    
    def on_shape_changed(self, dropdown, param, parent):
        selected = dropdown.get_selected()
        parent.highlight.shape = HighlightShape.ROUNDED_SQUARE if selected == 0 else HighlightShape.CIRCLE
        self.update_radius_sensitivity(parent.highlight.shape)
        parent.save_settings()
    
    def update_radius_sensitivity(self, shape):
        self.radius_row.set_sensitive(shape == HighlightShape.ROUNDED_SQUARE)
    
    def on_outer_stroke_changed(self, scale, parent):
        parent.highlight.border_width = scale.get_value()
        parent.save_settings()
    
    def on_inner_stroke_changed(self, scale, parent):
        parent.highlight.inner_stroke_width = scale.get_value()
        parent.save_settings()
    
    def on_animation_toggled(self, switch, param, parent):
        parent.highlight.animation_enabled = switch.get_active()
        parent.save_settings()
    
    def on_speed_changed(self, scale, parent):
        parent.highlight.animation_speed = scale.get_value()
        parent.save_settings()

class CursorProApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        
    def do_activate(self):
        win = CursorProWindow(self)
        win.present()
        
    def do_startup(self):
        Gtk.Application.do_startup(self)
        
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit)
        self.add_action(quit_action)
        
        pref_action = Gio.SimpleAction.new("preferences", None)
        pref_action.connect("activate", self.on_preferences)
        self.add_action(pref_action)
        
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)
        
        # Add keyboard shortcuts
        self.set_accels_for_action("app.preferences", ["<Control>p"])
        self.set_accels_for_action("app.quit", ["<Control>q"])
        
    def on_quit(self, action, param):
        self.quit()
        
    def on_preferences(self, action, param):
        win = self.get_active_window()
        dialog = PreferencesDialog(win)
        dialog.present()
        
    def on_about(self, action, param):
        win = self.get_active_window()
        about = Adw.AboutWindow(
            transient_for=win,
            application_name=APP_ID.split('.')[-1].capitalize(),
            application_icon="applications-graphics",
            developer_name=f"{GITHUB_USER}",
            version=VERSION,
            copyright=f"© {datetime.now().year}",
            website=f"https://github.com/{GITHUB_USER}/{APP_ID.split('.')[-1]}",
            issue_url=f"https://github.com/{GITHUB_USER}/{APP_ID.split('.')[-1]}/issues",
            developers=[
                f"GitHub: https://github.com/{GITHUB_USER}",
                f"Twitter: https://twitter.com/{TWITTER_USER}"
            ],
            license_type=Gtk.License.GPL_3_0)
        about.present()

if __name__ == "__main__":
    app = CursorProApp()
    app.run(sys.argv)
