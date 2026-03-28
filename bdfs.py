import time
from collections import deque

FOUNDATION_SUITS = ['s', 'h', 'd', 'c']
SUIT_TO_INDEX = {s: i for i, s in enumerate(FOUNDATION_SUITS)}

def get_color(suit):
    return 'red' if suit in ['d', 'h'] else 'black'

def encode_state(tableaus, free_cells, foundations):
    """Canonical encoding using sorted tuples for maximum speed."""
    fcs = tuple(sorted(c for c in free_cells if c is not None))
    tabs = tuple(sorted(tuple(col) for col in tableaus))
    return (tuple(foundations), fcs, tabs)

def is_safe_to_foundation(card, foundations):
    rank, suit = card
    suit_idx = SUIT_TO_INDEX[suit]
    if foundations[suit_idx] != rank - 1:
        return False
    if rank <= 2: return True
    color = get_color(suit)
    opp_suits = ['s', 'c'] if color == 'red' else ['d', 'h']
    for opp_suit in opp_suits:
        if foundations[SUIT_TO_INDEX[opp_suit]] < rank - 1: 
            return False
    return True

def generate_child_states(state):
    tableaus, free_cells, foundations = state
    
    # Priority: Safe Foundation moves (Pruning)
    for col_idx, col in enumerate(tableaus):
        if col and is_safe_to_foundation(col[-1], foundations):
            card = col[-1]
            new_tabs = list(tableaus)
            new_tabs[col_idx] = col[:-1]
            new_founds = list(foundations)
            new_founds[SUIT_TO_INDEX[card[1]]] += 1
            return [(tuple(new_tabs), free_cells, tuple(new_founds))]

    for fc_idx, card in enumerate(free_cells):
        if card and is_safe_to_foundation(card, foundations):
            new_fcs = list(free_cells)
            new_fcs[fc_idx] = None
            new_founds = list(foundations)
            new_founds[SUIT_TO_INDEX[card[1]]] += 1
            return [(tableaus, tuple(new_fcs), tuple(new_founds))]

    empty_fc = free_cells.count(None)
    empty_cols = sum(1 for col in tableaus if not col)
    max_movable = (1 + empty_fc) * (1 << empty_cols)
    children = []

    # Tableau to Tableau
    for col_idx, col in enumerate(tableaus):
        if not col: continue
        for seq_idx in range(len(col) - 1, -1, -1):
            seq = col[seq_idx:]
            if len(seq) > 1:
                c1, c2 = col[seq_idx], col[seq_idx+1]
                if get_color(c1[1]) == get_color(c2[1]) or c1[0] != c2[0] + 1:
                    break
            
            if len(seq) > max_movable: continue

            for t_idx, t_col in enumerate(tableaus):
                if t_idx == col_idx: continue
                can_move = False
                if not t_col:
                    if len(seq) <= (1 + empty_fc) * (1 << (empty_cols - 1 if empty_cols > 0 else 0)):
                        can_move = True
                elif get_color(t_col[-1][1]) != get_color(seq[0][1]) and seq[0][0] == t_col[-1][0] - 1:
                    can_move = True

                if can_move:
                    new_tabs = list(tableaus)
                    new_tabs[col_idx] = col[:seq_idx]
                    new_tabs[t_idx] = t_col + seq
                    children.append((tuple(new_tabs), free_cells, foundations))

        # Tableau to Freecell
        if empty_fc > 0:
            for f_idx, slot in enumerate(free_cells):
                if slot is None:
                    new_tabs = list(tableaus)
                    new_tabs[col_idx] = col[:-1]
                    new_fcs = list(free_cells)
                    new_fcs[f_idx] = col[-1]
                    children.append((tuple(new_tabs), tuple(new_fcs), foundations))
                    break

    # Freecell to Tableau
    for f_idx, card in enumerate(free_cells):
        if card is None: continue
        for t_idx, t_col in enumerate(tableaus):
            if not t_col or (get_color(t_col[-1][1]) != get_color(card[1]) and card[0] == t_col[-1][0] - 1):
                new_tabs = list(tableaus)
                new_tabs[t_idx] = t_col + (card,)
                new_fcs = list(free_cells)
                new_fcs[f_idx] = None
                children.append((tuple(new_tabs), tuple(new_fcs), foundations))

    return children

def run_bfs(start_tabs, start_fcs, start_founds, solver_ctx):
    solve_generic(start_tabs, start_fcs, start_founds, solver_ctx, mode='BFS')

def run_dfs(start_tabs, start_fcs, start_founds, solver_ctx):
    solve_generic(start_tabs, start_fcs, start_founds, solver_ctx, mode='DFS')

def solve_generic(start_tabs, start_fcs, start_founds, solver_ctx, mode='BFS'):
    """Unified solver for BFS and DFS to keep code clean."""
    start_time = time.time()
    start_state = (tuple(start_tabs), tuple(start_fcs), tuple(start_founds))
    start_enc = encode_state(*start_state)
    
    # BFS uses popleft() on a deque, DFS uses pop() on a list
    container = deque([(start_state, start_enc)])
    visited = {start_enc}
    parent_map = {start_enc: (None, start_state)}
    
    expanded = 0
    while container:
        curr_state, curr_enc = container.popleft() if mode == 'BFS' else container.pop()
        expanded += 1
        
        if sum(curr_state[2]) == 52:
            path = []
            curr = curr_enc
            while curr != start_enc:
                p_enc, state = parent_map[curr]
                path.append(state)
                curr = p_enc
            solver_ctx['path'] = path[::-1]
            solver_ctx['status'] = f"{mode} Solved! Exp: {expanded} Time: {time.time()-start_time:.2f}s"
            solver_ctx['is_solving'] = False
            return
            
        for child in generate_child_states(curr_state):
            child_enc = encode_state(*child)
            if child_enc not in visited:
                visited.add(child_enc)
                parent_map[child_enc] = (curr_enc, child)
                container.append((child, child_enc))

    solver_ctx['status'] = f"{mode} Failed."
    solver_ctx['is_solving'] = False