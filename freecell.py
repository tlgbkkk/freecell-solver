import pygame
import os
import random
from pysol_cards.deal_game import Game

# config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PICS_DIR = os.path.join(BASE_DIR, "pics")
WIDTH, HEIGHT = 1100, 800
FPS = 60
BG_COLOR = (20, 100, 20)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("FreeCell Solver")
clock = pygame.time.Clock()

# load resource
card_images = {}
required_images = ["bottom0.gif", "bottom1.gif", "bottom2.gif", "bottom3.gif", "shade.gif"]
for s in ['c', 'd', 'h', 's']:
    for r in range(1, 14):
        required_images.append(f"{r:02d}{s}.gif")

for img_name in required_images:
    path = os.path.join(PICS_DIR, img_name)
    if os.path.exists(path):
        card_images[img_name] = pygame.image.load(path).convert_alpha()
    else:
        placeholder = pygame.Surface((72, 96))
        placeholder.fill((200, 0, 0))
        card_images[img_name] = placeholder


def get_card_filename(card):
    suits = ['c', 'd', 'h', 's']
    rank = (card.rank % 13)
    if rank == 0: rank = 13
    return f"{rank:02d}{suits[card.suit % 4]}.gif"


fc_logic = Game('freecell', random.randint(1, 1000000), 'ms')
fc_logic.deal()
fc_logic.freecell()

tableaus = []
for col in fc_logic.board.columns.cols:
    column_data = []
    for card in col:
        filename = get_card_filename(card)
        if filename in card_images:
            rank = int(filename[:2])
            suit = filename[2]
            column_data.append({
                'img': card_images[filename],
                'name': filename,
                'rank': rank,
                'suit': suit,
                'color': 'red' if suit in ['d', 'h'] else 'black'
            })
    tableaus.append(column_data)

free_cells = [None] * 4
foundations = [[] for _ in range(4)]
foundation_suits = ['s', 'h', 'd', 'c']

dragging_cards = []
drag_offset_x = drag_offset_y = 0
source_type = source_index = None


def get_max_movable_cards(empty_fc, empty_cols, moving_to_empty_col=False):
    if moving_to_empty_col and empty_cols > 0:
        empty_cols -= 1
    return (1 + empty_fc) * (2 ** empty_cols)


def is_valid_sequence(cards):
    for i in range(len(cards) - 1):
        if cards[i]['color'] == cards[i + 1]['color'] or cards[i]['rank'] != cards[i + 1]['rank'] + 1:
            return False
    return True


def validate_drop(cards, dest_type, dest_idx):
    if not cards: return False
    first_card = cards[0]

    if dest_type == 'foundation':
        if len(cards) > 1: return False
        target_suit = foundation_suits[dest_idx]
        top_rank = foundations[dest_idx][-1]['rank'] if foundations[dest_idx] else 0
        return first_card['suit'] == target_suit and first_card['rank'] == top_rank + 1

    elif dest_type == 'freecell':
        if len(cards) > 1: return False
        return free_cells[dest_idx] is None

    elif dest_type == 'tableau':
        col = tableaus[dest_idx]
        empty_fc = free_cells.count(None)
        empty_cols = sum(1 for c in tableaus if not c)

        if not col:  # Thả vào cột trống
            return len(cards) <= get_max_movable_cards(empty_fc, empty_cols, moving_to_empty_col=True)
        else:  # Thả nối đuôi
            if len(cards) > get_max_movable_cards(empty_fc, empty_cols, moving_to_empty_col=False):
                return False
            target_card = col[-1]
            return first_card['color'] != target_card['color'] and first_card['rank'] == target_card['rank'] - 1

    return False


def execute_move(cards, dest_type, dest_idx):
    if dest_type == 'foundation':
        foundations[dest_idx].append(cards[0])
    elif dest_type == 'freecell':
        free_cells[dest_idx] = cards[0]
    elif dest_type == 'tableau':
        tableaus[dest_idx].extend(cards)


def solver_move(src_type, src_idx, dest_type, dest_idx, count):
    if src_type == 'tableau':
        if len(tableaus[src_idx]) < count: return False
        cards = tableaus[src_idx][-count:]
        if not is_valid_sequence(cards): return False
    elif src_type == 'freecell' and count == 1:
        if free_cells[src_idx] is None: return False
        cards = [free_cells[src_idx]]
    else:
        return False

    if validate_drop(cards, dest_type, dest_idx):
        if src_type == 'tableau':
            del tableaus[src_idx][-count:]
        elif src_type == 'freecell':
            free_cells[src_idx] = None
        execute_move(cards, dest_type, dest_idx)
        return True
    return False


running = True
while running:
    mouse_x, mouse_y = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 1. Bốc từ Tableau
            for col_idx, column in enumerate(tableaus):
                clicked_row = -1
                for row_idx in range(len(column) - 1, -1, -1):
                    rect_h = 96 if row_idx == len(column) - 1 else 35
                    if pygame.Rect(50 + col_idx * 130, 200 + row_idx * 35, 72, rect_h).collidepoint(mouse_x, mouse_y):
                        clicked_row = row_idx
                        break

                if clicked_row != -1:
                    seq = column[clicked_row:]
                    empty_fc = free_cells.count(None)
                    empty_cols = sum(1 for c in tableaus if not c)
                    max_pickup = get_max_movable_cards(empty_fc, empty_cols,
                                                       moving_to_empty_col=True)

                    if is_valid_sequence(seq) and len(seq) <= max_pickup:
                        dragging_cards = seq
                        del tableaus[col_idx][clicked_row:]
                        source_type, source_index = 'tableau', col_idx
                        drag_offset_x = (50 + col_idx * 130) - mouse_x
                        drag_offset_y = (200 + clicked_row * 35) - mouse_y
                    break

            if not dragging_cards:
                for i in range(4):
                    if free_cells[i] and pygame.Rect(50 + i * 130, 40, 72, 96).collidepoint(mouse_x, mouse_y):
                        dragging_cards = [free_cells[i]]
                        free_cells[i] = None
                        source_type, source_index = 'freecell', i
                        drag_offset_x = (50 + i * 130) - mouse_x
                        drag_offset_y = 40 - mouse_y
                        break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
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
                if not moved:
                    moved = try_drop_to('freecell', [(50 + i * 130, 40) for i in range(4)])
                if not moved:
                    coords = [(50 + i * 130, 200 + max(0, len(tableaus[i]) - 1) * 35) for i in range(8)]
                    moved = try_drop_to('tableau', coords, size=(72, 300))

                if not moved:
                    execute_move(dragging_cards, source_type, source_index)

                dragging_cards = []

    screen.fill(BG_COLOR)

    for i in range(4):
        screen.blit(card_images["shade.gif"], (50 + i * 130, 40))
        if free_cells[i]: screen.blit(free_cells[i]['img'], (50 + i * 130, 40))

    for i in range(4):
        screen.blit(card_images[f"bottom{i}.gif"], (570 + i * 130, 40))
        if foundations[i]: screen.blit(foundations[i][-1]['img'], (570 + i * 130, 40))

    for col_idx, col_cards in enumerate(tableaus):
        for row_idx, card_info in enumerate(col_cards):
            screen.blit(card_info['img'], (50 + col_idx * 130, 200 + row_idx * 35))

    if dragging_cards:
        for i, card_info in enumerate(dragging_cards):
            screen.blit(card_info['img'], (mouse_x + drag_offset_x, mouse_y + drag_offset_y + i * 35))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()