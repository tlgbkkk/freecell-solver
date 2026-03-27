import pygame
import os
import threading
import random
from pysol_cards.deal_game import Game
from logic import (SUITS_MAP, INV_SUITS, foundation_suits, get_color,
                   get_max_movable_cards, is_valid_sequence, decode_state)
from bfs import run_bfs

# config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PICS_DIR = os.path.join(BASE_DIR, "pics")
WIDTH, HEIGHT = 1100, 800
FPS = 60
BG_COLOR = (20, 100, 20)

pygame.init()
pygame.font.init()
font = pygame.font.SysFont('Arial', 20, bold=True)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("FreeCell Solver")
clock = pygame.time.Clock()

# load resources
card_images = {}
required_images = ["bottom0.gif", "bottom1.gif", "bottom2.gif", "bottom3.gif", "shade.gif"]
for s in ['c', 'd', 'h', 's']:
    for r in range(1, 14): required_images.append(f"{r:02d}{s}.gif")

for img_name in required_images:
    path = os.path.join(PICS_DIR, img_name)
    if os.path.exists(path):
        card_images[img_name] = pygame.image.load(path).convert_alpha()
    else:
        placeholder = pygame.Surface((72, 96))
        placeholder.fill((200, 0, 0))
        card_images[img_name] = placeholder


def make_card(rank, suit):
    filename = f"{rank:02d}{suit}.gif"
    return {'img': card_images[filename], 'rank': rank, 'suit': suit, 'color': get_color(suit)}


# init game
def init_random_pysol_game():
    game_num = random.randint(1, 1000000)
    game = Game(game_id="freecell", game_num=game_num, which_deals="ms")

    game.deal()
    game.freecell()

    # 0:Club, 1:Diamond, 2:Heart, 3:Spade
    suit_map = {0: 'c', 1: 'd', 2: 'h', 3: 's'}

    tableaus = [[] for _ in range(8)]
    free_cells = [None] * 4
    foundations = [[] for _ in range(4)]

    for i, col in enumerate(game.board.columns.cols):
        for card in col:
            # 1 (A) -> 13 (K)
            tableaus[i].append(make_card(card.rank, suit_map[card.suit]))

    solver_ctx = {
        'is_solving': False,
        'status': f"Ready (Seed: {game_num})",
        'path': []
    }

    return tableaus, free_cells, foundations, solver_ctx

tableaus, free_cells, foundations, solver_ctx = init_random_pysol_game()


# UI update
def update_board_from_state(b_state):
    global tableaus, free_cells, foundations
    tabs, fcs, founds = decode_state(b_state)

    foundations = [[] for _ in range(4)]
    for i, suit in enumerate(foundation_suits):
        for rank in range(1, founds[i] + 1):
            foundations[i].append(make_card(rank, suit))

    free_cells = [make_card(c[0], c[1]) if c else None for c in fcs]

    tableaus = []
    for col in tabs:
        tableaus.append([make_card(r, s) for r, s in col])
    while len(tableaus) < 8: tableaus.append([])


def get_layout_positions(tabs, fcs, founds):
    positions = {}
    for i, count in enumerate(founds):
        for rank in range(1, count + 1):
            positions[(rank, foundation_suits[i])] = (570 + i * 130, 40)
    for i, card in enumerate(fcs):
        if card: positions[(card[0], card[1])] = (50 + i * 130, 40)
    for col_idx, col in enumerate(tabs):
        for row_idx, card in enumerate(col):
            positions[(card[0], card[1])] = (50 + col_idx * 130, 200 + row_idx * 35)
    return positions


animating = False
anim_card_key, anim_start_pos, anim_end_pos = None, (0, 0), (0, 0)
anim_start_time = 0
ANIM_DURATION = 500

dragging_cards = []
drag_offset_x = drag_offset_y = 0
source_type = source_index = None

buttons = {"BFS": pygame.Rect(50, 720, 100, 40), "DFS": pygame.Rect(170, 720, 100, 40),
           "UCS": pygame.Rect(290, 720, 100, 40), "A*": pygame.Rect(410, 720, 100, 40)}


def validate_drop(cards, dest_type, dest_idx):
    if not cards: return False
    first_card = cards[0]
    if dest_type == 'foundation':
        if len(cards) > 1: return False
        return first_card['suit'] == foundation_suits[dest_idx] and first_card['rank'] == len(foundations[dest_idx]) + 1
    elif dest_type == 'freecell':
        return len(cards) == 1 and free_cells[dest_idx] is None
    elif dest_type == 'tableau':
        col = tableaus[dest_idx]
        empty_fc, empty_cols = free_cells.count(None), sum(1 for c in tableaus if not c)
        if not col: return len(cards) <= get_max_movable_cards(empty_fc, empty_cols, True)
        if len(cards) > get_max_movable_cards(empty_fc, empty_cols, False): return False
        return first_card['color'] != col[-1]['color'] and first_card['rank'] == col[-1]['rank'] - 1


def execute_move(cards, dest_type, dest_idx):
    if dest_type == 'foundation':
        foundations[dest_idx].append(cards[0])
    elif dest_type == 'freecell':
        free_cells[dest_idx] = cards[0]
    elif dest_type == 'tableau':
        tableaus[dest_idx].extend(cards)


# game loop
running = True
while running:
    current_time = pygame.time.get_ticks()
    mouse_x, mouse_y = pygame.mouse.get_pos()

    if animating and current_time - anim_start_time >= ANIM_DURATION:
        animating, anim_card_key = False, None

    # auto play
    if solver_ctx['path'] and not animating:
        next_state = solver_ctx['path'].pop(0)

        current_tabs = tuple(tuple((c['rank'], c['suit']) for c in col) for col in tableaus)
        current_fcs = tuple((c['rank'], c['suit']) if c else None for c in free_cells)
        current_founds = tuple(len(f) for f in foundations)

        pos_old = get_layout_positions(current_tabs, current_fcs, current_founds)
        next_tabs, next_fcs, next_founds = decode_state(next_state)
        pos_new = get_layout_positions(next_tabs, next_fcs, next_founds)

        moved_key = next((k for k in pos_new if k in pos_old and pos_old[k] != pos_new[k]), None)

        if moved_key:
            animating, anim_card_key = True, moved_key
            anim_start_pos, anim_end_pos = pos_old[moved_key], pos_new[moved_key]
            anim_start_time = current_time

        update_board_from_state(next_state)
        if not solver_ctx['path']: solver_ctx['status'] = "Finished Auto-playing!"


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            solver_ctx['is_solving'] = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not solver_ctx['path']:
            btn_clicked = False

            if buttons["BFS"].collidepoint(mouse_x, mouse_y):
                if not solver_ctx['is_solving']:
                    solver_ctx['is_solving'] = True
                    start_tabs = tuple(tuple((c['rank'], c['suit']) for c in col) for col in tableaus)
                    start_fcs = tuple((c['rank'], c['suit']) if c else None for c in free_cells)
                    start_founds = tuple(len(f) for f in foundations)
                    threading.Thread(target=run_bfs, args=(start_tabs, start_fcs, start_founds, solver_ctx),
                                     daemon=True).start()
                btn_clicked = True

            elif buttons["DFS"].collidepoint(mouse_x, mouse_y):
                # call DFS o day

                btn_clicked = True
            elif buttons["UCS"].collidepoint(mouse_x, mouse_y):
                # call UCS o day

                btn_clicked = True
            elif buttons["A*"].collidepoint(mouse_x, mouse_y):
                # call A* o day

                btn_clicked = True

            if btn_clicked: continue

            for col_idx, column in enumerate(tableaus):
                clicked_row = -1
                for row_idx in range(len(column) - 1, -1, -1):
                    rect_h = 96 if row_idx == len(column) - 1 else 35
                    if pygame.Rect(50 + col_idx * 130, 200 + row_idx * 35, 72, rect_h).collidepoint(mouse_x, mouse_y):
                        clicked_row = row_idx
                        break
                if clicked_row != -1:
                    seq = column[clicked_row:]
                    empty_fc, empty_cols = free_cells.count(None), sum(1 for c in tableaus if not c)
                    if is_valid_sequence(seq) and len(seq) <= get_max_movable_cards(empty_fc, empty_cols, True):
                        dragging_cards = seq
                        del tableaus[col_idx][clicked_row:]
                        source_type, source_index = 'tableau', col_idx
                        drag_offset_x, drag_offset_y = (50 + col_idx * 130) - mouse_x, (
                                    200 + clicked_row * 35) - mouse_y
                    break

            if not dragging_cards:
                for i in range(4):
                    if free_cells[i] and pygame.Rect(50 + i * 130, 40, 72, 96).collidepoint(mouse_x, mouse_y):
                        dragging_cards = [free_cells[i]]
                        free_cells[i] = None
                        source_type, source_index = 'freecell', i
                        drag_offset_x, drag_offset_y = (50 + i * 130) - mouse_x, 40 - mouse_y
                        break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and not solver_ctx['path']:
            if dragging_cards:
                moved = False


                def try_drop_to(dest_type, coords_list, size=(72, 96)):
                    for idx, (dx, dy) in enumerate(coords_list):
                        if pygame.Rect(dx, dy, *size).collidepoint(mouse_x, mouse_y):
                            if validate_drop(dragging_cards, dest_type, idx):
                                execute_move(dragging_cards, dest_type, idx)
                                return True
                    return False


                moved = try_drop_to('foundation', [(570 + i * 130, 40) for i in range(4)])
                if not moved: moved = try_drop_to('freecell', [(50 + i * 130, 40) for i in range(4)])
                if not moved: moved = try_drop_to('tableau',
                                                  [(50 + i * 130, 200 + max(0, len(tableaus[i]) - 1) * 35) for i in
                                                   range(8)], size=(72, 300))
                if not moved: execute_move(dragging_cards, source_type, source_index)
                dragging_cards = []

    # draw GUI
    screen.fill(BG_COLOR)
    for i in range(4):
        screen.blit(card_images["shade.gif"], (50 + i * 130, 40))
        if free_cells[i]:
            fc_card = free_cells[i]
            if not (animating and anim_card_key == (fc_card['rank'], fc_card['suit'])):
                screen.blit(fc_card['img'], (50 + i * 130, 40))

        screen.blit(card_images[f"bottom{i}.gif"], (570 + i * 130, 40))
        if foundations[i]:
            top_card = foundations[i][-1]
            if animating and anim_card_key == (top_card['rank'], top_card['suit']):
                if len(foundations[i]) > 1: screen.blit(foundations[i][-2]['img'], (570 + i * 130, 40))
            else:
                screen.blit(top_card['img'], (570 + i * 130, 40))

    for col_idx, col_cards in enumerate(tableaus):
        for row_idx, card_info in enumerate(col_cards):
            if animating and anim_card_key == (card_info['rank'], card_info['suit']): continue
            screen.blit(card_info['img'], (50 + col_idx * 130, 200 + row_idx * 35))

    if dragging_cards:
        for i, card_info in enumerate(dragging_cards):
            screen.blit(card_info['img'], (mouse_x + drag_offset_x, mouse_y + drag_offset_y + i * 35))

    if animating and anim_card_key:
        progress = max(0.0, min(1.0, (current_time - anim_start_time) / ANIM_DURATION))
        curr_x = anim_start_pos[0] + (anim_end_pos[0] - anim_start_pos[0]) * progress
        curr_y = anim_start_pos[1] + (anim_end_pos[1] - anim_start_pos[1]) * progress
        screen.blit(card_images[f"{anim_card_key[0]:02d}{anim_card_key[1]}.gif"], (curr_x, curr_y))

    status_surf = font.render(f"Status: {solver_ctx['status']}", True, (255, 255, 255))
    screen.blit(status_surf, (550, 730))

    for name, rect in buttons.items():
        color = (255, 100, 100) if name == "BFS" and solver_ctx['is_solving'] else (
            (180, 180, 180) if rect.collidepoint(mouse_x, mouse_y) else (220, 220, 220))
        pygame.draw.rect(screen, color, rect, border_radius=5)
        text_surf = font.render(name, True, (0, 0, 0))
        screen.blit(text_surf, text_surf.get_rect(center=rect.center))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()