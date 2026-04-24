import pygame
import sys
import math
from collections import deque

pygame.init()

# ── constants ─────────────────────────────────────────────────────────────────
CELL        = 100
GRID        = 6
GRID_PX     = CELL * GRID
PAD         = 50
SIDE_W      = 260
WIN_W       = PAD + GRID_PX + PAD + SIDE_W + PAD
WIN_H       = PAD + GRID_PX + PAD
FPS         = 60

BG          = (13,  13,  18)
GRID_BG     = (22,  22,  30)
CELL_CLR    = (30,  30,  40)
CELL_BORDER = (40,  40,  55)
WHITE       = (255, 255, 255)
MUTED       = (90,  90, 110)
ACCENT      = (220,  60,  50)
ACCENT2     = (255, 200,  60)
GREEN       = ( 46, 204, 113)
BLUE        = ( 52, 152, 219)
PANEL_BG    = (18,  18,  25)
PANEL_BORDER= (40,  40,  55)

CAR_COLORS = {
    'R': (220,  55,  50),
    'A': ( 52, 152, 219),
    'B': (230, 126,  34),
    'C': ( 39, 174,  96),
    'D': (155,  89, 182),
    'E': ( 26, 188, 156),
    'F': (241, 196,  15),
    'G': (233,  30, 142),
    'H': ( 41, 128, 185),
    'I': (142, 236,  93),
    'J': (231,  76,  60),
    'K': ( 52,  73,  94),
}

# ── random puzzle generator ───────────────────────────────────────────────────
import random
CAR_IDS = ['A','B','C','D','E','F','G','H','I','J','K']

def cells_of(row, col, length, horiz):
    if horiz:
        return [(row, col + i) for i in range(length)]
    else:
        return [(row + i, col) for i in range(length)]

def place_vehicle(grid, row, col, length, horiz, vid):
    cells = cells_of(row, col, length, horiz)
    for r, c in cells:
        if not (0 <= r < 6 and 0 <= c < 6): return False
        if grid[r][c] is not None: return False
    for r, c in cells:
        grid[r][c] = vid
    return True

def generate_puzzle(num_vehicles=9, puzzle_num=1):
    MAX_TRIES = 300
    for _ in range(MAX_TRIES):
        grid = [[None]*6 for _ in range(6)]
        cars = []
        red_col = random.randint(0, 2)
        red_row = 2
        for c in range(red_col, red_col + 2):
            grid[red_row][c] = "R"
        cars.append({"id":"R","row":red_row,"col":red_col,"length":2,"horiz":True})

        blocker_cols = list(range(red_col + 2, 6))
        random.shuffle(blocker_cols)
        blocker_count = random.randint(2, min(3, len(blocker_cols)))
        used_ids = 0
        ids = ['A','B','C','D','E','F','G','H','I','J','K']

        for bc in blocker_cols[:blocker_count]:
            length = random.choice([2, 3])
            possible_rows = []
            for start_row in range(0, 6 - length + 1):
                ok = all(grid[start_row+i][bc] is None for i in range(length))
                if ok and start_row <= 2 <= start_row + length - 1:
                    possible_rows.append(start_row)
            if possible_rows:
                row = random.choice(possible_rows)
                vid = ids[used_ids]; used_ids += 1
                for i in range(length): grid[row+i][bc] = vid
                cars.append({"id":vid,"row":row,"col":bc,"length":length,"horiz":False})

        attempts = 0
        while len(cars) < num_vehicles and attempts < 500:
            attempts += 1
            if used_ids >= len(ids): break
            vid = ids[used_ids]; used_ids += 1
            horiz  = random.choice([True, False])
            length = random.choice([2, 2, 3])
            if horiz:
                row = random.randint(0, 5)
                col = random.randint(0, 6 - length)
                if row == 2: continue
                if all(grid[row][col+i] is None for i in range(length)):
                    for i in range(length): grid[row][col+i] = vid
                    cars.append({"id":vid,"row":row,"col":col,"length":length,"horiz":True})
            else:
                row = random.randint(0, 6 - length)
                col = random.randint(0, 5)
                if all(grid[row+i][col] is None for i in range(length)):
                    for i in range(length): grid[row+i][col] = vid
                    cars.append({"id":vid,"row":row,"col":col,"length":length,"horiz":False})

        blockers = sum(1 for c in range(red_col+2, 6) if grid[2][c] is not None)
        if blockers < 2 or len(cars) < 7: continue

        return {"name": f"Puzzle #{puzzle_num}", "cars": cars}

    return {
        "name": f"Puzzle #{puzzle_num} — Classic",
        "cars": [
            {"id":"R","row":2,"col":1,"length":2,"horiz":True},
            {"id":"A","row":0,"col":0,"length":2,"horiz":False},
            {"id":"B","row":0,"col":3,"length":3,"horiz":False},
            {"id":"C","row":1,"col":1,"length":2,"horiz":True},
            {"id":"D","row":3,"col":3,"length":2,"horiz":True},
            {"id":"E","row":4,"col":0,"length":3,"horiz":True},
            {"id":"F","row":5,"col":3,"length":2,"horiz":True},
        ]
    }

# ── BFS SOLVER ────────────────────────────────────────────────────────────────
def state_from_cars(cars):
    return tuple(sorted((c["id"], c["row"], c["col"]) for c in cars))

def get_all_moves(cars):
    grid = [[None]*6 for _ in range(6)]
    for car in cars:
        for i in range(car["length"]):
            r = car["row"] + (0 if car["horiz"] else i)
            c = car["col"] + (i if car["horiz"] else 0)
            grid[r][c] = car["id"]

    moves = []
    for car in cars:
        cid, row, col, length, horiz = car["id"], car["row"], car["col"], car["length"], car["horiz"]
        if horiz:
            if col > 0 and grid[row][col-1] is None:
                new = [dict(c) for c in cars]
                next(nc for nc in new if nc["id"]==cid)["col"] -= 1
                moves.append((cid, "left", new))
            if col + length < 6 and grid[row][col+length] is None:
                new = [dict(c) for c in cars]
                next(nc for nc in new if nc["id"]==cid)["col"] += 1
                moves.append((cid, "right", new))
        else:
            if row > 0 and grid[row-1][col] is None:
                new = [dict(c) for c in cars]
                next(nc for nc in new if nc["id"]==cid)["row"] -= 1
                moves.append((cid, "up", new))
            if row + length < 6 and grid[row+length][col] is None:
                new = [dict(c) for c in cars]
                next(nc for nc in new if nc["id"]==cid)["row"] += 1
                moves.append((cid, "down", new))
    return moves

def is_solved(cars):
    for car in cars:
        if car["id"] == "R":
            return car["col"] + car["length"] == 6
    return False

def bfs_solve(initial_cars):
    initial_state = state_from_cars(initial_cars)
    queue         = deque([(initial_state, initial_cars)])
    visited       = {initial_state: None}
    parent_move   = {initial_state: None}
    states_explored = 0

    while queue:
        state, cars = queue.popleft()
        states_explored += 1

        if is_solved(cars):
            path = []
            cur = state
            while parent_move[cur] is not None:
                path.append(parent_move[cur])
                cur = visited[cur]
            path.reverse()
            return path, states_explored

        for cid, direction, new_cars in get_all_moves(cars):
            new_state = state_from_cars(new_cars)
            if new_state not in visited:
                visited[new_state]     = state
                parent_move[new_state] = (cid, direction)
                queue.append((new_state, new_cars))

    return None, states_explored

# ── fonts ──────────────────────────────────────────────────────────────────────
pygame.font.init()
FONT_BIG  = pygame.font.SysFont("Arial", 36, bold=True)
FONT_MED  = pygame.font.SysFont("Arial", 22, bold=True)
FONT_SM   = pygame.font.SysFont("Arial", 16)
FONT_TINY = pygame.font.SysFont("Arial", 13)

# ── helpers ───────────────────────────────────────────────────────────────────
def lighten(color, amt=60):
    return tuple(min(255, c + amt) for c in color)

def draw_rounded_rect(surf, color, rect, radius=12, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)

def grid_to_px(row, col):
    return PAD + col * CELL, PAD + row * CELL

# ── Car ───────────────────────────────────────────────────────────────────────
class Car:
    def __init__(self, data):
        self.id     = data["id"]
        self.row    = data["row"]
        self.col    = data["col"]
        self.length = data["length"]
        self.horiz  = data["horiz"]
        self.color  = CAR_COLORS.get(self.id, (100,100,100))
        self.px     = float(PAD + self.col * CELL)
        self.py     = float(PAD + self.row * CELL)
        self.target_px = self.px
        self.target_py = self.py

    def update(self):
        self.px += (self.target_px - self.px) * 0.25 * 4
        self.py += (self.target_py - self.py) * 0.25 * 4
        if abs(self.px - self.target_px) < 0.5: self.px = self.target_px
        if abs(self.py - self.target_py) < 0.5: self.py = self.target_py

    def sync_target(self):
        self.target_px = PAD + self.col * CELL
        self.target_py = PAD + self.row * CELL

    @property
    def rect_px(self):
        GAP = 6
        w = (self.length * CELL - GAP) if self.horiz else (CELL - GAP)
        h = (CELL - GAP) if self.horiz else (self.length * CELL - GAP)
        return pygame.Rect(int(self.px)+GAP//2, int(self.py)+GAP//2, w, h)

# ── Game ──────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.puzzle_idx     = 1
        self.cars           = []
        self.selected       = None
        self.moves          = 0
        self.won            = False
        self.win_alpha      = 0
        self.current_puzzle = None
        self.ai_mode        = False
        self.ai_steps       = []
        self.ai_step_idx    = 0
        self.ai_timer       = 0
        self.ai_delay       = 38
        self.ai_states      = 0
        self.ai_no_solution = False
        self.new_puzzle()

    def new_puzzle(self):
        data = generate_puzzle(num_vehicles=random.randint(7,10),
                               puzzle_num=self.puzzle_idx)
        self.current_puzzle = data
        self._load_cars(data["cars"])
        self.ai_mode = False; self.ai_steps = []; self.ai_step_idx = 0
        self.ai_timer = 0;    self.ai_states = 0;  self.ai_no_solution = False

    def _load_cars(self, car_data):
        self.cars = [Car(dict(c)) for c in car_data]
        self.selected = None; self.moves = 0; self.won = False; self.win_alpha = 0

    def next_puzzle(self): self.puzzle_idx += 1; self.new_puzzle()

    def reset(self):
        self._load_cars(self.current_puzzle["cars"])
        self.ai_mode = False; self.ai_steps = []; self.ai_step_idx = 0
        self.ai_timer = 0;    self.ai_states = 0;  self.ai_no_solution = False

    def grid_map(self):
        g = [[None]*6 for _ in range(6)]
        for car in self.cars:
            for i in range(car.length):
                r = car.row + (0 if car.horiz else i)
                c = car.col + (i if car.horiz else 0)
                if 0 <= r < 6 and 0 <= c < 6: g[r][c] = car.id
        return g

    def can_move(self, car, direction):
        g = self.grid_map()
        if car.horiz:
            if direction == "left":  return car.col > 0 and g[car.row][car.col-1] is None
            if direction == "right": return car.col+car.length < 6 and g[car.row][car.col+car.length] is None
        else:
            if direction == "up":   return car.row > 0 and g[car.row-1][car.col] is None
            if direction == "down": return car.row+car.length < 6 and g[car.row+car.length][car.col] is None
        return False

    def move(self, car, direction):
        if not self.can_move(car, direction): return False
        if direction == "left":  car.col -= 1
        if direction == "right": car.col += 1
        if direction == "up":    car.row -= 1
        if direction == "down":  car.row += 1
        car.sync_target(); self.moves += 1; self.check_win(); return True

    def check_win(self):
        red = next((c for c in self.cars if c.id == "R"), None)
        if red and red.col + red.length == 6: self.won = True

    def car_from_pixel(self, mx, my):
        for car in self.cars:
            if car.rect_px.collidepoint(mx, my): return car
        return None

    def start_ai(self):
        self.ai_no_solution = False
        car_dicts = [{"id":c.id,"row":c.row,"col":c.col,"length":c.length,"horiz":c.horiz}
                     for c in self.cars]
        steps, states = bfs_solve(car_dicts)
        self.ai_states = states
        if steps is None:
            self.ai_no_solution = True; return
        self.ai_steps = steps; self.ai_step_idx = 0
        self.ai_timer = 0;     self.ai_mode = True; self.selected = None

    def update_ai(self):
        if not self.ai_mode or self.won: return
        self.ai_timer += 1
        if self.ai_timer >= self.ai_delay:
            self.ai_timer = 0
            if self.ai_step_idx < len(self.ai_steps):
                cid, direction = self.ai_steps[self.ai_step_idx]
                car = next((c for c in self.cars if c.id == cid), None)
                if car: self.move(car, direction)
                self.ai_step_idx += 1
            else:
                self.ai_mode = False

# ── drawing ───────────────────────────────────────────────────────────────────
def draw_arrow(surf, x, y, direction, color, size=18, hover=False):
    s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
    pts = {
        "left":  [(size*2-4,4),(size*2-4,size*2-4),(4,size)],
        "right": [(4,4),(4,size*2-4),(size*2-4,size)],
        "up":    [(4,size*2-4),(size*2-4,size*2-4),(size,4)],
        "down":  [(4,4),(size*2-4,4),(size,size*2-4)],
    }
    pygame.draw.polygon(s, (*color[:3], 220 if hover else 150), pts[direction])
    surf.blit(s, (x-size, y-size))

def draw_car(surf, car, selected, hover, tick, ai_highlight=False):
    r = car.rect_px; base = car.color; is_target = car.id == "R"
    if selected or is_target:
        g = pygame.Surface((r.width+20,r.height+20), pygame.SRCALPHA)
        pygame.draw.rect(g, (*base,60), (0,0,r.width+20,r.height+20), border_radius=14)
        surf.blit(g, (r.x-10, r.y-10))
    if is_target:
        pulse = abs(math.sin(tick*0.04))*15
        g2 = pygame.Surface((r.width+int(pulse)*2,r.height+int(pulse)*2), pygame.SRCALPHA)
        pygame.draw.rect(g2, (*base,25), (0,0,r.width+int(pulse)*2,r.height+int(pulse)*2), border_radius=14)
        surf.blit(g2, (r.x-int(pulse), r.y-int(pulse)))
    sh = pygame.Surface((r.width,r.height), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0,0,0,60), (3,4,r.width,r.height), border_radius=12)
    surf.blit(sh, (r.x+2, r.y+4))
    bc = lighten(base, 50 if selected else (30 if ai_highlight else (10 if hover else 0)))
    draw_rounded_rect(surf, bc, r, radius=12)
    shine = pygame.Surface((r.width, r.height//2), pygame.SRCALPHA)
    pygame.draw.rect(shine, (255,255,255,28), (0,0,r.width,r.height//2), border_radius=12)
    surf.blit(shine, (r.x, r.y))
    pygame.draw.rect(surf, WHITE if selected else lighten(base,50), r, 2 if selected else 1, border_radius=12)
    label = "→" if is_target else car.id
    txt = FONT_MED.render(label, True, WHITE)
    tr  = txt.get_rect(center=r.center)
    surf.blit(FONT_MED.render(label, True, (0,0,0)), (tr.x+1, tr.y+1))
    surf.blit(txt, tr)

def draw_grid(surf, game):
    draw_rounded_rect(surf, GRID_BG,
                      pygame.Rect(PAD,PAD,GRID_PX,GRID_PX).inflate(8,8),
                      radius=14, border=1, border_color=(50,50,65))
    for r in range(GRID):
        for c in range(GRID):
            x, y = grid_to_px(r, c)
            draw_rounded_rect(surf, CELL_CLR, pygame.Rect(x+3,y+3,CELL-6,CELL-6),
                              radius=8, border=1, border_color=CELL_BORDER)
    red     = next((c for c in game.cars if c.id=="R"), None)
    red_row = red.row if red else 2
    ex = PAD + GRID_PX + 8
    ey = PAD + red_row * CELL + CELL//2
    pulse = (220,60,50,int(150+80*abs(math.sin(pygame.time.get_ticks()*0.003))))
    asurf = pygame.Surface((44,32), pygame.SRCALPHA)
    pygame.draw.polygon(asurf, pulse, [(0,7),(26,7),(26,0),(43,16),(26,32),(26,25),(0,25)])
    surf.blit(asurf, (ex, ey-16))

def draw_panel(surf, game, tick):
    px = PAD + GRID_PX + PAD; pw = SIDE_W; ph = GRID_PX
    draw_rounded_rect(surf, PANEL_BG, pygame.Rect(px,PAD,pw,ph),
                      radius=14, border=1, border_color=PANEL_BORDER)
    y = PAD + 20
    t = FONT_BIG.render("RUSH HOUR", True, ACCENT)
    surf.blit(t, (px+(pw-t.get_width())//2, y)); y += 44
    pygame.draw.line(surf,(50,50,65),(px+16,y),(px+pw-16,y),1); y += 14

    pname = game.current_puzzle["name"] if game.current_puzzle else ""
    t = FONT_TINY.render(pname.upper(), True, MUTED)
    surf.blit(t, (px+(pw-t.get_width())//2, y)); y += 22

    t = FONT_TINY.render("MOVES", True, MUTED)
    surf.blit(t, (px+(pw-t.get_width())//2, y)); y += 18
    t = FONT_BIG.render(str(game.moves), True, ACCENT2)
    surf.blit(t, (px+(pw-t.get_width())//2, y)); y += 42

    # BFS stats
    if game.ai_states > 0:
        pygame.draw.line(surf,(50,50,65),(px+16,y),(px+pw-16,y),1); y += 10
        t = FONT_TINY.render("─── BFS RESULTS ───", True, BLUE)
        surf.blit(t, (px+(pw-t.get_width())//2, y)); y += 18
        t = FONT_TINY.render(f"States explored: {game.ai_states}", True, MUTED)
        surf.blit(t, (px+(pw-t.get_width())//2, y)); y += 16
        t = FONT_TINY.render(f"Optimal moves: {len(game.ai_steps)}", True, MUTED)
        surf.blit(t, (px+(pw-t.get_width())//2, y)); y += 16
        if game.ai_mode:
            prog = f"Playing: {game.ai_step_idx} / {len(game.ai_steps)}"
            t = FONT_TINY.render(prog, True, GREEN)
            surf.blit(t, (px+(pw-t.get_width())//2, y)); y += 16
        y += 4
    else:
        y += 10

    pygame.draw.line(surf,(50,50,65),(px+16,y),(px+pw-16,y),1); y += 10

    lines = [("HOW TO PLAY", MUTED),("Click car + Arrow keys",WHITE),
             ("SPACE = AI Solve",ACCENT2),("",""),("GOAL",MUTED),("Red car → exit!",ACCENT)]
    for text, color in lines:
        if not text: y += 4; continue
        f = FONT_TINY if color == MUTED else FONT_SM
        t = f.render(text, True, color)
        surf.blit(t, (px+(pw-t.get_width())//2, y)); y += 20

    pygame.draw.line(surf,(50,50,65),(px+16,y),(px+pw-16,y),1); y += 12

    mx, my = pygame.mouse.get_pos()
    bw, bh = pw-32, 38; bx = px+16
    buttons = {}

    def btn(label, idle, active):
        nonlocal y
        rect = pygame.Rect(bx, y, bw, bh)
        bg = active if rect.collidepoint(mx,my) else idle
        draw_rounded_rect(surf, bg, rect, radius=8, border=1, border_color=(80,80,100))
        t = FONT_SM.render(label, True, WHITE)
        surf.blit(t, (bx+(bw-t.get_width())//2, y+(bh-t.get_height())//2))
        y += bh+8
        return rect

    buttons["reset"] = btn("↺  Reset",          (40,40,55), (70,70,95))
    buttons["next"]  = btn("Next Puzzle →",      (40,40,55), (70,70,95))

    if game.ai_mode:
        ai_lbl = f"⏸ AI Playing... {game.ai_step_idx}/{len(game.ai_steps)}"
        buttons["ai"] = btn(ai_lbl, (20,100,60), (30,140,80))
    elif game.ai_no_solution:
        buttons["ai"] = btn("✗ No Solution", (100,30,30), (130,40,40))
    else:
        buttons["ai"] = btn("🤖 AI Solve (BFS)", (30,80,150), (50,110,190))

    return buttons

def draw_move_arrows(surf, game, tick):
    car = game.selected
    if not car or game.ai_mode: return {}
    r = car.rect_px; mx,my = pygame.mouse.get_pos()
    dirs = ["left","right"] if car.horiz else ["up","down"]
    arrow_rects = {}
    for d in dirs:
        if not game.can_move(car, d): continue
        if d=="left":   ax,ay = r.left-28, r.centery
        elif d=="right": ax,ay = r.right+10, r.centery
        elif d=="up":    ax,ay = r.centerx, r.top-28
        else:            ax,ay = r.centerx, r.bottom+10
        draw_arrow(surf, ax, ay, d, ACCENT2, size=16, hover=math.hypot(mx-ax,my-ay)<22)
        arrow_rects[d] = (ax, ay)
    return arrow_rects

def draw_win_overlay(surf, game):
    if not game.won: return
    game.win_alpha = min(game.win_alpha+6, 220)
    ov = pygame.Surface((WIN_W,WIN_H), pygame.SRCALPHA)
    ov.fill((0,0,0,game.win_alpha)); surf.blit(ov,(0,0))
    cx,cy = WIN_W//2, WIN_H//2
    box = pygame.Rect(cx-190,cy-130,380,270)
    draw_rounded_rect(surf,(20,20,28),box,radius=18,border=2,border_color=GREEN)
    t = FONT_BIG.render("SOLVED!", True, GREEN)
    surf.blit(t,(cx-t.get_width()//2, cy-100))
    t2 = FONT_SM.render(f"Completed in {game.moves} moves", True, MUTED)
    surf.blit(t2,(cx-t2.get_width()//2, cy-54))
    if game.ai_states > 0:
        t3 = FONT_TINY.render(f"BFS: {game.ai_states} states explored  |  optimal: {len(game.ai_steps)} moves", True, BLUE)
        surf.blit(t3,(cx-t3.get_width()//2, cy-26))
    btn = pygame.Rect(cx-100,cy+30,200,44)
    mx,my = pygame.mouse.get_pos(); hover = btn.collidepoint(mx,my)
    draw_rounded_rect(surf, GREEN if hover else (40,140,80), btn, radius=10)
    t4 = FONT_SM.render("Next Puzzle →", True, (0,0,0) if hover else WHITE)
    surf.blit(t4,(cx-t4.get_width()//2, cy+30+(44-t4.get_height())//2))
    return btn

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Rush Hour — BFS AI Solver")
    clock = pygame.time.Clock()
    game  = Game(); tick = 0; arrow_rects = {}; buttons = {}

    while True:
        tick += 1; mx,my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game.won:
                    if pygame.Rect(WIN_W//2-100,WIN_H//2+30,200,44).collidepoint(mx,my):
                        game.next_puzzle()
                    continue
                if buttons.get("reset") and buttons["reset"].collidepoint(mx,my): game.reset(); continue
                if buttons.get("next")  and buttons["next"].collidepoint(mx,my):  game.next_puzzle(); continue
                if buttons.get("ai")    and buttons["ai"].collidepoint(mx,my):
                    if not game.ai_mode and not game.won: game.start_ai()
                    continue
                if not game.ai_mode:
                    clicked_arrow = False
                    for d,(ax,ay) in arrow_rects.items():
                        if math.hypot(mx-ax,my-ay)<22 and game.selected:
                            game.move(game.selected,d); clicked_arrow=True; break
                    if clicked_arrow: continue
                    clicked = game.car_from_pixel(mx,my)
                    if clicked: game.selected = clicked if game.selected!=clicked else None
                    elif PAD<=mx<=PAD+GRID_PX and PAD<=my<=PAD+GRID_PX: game.selected=None

            if event.type == pygame.KEYDOWN and not game.ai_mode and not game.won:
                km = {pygame.K_LEFT:"left",pygame.K_RIGHT:"right",
                      pygame.K_UP:"up",pygame.K_DOWN:"down",
                      pygame.K_a:"left",pygame.K_d:"right",pygame.K_w:"up",pygame.K_s:"down"}
                if event.key in km and game.selected: game.move(game.selected,km[event.key])
                if event.key==pygame.K_ESCAPE: game.selected=None
                if event.key==pygame.K_r: game.reset()
                if event.key==pygame.K_n: game.next_puzzle()
                if event.key==pygame.K_SPACE: game.start_ai()

        game.update_ai()
        for car in game.cars: car.update()

        screen.fill(BG)
        for i in range(0,WIN_W,40): pygame.draw.line(screen,(20,20,28),(i,0),(i,WIN_H))
        for j in range(0,WIN_H,40): pygame.draw.line(screen,(20,20,28),(0,j),(WIN_W,j))

        draw_grid(screen, game)

        ai_next = game.ai_steps[game.ai_step_idx][0] if (game.ai_mode and game.ai_step_idx<len(game.ai_steps)) else None
        hover_car = game.car_from_pixel(mx,my)
        for car in game.cars:
            draw_car(screen, car,
                     selected=(game.selected==car) or (game.ai_mode and car.id==ai_next),
                     hover=hover_car==car and not game.ai_mode,
                     tick=tick,
                     ai_highlight=game.ai_mode and car.id==ai_next)

        arrow_rects = draw_move_arrows(screen, game, tick)
        buttons     = draw_panel(screen, game, tick)
        if game.won: draw_win_overlay(screen, game)

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()