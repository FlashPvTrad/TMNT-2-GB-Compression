import sys

def decompress(data, offset):
    out = bytearray()
    de = offset
    n_data = len(data)
    while True:
        c = data[de]; de += 1
        if c == 0:
            break
        if (c & 0x80) == 0:
            # RLE: repeat single byte c times
            count = c
            val = data[de]; de += 1
            out.extend([val]) 
            out.extend([val]*(count-1))
        else:
            low = c & 0x7F
            if low == 0:
                # extended command (c == 0x80)
                d2 = data[de]; de += 1
                if (d2 & 0x80) == 0:
                    # increment fill, count = d2
                    count = d2
                    start = data[de]; de += 1
                    for i in range(count):
                        out.append((start + i) & 0xFF)
                else:
                    typ = d2 & 0x7F
                    cnt = data[de]; de += 1
                    for i in range(cnt):
                        x = data[de]; de += 1
                        if typ == 1:
                            out.append(x); out.append(0x00)
                        elif typ == 2:
                            out.append(0x00); out.append(x)
                        elif typ == 3:
                            out.append(x); out.append(x)
                        elif typ == 4:
                            out.append(0xFF); out.append(x)
                        elif typ == 5:
                            out.append(x); out.append(0xFF)
                        else:
                            out.append((~x) & 0xFF); out.append(x)
            else:
                count = low
                for i in range(count):
                    out.append(data[de]); de += 1
        if de > n_data:
            raise ValueError("Ran past end of file - stream may not be self-terminating as assumed")
    return bytes(out), de

if __name__ == "__main__":
    rom_path = "/mnt/user-data/uploads/Teenage_Mutant_Ninja_Turtles_II_-_Back_from_the_Sewers__USA_.gb"
    data = open(rom_path, "rb").read()
    offset = 0x3497D
    decompressed, end_off = decompress(data, offset)
    print("Start offset:", hex(offset))
    print("End offset (exclusive, after terminator):", hex(end_off))
    print("Compressed size:", end_off - offset, "bytes")
    print("Decompressed size:", len(decompressed), "bytes")
    print("Decompressed / 16 (tiles if 2bpp):", len(decompressed)/16)
    print("First 64 bytes of output:")
    print(' '.join(f'{b:02X}' for b in decompressed[:64]))
    with open("/home/claude/gfx_3497D.bin", "wb") as f:
        f.write(decompressed)
