SUITS_MAP = {'c': 0, 'd': 1, 'h': 2, 's': 3}
INV_SUITS = ['c', 'd', 'h', 's']
foundation_suits = ['s', 'h', 'd', 'c']


def get_color(suit):
    return 'red' if suit in ['d', 'h'] else 'black'


def get_max_movable_cards(empty_fc, empty_cols, moving_to_empty_col=False):
    if moving_to_empty_col and empty_cols > 0: empty_cols -= 1
    return (1 + empty_fc) * (2 ** empty_cols)


def is_valid_sequence(cards):
    for i in range(len(cards) - 1):
        if cards[i]['color'] == cards[i + 1]['color'] or cards[i]['rank'] != cards[i + 1]['rank'] + 1:
            return False
    return True


def encode_state(tabs, fcs, founds):
    b_founds = bytes(founds)

    fc_vals = []
    for c in fcs:
        if c is None:
            fc_vals.append(0)
        else:
            fc_vals.append(SUITS_MAP[c[1]] * 13 + c[0])
    b_fcs = bytes(sorted(fc_vals))

    tab_b = []
    for col in tabs:
        if col:
            tab_b.append(bytes([SUITS_MAP[s] * 13 + r for r, s in col]))
    tab_b.sort()

    return b_founds + b_fcs + b'\xff'.join(tab_b) if tab_b else b_founds + b_fcs


def decode_state(b_state):
    founds = tuple(b_state[0:4])
    fcs = []
    for val in b_state[4:8]:
        if val == 0:
            fcs.append(None)
        else:
            fcs.append(((val - 1) % 13 + 1, INV_SUITS[(val - 1) // 13]))

    tabs = []
    if len(b_state) > 8:
        for b_col in b_state[8:].split(b'\xff'):
            if not b_col: continue
            col = tuple(((val - 1) % 13 + 1, INV_SUITS[(val - 1) // 13]) for val in b_col)
            tabs.append(col)

    while len(tabs) < 8: tabs.append(())

    return tuple(tabs), tuple(fcs), founds


def get_successors(tabs, fcs, founds):
    successors = []

    # uu tien dua len foundations
    for i, col in enumerate(tabs):
        if col:
            rank, suit = col[-1]
            f_idx = foundation_suits.index(suit)
            if rank == founds[f_idx] + 1:
                new_tabs = list(tabs)
                new_tabs[i] = col[:-1]
                new_founds = list(founds)
                new_founds[f_idx] += 1
                return [(tuple(new_tabs), fcs, tuple(new_founds))]

    for i, card in enumerate(fcs):
        if card:
            rank, suit = card
            f_idx = foundation_suits.index(suit)
            if rank == founds[f_idx] + 1:
                new_fcs = list(fcs)
                new_fcs[i] = None
                new_founds = list(founds)
                new_founds[f_idx] += 1
                return [(tabs, tuple(new_fcs), tuple(new_founds))]

    first_empty_col = -1
    for idx, col in enumerate(tabs):
        if not col:
            first_empty_col = idx
            break

    # tableaus -> tableaus
    for i, src_col in enumerate(tabs):
        if not src_col: continue

        card = src_col[-1]
        for j, dest_col in enumerate(tabs):
            if i == j: continue
            if dest_col:
                dest_card = dest_col[-1]
                if get_color(card[1]) != get_color(dest_card[1]) and card[0] == dest_card[0] - 1:
                    new_tabs = list(tabs)
                    new_tabs[j] = dest_col + (card,)
                    new_tabs[i] = src_col[:-1]
                    successors.append((tuple(new_tabs), fcs, founds))

        if first_empty_col != -1 and first_empty_col != i:
            new_tabs = list(tabs)
            new_tabs[first_empty_col] = (card,)
            new_tabs[i] = src_col[:-1]
            successors.append((tuple(new_tabs), fcs, founds))

    # freecells -> tableaus
    for i, card in enumerate(fcs):
        if card:
            for j, dest_col in enumerate(tabs):
                if dest_col:
                    dest_card = dest_col[-1]
                    if get_color(card[1]) != get_color(dest_card[1]) and card[0] == dest_card[0] - 1:
                        new_tabs = list(tabs)
                        new_tabs[j] = dest_col + (card,)
                        new_fcs = list(fcs)
                        new_fcs[i] = None
                        successors.append((tuple(new_tabs), tuple(new_fcs), founds))

            if first_empty_col != -1:
                new_tabs = list(tabs)
                new_tabs[first_empty_col] = (card,)
                new_fcs = list(fcs)
                new_fcs[i] = None
                successors.append((tuple(new_tabs), tuple(new_fcs), founds))

    # tableaus -> freecells
    if None in fcs:
        empty_idx = fcs.index(None)
        for i, col in enumerate(tabs):
            if not col: continue
            new_tabs = list(tabs)
            card = col[-1]
            new_tabs[i] = col[:-1]
            new_fcs = list(fcs)
            new_fcs[empty_idx] = card
            successors.append((tuple(new_tabs), tuple(new_fcs), founds))

    return successors