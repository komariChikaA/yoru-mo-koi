import os
import re
import sys

def fmt(v, prec=2):
    s = f"{v:.{prec}f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" or s == "" else s

def format_cmd(ctype, easing, st, et, vals):
    st_s = str(st)
    et_s = str(et) if et != st else ""
    if ctype in ("M", "V"):
        prec = 2 if ctype == "M" else 4
        if len(vals) == 4 and abs(vals[0]-vals[2]) < 1e-4 and abs(vals[1]-vals[3]) < 1e-4:
            vals = vals[:2]
            et_s = ""
        val_str = ",".join(fmt(x, prec) for x in vals)
    elif ctype in ("MX", "MY"):
        if len(vals) == 2 and abs(vals[0]-vals[1]) < 1e-4:
            vals = vals[:1]
            et_s = ""
        val_str = ",".join(fmt(x, 2) for x in vals)
    elif ctype == "F":
        if len(vals) == 2 and abs(vals[0]-vals[1]) < 1e-4:
            vals = vals[:1]
            et_s = ""
        val_str = ",".join(fmt(x, 3) for x in vals)
    elif ctype == "S":
        if len(vals) == 2 and abs(vals[0]-vals[1]) < 1e-4:
            vals = vals[:1]
            et_s = ""
        val_str = ",".join(fmt(x, 4) for x in vals)
    elif ctype == "R":
        if len(vals) == 2 and abs(vals[0]-vals[1]) < 1e-4:
            vals = vals[:1]
            et_s = ""
        val_str = ",".join(fmt(x, 4) for x in vals)
    elif ctype == "C":
        if len(vals) == 6 and vals[:3] == vals[3:]:
            vals = vals[:3]
            et_s = ""
        val_str = ",".join(str(int(round(x))) for x in vals)
    else:
        val_str = ",".join(fmt(x, 3) for x in vals)

    return f" {ctype},{easing},{st_s},{et_s},{val_str}"

def optimize_osb(input_path, output_path):
    print(f"Reading {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    sprite_blocks = re.findall(r"(?m)^((?:Sprite|Animation),[^\n]+(?:\n +[^\n]+)*)", text)
    print(f"Found {len(sprite_blocks)} sprites.")

    if any(re.search(r"(?m)^\s+(?:L|T),", block) for block in sprite_blocks):
        raise ValueError("Loop or trigger groups are not supported by this optimizer; leaving OSB unchanged.")

    out_lines = ["[Events]"]

    removed_invisible = 0
    total_orig_cmds = 0
    total_opt_cmds = 0

    for block in sprite_blocks:
        lines = block.strip().split("\n")
        header = lines[0]
        cmds = lines[1:]
        total_orig_cmds += len(cmds)

        # Check visibility
        max_alpha = 0.0
        has_f = False
        all_sts = []
        all_ets = []
        for l in cmds:
            p = l.strip().split(",")
            st = int(p[2]) if p[2] != "" else 0
            et = int(p[3]) if len(p) > 3 and p[3] != "" else st
            all_sts.append(st)
            all_ets.append(et)
            if p[0] == "F":
                has_f = True
                for v in [float(x) for x in p[4:]]:
                    if v > max_alpha:
                        max_alpha = v
        if not has_f:
            max_alpha = 1.0

        if max_alpha <= 0.001:
            removed_invisible += 1
            continue

        orig_max_et = max(all_ets) if all_ets else 0

        # Parse commands by type
        by_type = {}
        type_order = []
        removed_terminal_holds = []
        for l in cmds:
            parts = l.strip().split(",")
            ctype = parts[0]
            if ctype not in by_type:
                by_type[ctype] = []
                type_order.append(ctype)
            easing = parts[1]
            st = int(parts[2]) if parts[2] != "" else 0
            et = int(parts[3]) if len(parts) > 3 and parts[3] != "" else st
            vals = [float(x) for x in parts[4:]]
            by_type[ctype].append((easing, st, et, vals))

        sprite_opt_cmds = []
        for ctype in type_order:
            clist = by_type[ctype]
            clist.sort(key=lambda x: (x[1], x[2]))

            # Step 1: Remove redundant holds
            merged = []
            for c in clist:
                easing, st, et, vals = c
                if merged:
                    p_easing, p_st, p_et, p_vals = merged[-1]
                    if ctype in ("F", "R", "S"):
                        p_end = p_vals[-1]
                        c_start = vals[0]
                        c_end = vals[-1]
                        if abs(c_start - c_end) < 1e-4 and abs(p_end - c_start) < 1e-4 and easing == "0":
                            if et == orig_max_et:
                                removed_terminal_holds.append((ctype, easing, st, et, vals))
                            continue
                    elif ctype in ("M", "V"):
                        p_end = p_vals if len(p_vals) == 2 else p_vals[2:4]
                        c_start = vals[:2]
                        c_end = vals[2:4] if len(vals) >= 4 else vals[:2]
                        if abs(c_start[0] - c_end[0]) < 1e-3 and abs(c_start[1] - c_end[1]) < 1e-3 and \
                           abs(p_end[0] - c_start[0]) < 1e-3 and abs(p_end[1] - c_start[1]) < 1e-3 and easing == "0":
                            if et == orig_max_et:
                                removed_terminal_holds.append((ctype, easing, st, et, vals))
                            continue
                    elif ctype in ("MX", "MY"):
                        p_end = p_vals[-1]
                        c_start = vals[0]
                        c_end = vals[-1]
                        if abs(c_start - c_end) < 1e-3 and abs(p_end - c_start) < 1e-3 and easing == "0":
                            if et == orig_max_et:
                                removed_terminal_holds.append((ctype, easing, st, et, vals))
                            continue
                merged.append(c)

            # Step 2: Merge collinear segments
            collinear = []
            for c in merged:
                easing, st, et, vals = c
                if collinear and easing == "0" and collinear[-1][0] == "0" and collinear[-1][2] == st:
                    p_easing, p_st, p_et, p_vals = collinear[-1]
                    can_merge = False
                    if ctype in ("F", "R", "S"):
                        p_s = p_vals[0]
                        p_e = p_vals[-1]
                        c_s = vals[0]
                        c_e = vals[-1]
                        if p_et > p_st and et > st:
                            p_rate = (p_e - p_s) / (p_et - p_st)
                            c_rate = (c_e - c_s) / (et - st)
                            if abs(p_rate - c_rate) < 1e-4 and abs(p_e - c_s) < 1e-4:
                                collinear[-1] = (p_easing, p_st, et, [p_s, c_e])
                                can_merge = True
                    elif ctype in ("M", "V"):
                        p_s = p_vals[:2]
                        p_e = p_vals[2:4] if len(p_vals) >= 4 else p_vals[:2]
                        c_s = vals[:2]
                        c_e = vals[2:4] if len(vals) >= 4 else vals[:2]
                        if p_et > p_st and et > st:
                            p_rate_x = (p_e[0] - p_s[0]) / (p_et - p_st)
                            p_rate_y = (p_e[1] - p_s[1]) / (p_et - p_st)
                            c_rate_x = (c_e[0] - c_s[0]) / (et - st)
                            c_rate_y = (c_e[1] - c_s[1]) / (et - st)
                            if abs(p_rate_x - c_rate_x) < 1e-3 and abs(p_rate_y - c_rate_y) < 1e-3 and \
                               abs(p_e[0] - c_s[0]) < 1e-3 and abs(p_e[1] - c_s[1]) < 1e-3:
                                collinear[-1] = (p_easing, p_st, et, [p_s[0], p_s[1], c_e[0], c_e[1]])
                                can_merge = True
                    elif ctype in ("MX", "MY"):
                        p_s = p_vals[0]
                        p_e = p_vals[-1]
                        c_s = vals[0]
                        c_e = vals[-1]
                        if p_et > p_st and et > st:
                            p_rate = (p_e - p_s) / (p_et - p_st)
                            c_rate = (c_e - c_s) / (et - st)
                            if abs(p_rate - c_rate) < 1e-3 and abs(p_e - c_s) < 1e-3:
                                collinear[-1] = (p_easing, p_st, et, [p_s, c_e])
                                can_merge = True
                    if not can_merge:
                        collinear.append(c)
                else:
                    collinear.append(c)

            for c in collinear:
                sprite_opt_cmds.append((ctype, c[0], c[1], c[2], c[3]))

        # Preserve lifetime without extending a fade and changing its slope.
        new_max_et = max((c[3] for c in sprite_opt_cmds), default=0)
        if new_max_et < orig_max_et:
            candidates = [c for c in removed_terminal_holds if c[3] == orig_max_et]
            if not candidates:
                raise ValueError(f"Cannot preserve sprite lifetime ending at {orig_max_et} ms")
            sprite_opt_cmds.append(candidates[-1])

        out_lines.append(header)
        for c in sprite_opt_cmds:
            out_lines.append(format_cmd(c[0], c[1], c[2], c[3], c[4]))
        total_opt_cmds += len(sprite_opt_cmds)

    out_text = "\n".join(out_lines) + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(out_text)

    print(f"Invisible sprites removed: {removed_invisible}")
    print(f"Total commands: {total_orig_cmds} -> {total_opt_cmds} (saved {total_orig_cmds - total_opt_cmds}, {(1-total_opt_cmds/total_orig_cmds)*100:.1f}%)")
    orig_mb = len(text) / (1024 * 1024)
    opt_mb = len(out_text) / (1024 * 1024)
    print(f"File size: {orig_mb:.2f} MB -> {opt_mb:.2f} MB (saved {orig_mb - opt_mb:.2f} MB, {(1 - opt_mb/orig_mb)*100:.1f}%)")
    return {
        "sprites_before": len(sprite_blocks),
        "sprites_removed_invisible": removed_invisible,
        "commands_before": total_orig_cmds,
        "commands_after": total_opt_cmds,
        "commands_removed": total_orig_cmds - total_opt_cmds,
        "original_bytes": len(text.encode("utf-8")),
        "compressed_bytes": len(out_text.encode("utf-8")),
    }

if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2]
    optimize_osb(src, dst)
