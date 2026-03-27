import collections
from logic import encode_state, decode_state, get_successors


def run_bfs(start_tabs, start_fcs, start_founds, ctx):
    start_b = encode_state(start_tabs, start_fcs, start_founds)
    queue = collections.deque([start_b])
    parent_map = {start_b: None}
    count = 0

    while queue and ctx['is_solving']:
        current_b = queue.popleft()
        count += 1

        if current_b[0:4] == b'\x0d\x0d\x0d\x0d':
            ctx['status'] = f"Solved in {count} states!"

            path = []
            curr = current_b
            while curr is not None:
                path.append(curr)
                curr = parent_map[curr]

            path.reverse()
            ctx['path'] = path[1:]
            ctx['status'] = f"Auto-playing {len(ctx['path'])} moves (Checked {count} states)"
            ctx['is_solving'] = False
            return

        current_tabs, current_fcs, current_founds = decode_state(current_b)

        for s_tabs, s_fcs, s_founds in get_successors(current_tabs, current_fcs, current_founds):
            succ_b = encode_state(s_tabs, s_fcs, s_founds)
            if succ_b not in parent_map:
                parent_map[succ_b] = current_b
                queue.append(succ_b)

            ctx['status'] = f"BFS: {count} states..."

    if ctx['is_solving']:
        ctx['status'] = f"Failed. Explored {count} states."
    ctx['is_solving'] = False