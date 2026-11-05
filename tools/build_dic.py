#!/usr/bin/env python3
"""Colorful-dictionary: 元データ（mecab-naist-jdic）から colorful_talk.dic を作る。

使い方:
    python tools/build_dic.py --fetch -o colorful_talk.dic
    python tools/build_dic.py --src DIR -o colorful_talk.dic

形式は docs/spec.md の「形式（版 1）」を参照。
"""
import argparse
import hashlib
import os
import struct
import sys
import urllib.request

# 元データ（Open JTalk の GitHub ミラーの固定したコミット）
SRC_BASE = ("https://raw.githubusercontent.com/r9y9/open_jtalk/"
            "28a90fe334f269eb193191855eb65b8e37c06c47/src/mecab-naist-jdic/")
SRC_FILES = {
    "naist-jdic.csv": "cb9db77c16c6dbd604f5cbe3d1d94418f37563bcf33a117681b97f3f77d98b62",
    "matrix.def": "65d56d1158c3a465c177411fdbefd344b20dc0eee3f614498e1126e04a21b11e",
    "char.def": "1b4b0f30ce562e730187b14fe2a197cba46f1168ac2ecec01a1cea9ec00ebda8",
    "unk.def": "f3ce752bcce069e9b327d7ad86b246f04126eb30a15278bfba33f7f2bda7e5e6",
    "COPYING": "2a64fdfae08961671639767f8921ce8a3dcab81c686f74666b113d8ea4ce2ec9",
}
SRC_ENCODING = "euc_jp"

MAGIC = b"CTDIC\0\0\0"
VERSION = 1
HEADER_SIZE = 64


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(dst):
    os.makedirs(dst, exist_ok=True)
    for name, digest in SRC_FILES.items():
        path = os.path.join(dst, name)
        if not (os.path.exists(path) and sha256(path) == digest):
            print(f"取得: {SRC_BASE}{name}", file=sys.stderr)
            urllib.request.urlretrieve(SRC_BASE + name, path)
        if sha256(path) != digest:
            sys.exit(f"{name} のハッシュが一致しません")


def read_lines(path):
    with open(path, "rb") as f:
        data = f.read()
    for enc in (SRC_ENCODING, "utf-8"):
        try:
            return data.decode(enc).splitlines()
        except UnicodeDecodeError:
            pass
    sys.exit(f"{path} の文字コードを判別できません")


class Pool:
    """重複を除いた文字列プール（UTF-8、末尾 NUL）。"""

    def __init__(self):
        self.buf = bytearray(b"\0")  # 位置 0 は空文字列
        self.index = {"": 0}

    def add(self, s):
        off = self.index.get(s)
        if off is None:
            off = len(self.buf)
            self.buf += s.encode("utf-8") + b"\0"
            self.index[s] = off
        return off


def split_csv(line):
    # mecab-naist-jdic には引用符付きの項目がない（"," は表層形に現れない）
    return line.split(",")


def parse_char_def(lines):
    cats = []   # (name, invoke, group, length)
    names = {}
    ranges = []  # (lo, hi, [cat names])
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        cols = line.split()
        if cols[0].startswith("0x"):
            if ".." in cols[0]:
                lo, hi = (int(x, 16) for x in cols[0].split(".."))
            else:
                lo = hi = int(cols[0], 16)
            ranges.append((lo, hi, cols[1:]))
        else:
            names[cols[0]] = len(cats)
            cats.append((cols[0], int(cols[1]), int(cols[2]), int(cols[3])))
    # 後の行が前の行を上書きする。重ならない区間の列にする
    points = {}
    for lo, hi, cs in ranges:
        prim = names[cs[0]]
        mask = 0
        for c in cs:
            mask |= 1 << names[c]
        for cp in range(lo, hi + 1):
            points[cp] = (prim, mask)
    flat = []
    for cp in sorted(points):
        prim, mask = points[cp]
        if flat and flat[-1][1] == cp - 1 and flat[-1][2] == prim and flat[-1][3] == mask:
            flat[-1][1] = cp
        else:
            flat.append([cp, cp, prim, mask])
    return cats, names, flat


def pos_string(cols):
    # 品詞, 細分類 1〜3, 活用型, 活用形
    cols = (cols + ["*"] * 6)[:6]
    return ",".join(cols)


def build(src, out):
    pool = Pool()
    pos_ids = {}

    def pos_id(s):
        if s not in pos_ids:
            pos_ids[s] = len(pos_ids)
        return pos_ids[s]

    # ---- 語 ----
    entries = {}
    n = 0
    for line in read_lines(os.path.join(src, "naist-jdic.csv")):
        if not line:
            continue
        c = split_csv(line)
        if len(c) < 15:
            sys.exit(f"列が足りない行: {line}")
        surface, left, right, cost = c[0], int(c[1]), int(c[2]), int(c[3])
        pos = pos_string(c[4:10])
        pron, acc, chain = c[12], c[13], c[14]
        if pron == "*":
            pron = ""
        entries.setdefault(surface, []).append((cost, left, right, pos, pron, acc, chain))
        n += 1
    print(f"語: {n}、表層形: {len(entries)}", file=sys.stderr)

    surfaces = sorted(entries, key=lambda s: s.encode("utf-8"))
    surf_tab = bytearray()
    word_tab = bytearray()
    wi = 0
    for s in surfaces:
        b = s.encode("utf-8")
        if len(b) > 0xFFFF:
            sys.exit("表層形が長すぎます")
        words = sorted(entries[s])
        surf_tab += struct.pack("<IIHH", pool.add(s), wi, len(words), len(b))
        for cost, left, right, pos, pron, acc, chain in words:
            word_tab += struct.pack("<HHhHIII", left, right, max(-32768, min(32767, cost)),
                                    pos_id(pos), pool.add(pron), pool.add(acc), pool.add(chain))
            wi += 1

    # ---- 連接表 ----
    mlines = read_lines(os.path.join(src, "matrix.def"))
    lsize, rsize = (int(x) for x in mlines[0].split())
    matrix = [0] * (lsize * rsize)
    for line in mlines[1:]:
        if not line:
            continue
        a, b, cost = line.split()
        matrix[int(a) * rsize + int(b)] = max(-32768, min(32767, int(cost)))
    mat_tab = struct.pack(f"<{len(matrix)}h", *matrix)

    # ---- 文字種・未知語 ----
    cats, cat_names, ranges = parse_char_def(read_lines(os.path.join(src, "char.def")))
    range_tab = b"".join(struct.pack("<IIHHI", lo, hi, prim, 0, mask) for lo, hi, prim, mask in ranges)
    cat_tab = b"".join(struct.pack("<BBBBI", inv, grp, ln, 0, pool.add(name)) for name, inv, grp, ln in cats)
    unk_tab = bytearray()
    n_unk = 0
    for line in read_lines(os.path.join(src, "unk.def")):
        if not line:
            continue
        c = split_csv(line)
        unk_tab += struct.pack("<HHHhHH", cat_names[c[0]], int(c[1]), int(c[2]), int(c[3]),
                               pos_id(pos_string(c[4:10])), 0)
        n_unk += 1

    pos_tab = b"".join(struct.pack("<I", pool.add(p)) for p in sorted(pos_ids, key=pos_ids.get))

    header = struct.pack("<8sIIIHHIIIII", MAGIC, VERSION, len(surfaces), wi, lsize, rsize,
                         len(ranges), len(cats), n_unk, len(pos_ids), len(pool.buf))
    header += b"\0" * (HEADER_SIZE - len(header))

    def pad4(b):
        return bytes(b) + b"\0" * (-len(b) % 4)

    with open(out, "wb") as f:
        f.write(header)
        for sec in (surf_tab, word_tab, mat_tab, range_tab, cat_tab, unk_tab, pos_tab, pool.buf):
            f.write(pad4(sec))
    print(f"書き出し: {out}（{os.path.getsize(out)} バイト、品詞 {len(pos_ids)}、文字種の区間 {len(ranges)}）",
          file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="colorful_talk.dic を作る")
    ap.add_argument("--src", default="naist-jdic", help="元データのフォルダ（既定: naist-jdic）")
    ap.add_argument("--fetch", action="store_true", help="元データを取得する")
    ap.add_argument("-o", "--out", default="colorful_talk.dic")
    a = ap.parse_args()
    if a.fetch:
        fetch(a.src)
    for name in SRC_FILES:
        if not os.path.exists(os.path.join(a.src, name)):
            sys.exit(f"{a.src}/{name} がありません（--fetch で取得できます）")
    build(a.src, a.out)


if __name__ == "__main__":
    main()
