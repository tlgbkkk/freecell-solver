import pygame
import os
import sys
from pysol_cards.deal_game import Game 


# --- CẤU HÌNH ---
PICS_DIR = r"D:\mrbeast\pics"
WIDTH, HEIGHT = 1100, 800
FPS = 120
BG_COLOR = (20, 100, 20)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("FreeCell")
clock = pygame.time.Clock()

# --- LOAD TÀI NGUYÊN (LOAD 1 LẦN DÙNG MÃI) ---
card_images = {}
# Danh sách file cần load, bao gồm cả các ô trống
required_images = ["bottom0.gif", "bottom1.gif", "bottom2.gif", "bottom3.gif", "shade.gif"]
for s in ['c', 'd', 'h', 's']:
    for r in range(1, 14):
        required_images.append(f"{r:02d}{s}.gif")

for img_name in required_images:
    path = os.path.join(PICS_DIR, img_name)
    if os.path.exists(path):
        # convert_alpha() giúp vẽ cực nhanh
        card_images[img_name] = pygame.image.load(path).convert_alpha()
    else:
        print(f"Cảnh báo: Thiếu ảnh {path}, game có thể bị lỗi.")

# Tọa độ các ô
freecell_rects = []
foundation_rects = []
tableau_rects = []

# --- LOGIC CHIA BÀI ---
def get_card_filename(card):
    suits = ['c', 'd', 'h', 's']
    # Fix lỗi KeyError '14s.gif' bằng cách ép rank về khoảng 1-13
    rank = (card.rank % 13)
    if rank == 0: rank = 13
    s_idx = card.suit % 4
    return f"{rank:02d}{suits[s_idx]}.gif"

# Khởi tạo game và chia bài (Ván số 1, Microsoft deal)
fc_logic = Game('freecell', 2, 'ms')
fc_logic.deal() 
fc_logic.freecell() 

# Quản lý 8 cột bài (Tableaus)
tableaus = []
for col in fc_logic.board.columns.cols:
    column_data = []
    for card in col:
        filename = get_card_filename(card)
        if filename in card_images:
            column_data.append({
                'img': card_images[filename],
                'name': filename
            })
    tableaus.append(column_data)

# Quản lý 4 ô FreeCell (Góc trái)
# Chúng ta bắt đầu bằng ô trống
free_cells = [None] * 4

# Quản lý 4 ô Foundation (Góc phải)
# Chúng ta bắt đầu bằng ô trống
foundations = [None] * 4

# --- BIẾN QUẢN LÝ KÉO THẢ ---
dragging_card = None
drag_offset_x = 0
drag_offset_y = 0
source_type = None # 'tableau', 'freecell'
source_index = None

# --- VÒNG LẶP CHÍNH ---
running = True
while running:
    mouse_x, mouse_y = pygame.mouse.get_pos()
    
    # 1. XỬ LÝ SỰ KIỆN MOUSE & KEYBOARD
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Click chuột trái
                # Kiểm tra click vào 8 cột bài
                for col_idx, column in enumerate(tableaus):
                    if column:
                        # Kiểm tra chỉ lá bài cuối cùng (trên cùng) mới được kéo
                        card_x = 50 + col_idx * 130
                        card_y = 200 + (len(column) - 1) * 35
                        # Giả định kích thước bài là 72x96 (từ file ảnh của bạn)
                        card_rect = pygame.Rect(card_x, card_y, 72, 96)
                        if card_rect.collidepoint(mouse_x, mouse_y):
                            dragging_card = column.pop()
                            source_type = 'tableau'
                            source_index = col_idx
                            drag_offset_x = card_x - mouse_x
                            drag_offset_y = card_y - mouse_y
                            break
                            
                # (Sẽ thêm logic kiểm tra click vào FreeCell ở bước sau)

        elif event.type == pygame.MOUSEBUTTONUP:
            if dragging_card:
                if event.button == 1:
                    # Kiểm tra xem có thả vào ô FreeCell nào không
                    moved_to_freecell = False
                    for i in range(4):
                        fc_rect = pygame.Rect(50 + i * 130, 40, 72, 96)
                        if fc_rect.collidepoint(mouse_x, mouse_y):
                            if free_cells[i] is None: # Ô trống mới được thả
                                free_cells[i] = dragging_card
                                dragging_card = None
                                moved_to_freecell = True
                                break
                    
                    if not moved_to_freecell:
                        # (Sẽ thêm logic kiểm tra thả vào Foundation ở bước sau)
                        # Tạm thời trả về chỗ cũ nếu không có chỗ chứa
                        if source_type == 'tableau':
                            tableaus[source_index].append(dragging_card)
                        dragging_card = None

    # 2. VẼ GIAO DIỆN
    screen.fill(BG_COLOR)

    # A. Vẽ 4 ô FreeCell (Góc trái, dùng shade.gif cho ô mờ)
    for i in range(4):
        # Vẽ nền ô mờ
        screen.blit(card_images["shade.gif"], (50 + i * 130, 40))
        # Nếu ô có bài, vẽ quân bài lên trên
        if free_cells[i]:
            screen.blit(free_cells[i]['img'], (50 + i * 130, 40))

    # B. Vẽ 4 ô Foundation (Góc phải, dùng bottom0.gif để gợi ý)
    # Pysol suit: 0=Club, 1=Diamond, 2=Heart, 3=Spade -> Map sang bottom0-3.gif
    for i in range(4):
        # Vẽ nền ô có hình chất bài
        foundation_name = f"bottom{i}.gif"
        screen.blit(card_images[foundation_name], (570 + i * 130, 40))
        # Nếu ô có bài, vẽ quân bài lên trên
        if foundations[i]:
            screen.blit(foundations[i]['img'], (570 + i * 130, 40))

    # C. Vẽ 8 cột bài (Tableaus)
    for col_idx, col_cards in enumerate(tableaus):
        for row_idx, card_info in enumerate(col_cards):
            x = 50 + col_idx * 130
            y = 200 + row_idx * 35
            screen.blit(card_info['img'], (x, y))

    # D. Vẽ quân bài đang được kéo theo chuột
    if dragging_card:
        screen.blit(dragging_card['img'], (mouse_x + drag_offset_x, mouse_y + drag_offset_y))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()