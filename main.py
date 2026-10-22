import sys, math, random
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import (QPainter, QColor, QRadialGradient, QBrush, QPen,
                           QFont, QLinearGradient, QPolygon, QTextOption)
from PySide6.QtCore import Qt, QPoint, QTimer, QRectF


def sf_font(size, bold=True):
    for family in ["Courier New", "Courier", "Lucida Console", "Consolas"]:
        f = QFont(family, size)
        f.setBold(bold)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        return f
    f = QFont()
    f.setFixedPitch(True)
    f.setPointSize(size)
    f.setBold(bold)
    return f


# ── Sequence builder ────────────────────────────────────────────────────
def build_command_sequence():
    core = [
        "Press",
        "Dont press",
        "press when cats are even",
        "remember this number",
        "HURRY UP! dont press",
        "dont press when u see a spider",
        "press once per corner",
        "press this times",
        "show number of cats",
        "press 0 times",
        "toss between press",
        "press the red word",
        "wait..wait..NOW",
        "press once for every vowel",
    ]
    random.shuffle(core)

    # cats even must come before show number of cats
    idx_even = core.index("press when cats are even")
    idx_show = core.index("show number of cats")
    if idx_even > idx_show:
        core.remove("press when cats are even")
        core.insert(idx_show, "press when cats are even")

    # Hit it + Double Tap at random spots
    for cmd in ["Hit it", "Double Tap"]:
        pos = random.randint(0, len(core))
        core.insert(pos, cmd)

    # taps = current score — only valid early; place at index 3-8 so score is low
    pos = random.randint(3, min(8, len(core) - 1))
    core.insert(pos, "taps = current score")

    # Same as last x2 (not first 2)
    for _ in range(2):
        pos = random.randint(2, len(core))
        core.insert(pos, "Same as last")

    # repeat the last action (not after press once per corner)
    inserted = False
    for _ in range(300):
        pos = random.randint(2, len(core))
        if core[pos - 1] not in ("press once per corner", "Same as last", "repeat the last action"):
            core.insert(pos, "repeat the last action")
            inserted = True
            break
    if not inserted:
        core.append("repeat the last action")

    # "for next 3 commands do opposite" block
    opposite_block = [
        "for next 3 commands",
        "opp_slot_1",
        "opp_slot_2",
        "opp_slot_3",
    ]
    pos = random.randint(2, max(2, len(core) - 5))
    for i, cmd in enumerate(opposite_block):
        core.insert(pos + i, cmd)

    # lie/wrong pair + outcome
    outcome = "Press" if random.random() < 0.7 else "Dont press"
    lie_block = [
        "the next statement is a lie",
        "the next command is wrong",
        outcome,
    ]
    pos = random.randint(2, max(2, len(core) - 3))
    for i, cmd in enumerate(lie_block):
        core.insert(pos + i, cmd)

    first_two = ["Press", "Dont press"]
    random.shuffle(first_two)

    sequence = first_two + core + ["press if you are straight"]
    return sequence


class IndustrialSciFiGame(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(650, 700)
        self.setWindowTitle("Industrial Sci-Fi Logic Chamber")
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_loop)
        self.update_timer.start(33)
        self.init_game()

    def init_game(self):
        self.is_pressed = False
        self.score = 0
        self.timer_val = 5.0
        self.game_active = True
        self.game_over_msg = ""

        self.blackout_active = False
        if hasattr(self, 'blackout_timer'):
            self.blackout_timer.stop()
        self.blackout_timer = QTimer(self)
        self.blackout_timer.setSingleShot(True)
        self.blackout_timer.timeout.connect(self.end_blackout)

        # prev state — updated after every command, stores both press/no-press AND tap count
        self.prev_action_required = True    # True=press, False=dont press
        self.prev_required_taps = 1         # how many taps the previous command needed

        self.current_action_required = True
        self.internal_counter = 0
        self.required_taps = 1
        self.current_shape = None

        self.no_press_streak = 0
        self.timer_speed = 1.0

        self.hold_blue_triggered = False
        self.hold_blue_success = False
        if hasattr(self, 'hold_blue_timer'):
            self.hold_blue_timer.stop()
        self.hold_blue_timer = QTimer(self)
        self.hold_blue_timer.setSingleShot(True)
        self.hold_blue_timer.timeout.connect(self.activate_blue)

        self.www_phase = 0
        self.www_press_window = False
        for attr in ('www_timer', 'www_window_timer', 'www_now_timer'):
            if hasattr(self, attr):
                getattr(self, attr).stop()
        self.www_timer = QTimer(self)
        self.www_timer.setSingleShot(True)
        self.www_timer.timeout.connect(self.www_next_phase)
        self.www_window_timer = QTimer(self)
        self.www_window_timer.setSingleShot(True)
        self.www_window_timer.timeout.connect(self.www_window_expired)

        self.btn_color_override = None

        self.hologram_lines = [random.uniform(0, 1) for _ in range(12)]
        self.fan_angle = 0
        self.fluid_pos = 0

        self.commands = build_command_sequence()
        self.command_index = 0
        self.current_display = ""
        self.update_logic_requirements()

    # ──────────────────────────────────────────────────────────
    #  COMMAND LOGIC
    # ──────────────────────────────────────────────────────────
    def update_logic_requirements(self):
        raw_cmd = self.commands[self.command_index]

        # Reset per-command state
        self.required_taps = 1
        self.current_action_required = True
        self.btn_color_override = None
        self.hold_blue_triggered = False
        self.hold_blue_success = False
        self.hold_blue_timer.stop()
        self.www_phase = 0
        self.www_press_window = False
        self.www_timer.stop()
        self.www_window_timer.stop()
        self.current_shape = None

        # ── Opposite slot commands ────────────────────────────
        if raw_cmd in ("opp_slot_1", "opp_slot_2", "opp_slot_3"):
            original_press = random.random() < 0.6
            if original_press:
                self.current_display = "PRESS"
                self.current_action_required = False
                self.required_taps = 0
            else:
                self.current_display = "DONT PRESS"
                self.current_action_required = True
                self.required_taps = 1
            return

        # ── Normal commands ───────────────────────────────────
        if raw_cmd == "Press":
            self.current_display = "PRESS"
            self.current_action_required = True

        elif raw_cmd == "Dont press":
            self.current_display = "DONT PRESS"
            self.current_action_required = False

        elif raw_cmd in ("Same as last", "repeat the last action"):
            # Always repeat whatever the previous command required — including multi-tap
            self.current_action_required = self.prev_action_required
            self.required_taps = self.prev_required_taps
            self.current_display = raw_cmd.upper()

        elif raw_cmd == "Hit it":
            self.current_display = "HIT IT"
            self.current_action_required = True

        elif raw_cmd == "Double Tap":
            self.current_display = "DOUBLE TAP"
            self.current_action_required = True
            self.required_taps = 2

        elif raw_cmd == "press when cats are even":
            self.current_display = "PRESS WHEN\nCATS ARE EVEN"
            self.current_action_required = False

        elif raw_cmd == "remember this number":
            num = random.randint(0, 10)
            self.current_display = f"REMEMBER\nTHIS NUMBER\n{num}"
            self.current_action_required = False

        elif raw_cmd == "HURRY UP! dont press":
            self.current_display = "HURRY UP!\nDONT PRESS"
            self.current_action_required = False
            self.timer_val = 3.0

        elif raw_cmd == "dont press when u see a spider":
            self.current_display = "DONT PRESS\nWHEN U SEE\nA SPIDER"
            self.current_action_required = False

        elif raw_cmd == "press once per corner":
            shape = random.choice(["circle", "square", "star", "triangle"])
            self.current_shape = shape
            self.current_display = "PRESS ONCE\nPER CORNER"
            if shape == "circle":
                self.required_taps = 0
                self.current_action_required = False
            elif shape == "square":
                self.required_taps = 4
                self.current_action_required = True
            elif shape == "triangle":
                self.required_taps = 3
                self.current_action_required = True
            elif shape == "star":
                self.required_taps = 10
                self.current_action_required = True

        elif raw_cmd == "for next 3 commands":
            self.current_display = "FOR NEXT\n3 COMMANDS\nDO OPPOSITE"
            self.current_action_required = False

        elif raw_cmd == "press this times":
            a = random.randint(1, 5)
            b = random.randint(1, 5)
            self.required_taps = a + b
            self.current_action_required = True
            self.current_display = f"PRESS THIS\nMANY TIMES\n{a} + {b} = ?"

        elif raw_cmd == "taps = current score":
            # Use actual current score as tap count (no cap, no number shown in display)
            taps = max(1, self.score)
            self.required_taps = taps
            self.current_action_required = True
            self.current_display = "TAPS =\nCURRENT SCORE"

        elif raw_cmd == "hold until blue":
            self.current_display = "HOLD UNTIL\nBLUE"
            self.current_action_required = True
            self.hold_blue_timer.start(random.randint(1500, 3000))

        elif raw_cmd == "show number of cats":
            cats = random.randint(1, 9)
            self.current_action_required = (cats % 2 == 0)
            self.current_display = f"CATS: {cats}"

        elif raw_cmd == "press 0 times":
            self.current_display = "PRESS\n0 TIMES"
            self.current_action_required = False

        elif raw_cmd == "the next statement is a lie":
            self.current_display = "THE NEXT\nSTATEMENT\nIS A LIE"
            self.current_action_required = False

        elif raw_cmd == "the next command is wrong":
            self.current_display = "THE NEXT\nCOMMAND\nIS WRONG"
            self.current_action_required = False

        elif raw_cmd == "toss between press":
            chosen = random.choice([True, False])
            self.current_display = "PRESS" if chosen else "DONT PRESS"
            self.current_action_required = chosen

        elif raw_cmd == "press the red word":
            self.current_display = "__RED_WORD__"
            self.current_action_required = False

        elif raw_cmd == "wait..wait..NOW":
            self.current_display = "WAIT..."
            self.current_action_required = False
            self.www_phase = 1
            self.timer_val = 7.0
            self.www_timer.start(1500)

        elif raw_cmd == "press once for every vowel":
            word = random.choice([
                "apple", "ocean", "unite", "earth", "eager",
                "brave", "crisp", "flute", "glyph", "shrug",
                "drape", "clown", "pixie", "blunt", "froze"
            ])
            vowels = sum(1 for c in word if c in "aeiou")
            self.required_taps = max(1, vowels)
            self.current_action_required = True
            self.current_display = f"PRESS PER\nVOWEL\n\"{word.upper()}\""

        elif raw_cmd == "press if you are straight":
            self.current_display = "PRESS IF YOU\nARE STRAIGHT"
            self.current_action_required = None

        # Slow timer for high tap counts
        if self.required_taps > 4:
            extra = (self.required_taps - 4) * 0.4
            self.timer_val = min(self.timer_val + extra, 8.0)

    # ──────────────────────────────────────────────────────────
    #  HOLD UNTIL BLUE
    # ──────────────────────────────────────────────────────────
    def activate_blue(self):
        if not self.game_active:
            return
        self.hold_blue_triggered = True
        self.btn_color_override = QColor(0, 120, 255)
        self.update()

    # ──────────────────────────────────────────────────────────
    #  WAIT..WAIT..NOW
    # ──────────────────────────────────────────────────────────
    def www_next_phase(self):
        if not self.game_active:
            return
        if self.www_phase == 1:
            self.current_display = "WAIT...\nWAIT..."
            self.www_phase = 2
            self.www_timer.start(1500)
        elif self.www_phase == 2:
            self.current_display = "NOW!"
            self.www_phase = 3
            self.current_action_required = True
            self.www_press_window = True
            self.www_window_timer.start(3000)
        self.update()

    def www_window_expired(self):
        if not self.game_active:
            return
        if self.www_press_window:
            self.game_over()
            self.update()

    # ──────────────────────────────────────────────────────────
    #  PRESSURE TIMER DISPLAY
    # ──────────────────────────────────────────────────────────
    def get_pressure_timer_display(self):
        total = 3.0 if "HURRY UP!" in self.commands[self.command_index] else 5.0
        ratio = max(0.0, self.timer_val / total)
        return total * (ratio ** 0.45)

    # ──────────────────────────────────────────────────────────
    #  MAIN LOOP
    # ──────────────────────────────────────────────────────────
    def update_loop(self):
        if not self.game_active:
            return
        if self.blackout_active:
            return

        for i in range(len(self.hologram_lines)):
            self.hologram_lines[i] += 0.005
            if self.hologram_lines[i] > 1.0:
                self.hologram_lines[i] = 0
        self.fan_angle += 1
        self.fluid_pos += 0.01

        speed = self.timer_speed
        if self.current_action_required is False:
            speed *= 1.6
        self.timer_val -= 0.033 * speed

        if self.timer_val <= 0:
            self.check_timeout_condition()
        self.update()

    # ──────────────────────────────────────────────────────────
    #  TIMEOUT
    # ──────────────────────────────────────────────────────────
    def check_timeout_condition(self):
        raw_cmd = self.commands[self.command_index]

        if raw_cmd == "press if you are straight":
            self.game_over_msg = "KNEW IT"
            self.game_active = False
            self.update()
            return

        if raw_cmd == "wait..wait..NOW":
            if self.www_phase < 3:
                self.game_over()
            return

        if raw_cmd == "hold until blue":
            self.game_over()
            return

        if self.current_action_required is False:
            self.score += 1
            self.no_press_streak += 1
            self.timer_speed = min(2.5, 1.0 + self.no_press_streak * 0.15)
            self.advance_command()
        else:
            self.game_over()

    # ──────────────────────────────────────────────────────────
    #  INPUT
    # ──────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if not self.game_active:
            self.init_game()
            self.update()
            return

        if self.blackout_active:
            return

        self.is_pressed = True
        raw_cmd = self.commands[self.command_index]

        if raw_cmd == "press if you are straight":
            self.game_over_msg = "NO, U LIED"
            self.game_active = False
            self.update()
            return

        if raw_cmd == "hold until blue":
            if not self.hold_blue_triggered:
                self.game_over()
            self.update()
            return

        if raw_cmd == "wait..wait..NOW":
            if self.www_phase < 3:
                self.game_over()
            else:
                self.www_press_window = False
                self.www_window_timer.stop()
                self.score += 1
                self.no_press_streak = 0
                self.timer_speed = max(1.0, self.timer_speed - 0.3)
                self.advance_command()
            self.update()
            return

        if self.current_action_required is False:
            self.game_over()
            self.update()
            return

        self.internal_counter += 1
        if self.internal_counter == self.required_taps:
            self.score += 1
            self.no_press_streak = 0
            self.timer_speed = max(1.0, self.timer_speed - 0.3)
            raw_cmd = self.commands[self.command_index]
            if raw_cmd in ("press once per corner", "press once for every vowel"):
                self.current_action_required = False
            else:
                self.advance_command()
        elif self.internal_counter > self.required_taps:
            self.game_over()

        self.update()

    def mouseReleaseEvent(self, event):
        self.is_pressed = False
        if not self.game_active:
            self.update()
            return
        raw_cmd = self.commands[self.command_index]
        if raw_cmd == "hold until blue" and self.hold_blue_triggered and not self.hold_blue_success:
            self.hold_blue_success = True
            self.score += 1
            self.no_press_streak = 0
            self.timer_speed = max(1.0, self.timer_speed - 0.3)
            self.advance_command()
        self.update()

    # ──────────────────────────────────────────────────────────
    #  TRANSITIONS
    # ──────────────────────────────────────────────────────────
    def advance_command(self):
        """Save prev state (always), then trigger blackout → next_command."""
        # Always save previous action and tap count so "Same as last" / "repeat" works correctly
        # for ALL command types, including multi-tap
        self.prev_action_required = self.current_action_required
        self.prev_required_taps = self.required_taps

        self.blackout_active = True
        self.blackout_timer.start(random.randint(120, 220))
        self.update()

    def end_blackout(self):
        self.blackout_active = False
        self.next_command()
        self.update()

    def next_command(self):
        self.command_index = (self.command_index + 1) % len(self.commands)
        self.internal_counter = 0
        raw_cmd = self.commands[self.command_index]
        self.timer_val = 3.0 if "HURRY UP!" in raw_cmd else 5.0
        self.update_logic_requirements()

    def game_over(self):
        self.game_over_msg = "GAME OVER"
        self.game_active = False

    # ──────────────────────────────────────────────────────────
    #  DRAW SHAPE
    # ──────────────────────────────────────────────────────────
    def draw_shape_on_button(self, painter, cx, btn_y, radius):
        shape = self.current_shape
        if not shape:
            return
        sx, sy = cx, btn_y + 38
        size = 48
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255, 230), 3))
        painter.setBrush(QColor(255, 255, 255, 30))

        if shape == "circle":
            painter.drawEllipse(int(sx - size), int(sy - size), size * 2, size * 2)
        elif shape == "square":
            painter.drawRect(int(sx - size), int(sy - size), size * 2, size * 2)
        elif shape == "triangle":
            pts = QPolygon([QPoint(int(sx), int(sy - size)),
                            QPoint(int(sx + size), int(sy + size)),
                            QPoint(int(sx - size), int(sy + size))])
            painter.drawPolygon(pts)
        elif shape == "star":
            outer, inner = size, size * 0.42
            pts = []
            for i in range(10):
                angle = math.radians(-90 + i * 36)
                r = outer if i % 2 == 0 else inner
                pts.append(QPoint(int(sx + r * math.cos(angle)), int(sy + r * math.sin(angle))))
            painter.drawPolygon(QPolygon(pts))

    # ──────────────────────────────────────────────────────────
    #  UI RENDERING
    # ──────────────────────────────────────────────────────────
    def draw_industrial_bolt(self, painter, x, y):
        painter.setPen(QPen(QColor(20, 20, 20), 1))
        painter.setBrush(QColor(60, 62, 65))
        painter.drawEllipse(x - 9, y - 9, 18, 18)
        bolt_top = QRadialGradient(x, y, 6)
        bolt_top.setColorAt(0, QColor(100, 102, 105))
        bolt_top.setColorAt(1, QColor(70, 72, 75))
        painter.setBrush(QBrush(bolt_top))
        painter.drawEllipse(x - 6, y - 6, 12, 12)
        painter.setPen(QPen(QColor(30, 30, 30), 2))
        painter.drawLine(x - 4, y - 4, x + 4, y + 4)

    def draw_complex_hex_bg(self, painter, rect):
        painter.setOpacity(0.15)
        painter.setPen(QPen(QColor(10, 10, 10), 1))
        for _ in range(10):
            x = rect.left() + random.uniform(0, 600)
            y = rect.top() + random.uniform(0, 650)
            pts = [QPoint(int(x + 25 * math.cos(math.radians(j * 60 + 30))),
                          int(y + 25 * math.sin(math.radians(j * 60 + 30)))) for j in range(6)]
            painter.drawPolygon(QPolygon(pts))
        painter.setOpacity(1.0)

    def draw_flow_pipes(self, painter, x, y, h=100):
        painter.setPen(QPen(QColor(10, 10, 10), 2))
        painter.setBrush(QColor(40, 42, 45))
        painter.drawRect(x, y, 15, h)
        fy = y + h - (h * self.fluid_pos)
        painter.setPen(QPen(QColor(100, 220, 220, 150), 4))
        painter.drawLine(x + 7, int(fy), x + 7, int(max(y, fy - 30)))

    def draw_gears_and_fans(self, painter, x, y):
        painter.setOpacity(0.7)
        painter.setBrush(QColor(30, 32, 34))
        painter.drawEllipse(x - 40, y - 40, 80, 80)
        for i in range(6):
            ang = math.radians(self.fan_angle + i * 60)
            painter.setPen(QPen(QColor(60, 62, 65), 5))
            painter.drawLine(int(x + 10 * math.cos(ang)), int(y + 10 * math.sin(ang)),
                             int(x + 35 * math.cos(ang)), int(y + 35 * math.sin(ang)))
        painter.setOpacity(1.0)

    def draw_hologram_data(self, painter, x, y, w, h):
        painter.setBrush(QColor(0, 50, 0, 30))
        painter.drawRect(x, y, w, h)
        painter.setPen(QPen(QColor(150, 255, 150, 150), 2))
        for line_y in self.hologram_lines:
            painter.drawLine(x + 5, int(y + 5 + (h - 10) * line_y),
                             x + w - 5, int(y + 5 + (h - 10) * line_y))

    def draw_circuit_trace(self, painter, x, y):
        painter.setPen(QPen(QColor(80, 200, 200, 120), 2))
        painter.drawLine(x, y, x + 50, y)
        painter.drawLine(x + 50, y, x + 70, y - 20)
        self.draw_industrial_bolt(painter, x, y)

    def draw_sf_vent(self, painter, x, y, count=3):
        painter.setBrush(QColor(30, 32, 34))
        for i in range(count):
            painter.drawRect(x, y + i * 15, 60, 10)

    def draw_dying_cells_timer(self, painter):
        total = 3.0 if "HURRY UP!" in self.commands[self.command_index] else 5.0
        ratio = max(0.0, self.timer_val / total)
        pressure_val = self.get_pressure_timer_display()

        batt_w = 320
        batt_h = 44
        batt_x = (self.width() - batt_w) // 2
        batt_y = self.height() - 70
        nub_w = 10
        nub_h = 22

        border_color = QColor(220, 220, 220) if ratio > 0.3 else QColor(255, 60, 60)
        painter.setPen(QPen(border_color, 2.5))
        painter.setBrush(QColor(18, 18, 18))
        painter.drawRoundedRect(batt_x, batt_y, batt_w, batt_h, 6, 6)
        painter.setPen(Qt.NoPen)
        painter.setBrush(border_color)
        painter.drawRoundedRect(batt_x + batt_w, batt_y + (batt_h - nub_h) // 2,
                                nub_w, nub_h, 3, 3)

        num_blocks = 12
        padding = 5
        gap = 4
        block_w = (batt_w - 2 * padding - gap * (num_blocks - 1)) // num_blocks
        block_h = batt_h - 2 * padding
        blocks_alive = round(ratio * num_blocks)

        for i in range(num_blocks):
            bx = batt_x + padding + i * (block_w + gap)
            by = batt_y + padding
            if i < blocks_alive:
                if ratio > 0.6:
                    color = QColor(50, 230, 80)
                elif ratio > 0.3:
                    t = (ratio - 0.3) / 0.3
                    color = QColor(230, int(60 + 170 * t), 15)
                else:
                    color = (QColor(255, 25, 25) if int(self.timer_val * 30) % 3 != 0
                             else QColor(120, 8, 8))
                grad = QLinearGradient(bx, by, bx, by + block_h)
                grad.setColorAt(0, color.lighter(140))
                grad.setColorAt(1, color.darker(160))
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(int(bx), int(by), int(block_w), int(block_h), 3, 3)
            else:
                painter.setBrush(QColor(12, 12, 12))
                painter.setPen(QPen(QColor(45, 45, 45), 1))
                painter.drawRoundedRect(int(bx), int(by), int(block_w), int(block_h), 3, 3)

        num_color = (QColor(80, 240, 110) if ratio > 0.6
                     else QColor(240, 190, 30) if ratio > 0.3
                     else QColor(255, 55, 55))
        painter.setPen(num_color)
        painter.setFont(sf_font(11))
        painter.drawText(batt_x + batt_w - 46, batt_y + batt_h + 16,
                         f"{max(0.0, pressure_val):.1f}s")

    # ──────────────────────────────────────────────────────────
    #  PAINT EVENT
    # ──────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.blackout_active:
            painter.fillRect(self.rect(), QColor(0, 0, 0))
            return

        # Background
        painter.fillRect(self.rect(), QColor(35, 37, 39))
        self.draw_complex_hex_bg(painter, self.rect())

        # Top panel
        top_panel = QLinearGradient(0, 0, 0, 190)
        top_panel.setColorAt(0, QColor(45, 47, 49))
        top_panel.setColorAt(1, QColor(30, 32, 34))
        painter.fillRect(0, 0, 650, 190, top_panel)
        painter.setPen(QPen(QColor(15, 15, 15), 3))
        painter.drawLine(0, 190, 650, 190)

        # Bolts
        self.draw_industrial_bolt(painter, 25, 25)
        self.draw_industrial_bolt(painter, 625, 25)
        self.draw_industrial_bolt(painter, 25, 170)
        self.draw_industrial_bolt(painter, 625, 170)

        # Ambient decoration
        self.draw_flow_pipes(painter, 140, 300, h=150)
        self.draw_gears_and_fans(painter, 80, 270)
        self.draw_hologram_data(painter, 100, 60, 140, 80)
        self.draw_circuit_trace(painter, 500, 320)
        self.draw_sf_vent(painter, 540, 590, count=6)

        cx, cy = self.width() // 2, self.height() // 2 + 70
        radius = 190

        # Button glow
        if not self.is_pressed and self.game_active:
            glow = QRadialGradient(cx, cy, radius + 70)
            glow.setColorAt(0.5, QColor(255, 80, 0, 130))
            glow.setColorAt(1.0, QColor(255, 0, 0, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(cx - (radius + 70), cy - (radius + 70),
                                (radius + 70) * 2, (radius + 70) * 2)

        # Button shadow
        painter.setBrush(QColor(10, 10, 10))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - radius - 7, cy - radius - 7,
                            (radius + 7) * 2, (radius + 7) * 2)

        # Button body
        btn_y = cy + (10 if self.is_pressed else 0)
        lens = QRadialGradient(cx, btn_y, radius)
        base_color = QColor(255, 40, 40) if not self.btn_color_override else self.btn_color_override
        lens.setColorAt(0, base_color)
        lens.setColorAt(1, QColor(60, 0, 0))
        painter.setBrush(QBrush(lens))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - radius, btn_y - radius, radius * 2, radius * 2)

        # Specular highlight
        if not self.is_pressed:
            spec = QRadialGradient(cx - 55, btn_y - 65, 55)
            spec.setColorAt(0, QColor(255, 255, 255, 180))
            spec.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(spec))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(cx - 110, btn_y - 120, 110, 110)

        # Shape overlay
        if self.current_shape and self.game_active:
            self.draw_shape_on_button(painter, cx, btn_y, radius)

        # ── Button text ──────────────────────────────────────
        raw_cmd = self.commands[self.command_index] if self.game_active else ""
        pad = 40
        text_box = QRectF(cx - radius + pad, btn_y - radius + pad,
                          (radius - pad) * 2, (radius - pad) * 2)

        if not self.game_active:
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(sf_font(26))
            opt = QTextOption(Qt.AlignCenter)
            opt.setWrapMode(QTextOption.WordWrap)
            painter.drawText(text_box, self.game_over_msg, opt)
            painter.setPen(QColor(200, 200, 200, 150))
            painter.setFont(sf_font(10, bold=False))
            painter.drawText(text_box.adjusted(0, text_box.height() * 0.5, 0, 0),
                             "TAP TO RESTART", QTextOption(Qt.AlignCenter))

        elif raw_cmd == "press the red word":
            h3 = text_box.height() / 3
            painter.setFont(sf_font(17))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(QRectF(text_box.x(), text_box.y(),
                                    text_box.width(), h3),
                             "PRESS THE", QTextOption(Qt.AlignCenter))
            painter.setPen(QColor(30, 100, 255))
            painter.setFont(sf_font(30))
            painter.drawText(QRectF(text_box.x(), text_box.y() + h3,
                                    text_box.width(), h3),
                             "RED", QTextOption(Qt.AlignCenter))
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(sf_font(17))
            painter.drawText(QRectF(text_box.x(), text_box.y() + h3 * 2,
                                    text_box.width(), h3),
                             "WORD", QTextOption(Qt.AlignCenter))

        elif self.current_shape:
            top_box = QRectF(text_box.x(), text_box.y(),
                             text_box.width(), text_box.height() * 0.42)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(sf_font(16))
            opt = QTextOption(Qt.AlignCenter)
            opt.setWrapMode(QTextOption.WordWrap)
            painter.drawText(top_box, "PRESS ONCE\nPER CORNER", opt)

        else:
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(sf_font(21))
            opt = QTextOption(Qt.AlignCenter)
            opt.setWrapMode(QTextOption.WordWrap)
            painter.drawText(text_box, self.current_display, opt)

        # Score
        painter.setPen(QColor(150, 255, 150))
        painter.setFont(sf_font(18))
        painter.drawText(50, 60, f"SCORE: {self.score}")

        # Timer bar
        if self.game_active:
            self.draw_dying_cells_timer(painter)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IndustrialSciFiGame()
    window.show()
    sys.exit(app.exec())