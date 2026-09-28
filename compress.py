from decompress import decompress

def optimal_compress(data):
    """Dynamic-programming optimal parse: minimizes total compressed size.
    Returns compressed bytes (including 0x00 terminator)."""
    n = len(data)
    D = [0] * (n + 1)          # D[i] = min cost to encode data[i:]
    choice = [None] * (n + 1)  # choice[i] = op used at position i

    for i in range(n - 1, -1, -1):
        remaining = n - i
        best_cost = None
        best_choice = None

        # --- RLE: repeat data[i] r times, r = 1..R, cost = 2 ---
        R = 1
        maxR = min(127, remaining)
        while R < maxR and data[i + R] == data[i]:
            R += 1
        for r in range(1, R + 1):
            c = 2 + D[i + r]
            if best_cost is None or c < best_cost:
                best_cost = c
                best_choice = ('RLE', r)

        # --- INC: increasing-by-1 sequence, r = 1..Rinc, cost = 3 ---
        Rinc = 1
        maxRinc = min(127, remaining)
        while Rinc < maxRinc and data[i + Rinc] == ((data[i] + Rinc) & 0xFF):
            Rinc += 1
        for r in range(1, Rinc + 1):
            c = 3 + D[i + r]
            if c < best_cost:
                best_cost = c
                best_choice = ('INC', r)

        # --- PAIR types 1-6, p = 1..P, cost = 3+p, outlen = 2p ---
        maxpairs = min(255, remaining // 2)
        for typ in range(1, 7):
            P = 0
            while P < maxpairs:
                a = data[i + 2 * P]
                b = data[i + 2 * P + 1]
                if typ == 1:
                    ok = (b == 0x00)
                elif typ == 2:
                    ok = (a == 0x00)
                elif typ == 3:
                    ok = (a == b)
                elif typ == 4:
                    ok = (a == 0xFF)
                elif typ == 5:
                    ok = (b == 0xFF)
                else:
                    ok = (a == ((~b) & 0xFF))
                if not ok:
                    break
                P += 1
            for p in range(1, P + 1):
                c = 3 + p + D[i + 2 * p]
                if c < best_cost:
                    best_cost = c
                    best_choice = ('PAIR', typ, p)

        # --- LIT: literal run, l = 1..min(127,remaining), cost = 1+l ---
        maxlit = min(127, remaining)
        for l in range(1, maxlit + 1):
            c = 1 + l + D[i + l]
            if c < best_cost:
                best_cost = c
                best_choice = ('LIT', l)

        D[i] = best_cost
        choice[i] = best_choice

    # reconstruct
    out = bytearray()
    i = 0
    while i < n:
        ch = choice[i]
        if ch[0] == 'RLE':
            r = ch[1]
            out.append(r & 0x7F)
            out.append(data[i])
            i += r
        elif ch[0] == 'INC':
            r = ch[1]
            out.append(0x80)
            out.append(r & 0x7F)
            out.append(data[i])
            i += r
        elif ch[0] == 'PAIR':
            typ, p = ch[1], ch[2]
            out.append(0x80)
            out.append(0x80 | typ)
            out.append(p & 0xFF)
            for k in range(p):
                a = data[i + 2 * k]
                b = data[i + 2 * k + 1]
                if typ in (1, 3, 5):
                    out.append(a)
                else:
                    out.append(b)
            i += 2 * p
        elif ch[0] == 'LIT':
            l = ch[1]
            out.append(0x80 | l)
            out.extend(data[i:i + l])
            i += l
    out.append(0x00)
    return bytes(out)


def _run_len_same(data, i, maxlen):
    n = len(data)
    l = 1
    while l < maxlen and i + l < n and data[i + l] == data[i]:
        l += 1
    return l

def _run_len_inc(data, i, maxlen):
    n = len(data)
    l = 1
    while l < maxlen and i + l < n and data[i + l] == ((data[i] + l) & 0xFF):
        l += 1
    return l

def _run_len_pairtype(data, i, maxpairs, typ):
    n = len(data)
    pairs = 0
    while pairs < maxpairs and i + 2 * pairs + 1 < n:
        a = data[i + 2 * pairs]
        b = data[i + 2 * pairs + 1]
        ok = False
        if typ == 1:
            ok = (b == 0x00)
        elif typ == 2:
            ok = (a == 0x00)
        elif typ == 3:
            ok = (a == b)
        elif typ == 4:
            ok = (a == 0xFF)
        elif typ == 5:
            ok = (b == 0xFF)
        elif typ == 6:
            ok = (a == ((~b) & 0xFF))
        if not ok:
            break
        pairs += 1
    return pairs

def compress(data):
    """Greedy encoder for the TMNT2 GB compression scheme.
    Returns compressed bytes (including the 0x00 terminator)."""
    out = bytearray()
    i = 0
    n = len(data)

    while i < n:
        remaining = n - i
        best = None  # (gain_ratio, cost, outlen, encode_fn)

        # Option: RLE (repeat single byte), cost=2, outlen=run
        rle = _run_len_same(data, i, min(127, remaining))
        if rle >= 1:
            cost = 2
            outlen = rle
            cand = (outlen - cost, cost, outlen, ('rle', outlen))
            if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[2] > best[2]):
                best = cand

        # Option: increment fill, cost=3, outlen=run (d2 must be <0x80 => max 127)
        inc = _run_len_inc(data, i, min(127, remaining))
        if inc >= 1:
            cost = 3
            outlen = inc
            cand = (outlen - cost, cost, outlen, ('inc', outlen))
            if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[2] > best[2]):
                best = cand

        # Option: pair types 1-6, cost=3+pairs, outlen=2*pairs (count byte max 255)
        maxpairs = min(255, remaining // 2)
        for typ in range(1, 7):
            pairs = _run_len_pairtype(data, i, maxpairs, typ)
            if pairs >= 1:
                cost = 3 + pairs
                outlen = 2 * pairs
                cand = (outlen - cost, cost, outlen, ('pair', typ, pairs))
                if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[2] > best[2]):
                    best = cand

        # Decide: only use a special encoding if it truly beats literal (gain>0)
        use_special = best is not None and best[0] > 0

        if use_special:
            kind = best[3]
            if kind[0] == 'rle':
                outlen = kind[1]
                out.append(outlen & 0x7F)  # bit7 clear
                out.append(data[i])
                i += outlen
            elif kind[0] == 'inc':
                outlen = kind[1]
                out.append(0x80)
                out.append(outlen & 0x7F)  # bit7 clear = increment fill, count
                out.append(data[i])
                i += outlen
            elif kind[0] == 'pair':
                typ = kind[1]
                pairs = kind[2]
                out.append(0x80)
                out.append(0x80 | typ)
                out.append(pairs & 0xFF)
                for k in range(pairs):
                    a = data[i + 2 * k]
                    b = data[i + 2 * k + 1]
                    if typ == 1:
                        out.append(a)
                    elif typ == 2:
                        out.append(b)
                    elif typ == 3:
                        out.append(a)
                    elif typ == 4:
                        out.append(b)
                    elif typ == 5:
                        out.append(a)
                    elif typ == 6:
                        out.append(b)
                i += 2 * pairs
        else:
            # literal run: extend until a special pattern would give a real gain, or hit 127/end
            lit_start = i
            lit_len = 0
            while i < n and lit_len < 127:
                remaining2 = n - i
                # check if a special pattern starting here would have gain>0
                r = _run_len_same(data, i, min(127, remaining2))
                gain_rle = r - 2 if r >= 1 else -999
                r2 = _run_len_inc(data, i, min(127, remaining2))
                gain_inc = r2 - 3 if r2 >= 1 else -999
                gain_pair = -999
                mp = min(255, remaining2 // 2)
                for typ in range(1, 7):
                    p = _run_len_pairtype(data, i, mp, typ)
                    if p >= 1:
                        g = 2 * p - (3 + p)
                        if g > gain_pair:
                            gain_pair = g
                if gain_rle > 0 or gain_inc > 0 or gain_pair > 0:
                    break
                i += 1
                lit_len += 1
            if lit_len == 0:
                # forced to emit at least 1 literal byte to make progress
                i += 1
                lit_len = 1
            out.append(0x80 | lit_len)
            out.extend(data[lit_start:lit_start + lit_len])

    out.append(0x00)  # terminator
    return bytes(out)


if __name__ == "__main__":
    import sys
    rom_path = "/mnt/user-data/uploads/Teenage_Mutant_Ninja_Turtles_II_-_Back_from_the_Sewers__USA_.gb"
    rom = open(rom_path, "rb").read()

    blocks = [0x342DA, 0x3497D, 0x35134]
    for off in blocks:
        decompressed, end_off = decompress(rom, off)
        orig_compressed = rom[off:end_off]
        recompressed = compress(decompressed)
        # verify round trip
        redecompressed, _ = decompress(recompressed, 0)
        ok_roundtrip = (redecompressed == decompressed)
        ok_exact = (recompressed == orig_compressed)
        print(f"--- Block at {hex(off)} ---")
        print("Original compressed size :", len(orig_compressed))
        print("Recompressed size        :", len(recompressed))
        print("Round-trip identical?    :", ok_roundtrip)
        print("Byte-exact vs original?  :", ok_exact)
        if not ok_exact:
            m = min(len(orig_compressed), len(recompressed))
            first_diff = next((k for k in range(m) if orig_compressed[k]!=recompressed[k]), m)
            print("First differing byte at offset (relative):", first_diff, "/", m)
        print()
