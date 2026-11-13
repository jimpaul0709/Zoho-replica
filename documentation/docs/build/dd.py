"""Diagram generator following the diagram-design skill rules, in the Ampera skin.
Orthogonal rounded connectors, masked arrow labels (<=14 chars), 4px grid, accessible SVG, geometry check."""
import html
import os
import subprocess
import tempfile

PAPER, INK, MUTED, SOFT, ACCENT, LINK = "#F5F6FA", "#002060", "#44546A", "#5B6B88", "#A82080", "#2E5597"
SANS = "Calibri, Arial, sans-serif"
MONO = "Consolas, 'Courier New', monospace"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def ink(a):
    return f"rgba(0,32,96,{a})"


KINDS = {  # fill, stroke, dash
    "focal": ("rgba(168,32,128,0.08)", ACCENT, None),
    "backend": ("#FFFFFF", INK, None),
    "store": (ink(.05), MUTED, None),
    "external": (ink(.03), ink(.30), None),
    "input": ("rgba(68,84,106,0.10)", SOFT, None),
    "optional": (ink(.02), ink(.20), "4,3"),
    "security": ("rgba(168,32,128,0.05)", "rgba(168,32,128,0.5)", "4,4"),
}


def esc(t):
    return html.escape(str(t), quote=False)


def rpath(pts, r=8):
    d = f"M{pts[0][0]},{pts[0][1]}"
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
        l1, l2 = abs(x1 - x0) + abs(y1 - y0), abs(x2 - x1) + abs(y2 - y1)
        rr = min(r, l1 / 2, l2 / 2)
        u1 = ((x1 - x0) / l1, (y1 - y0) / l1) if l1 else (0, 0)
        u2 = ((x2 - x1) / l2, (y2 - y1) / l2) if l2 else (0, 0)
        d += f" L{x1 - u1[0] * rr:g},{y1 - u1[1] * rr:g} Q{x1},{y1} {x1 + u2[0] * rr:g},{y1 + u2[1] * rr:g}"
    return d + f" L{pts[-1][0]},{pts[-1][1]}"


class D:
    def __init__(self, slug, title, desc, w=880, h=560, eyebrow="Diagram"):
        self.slug, self.title, self.desc, self.W, self.H, self.eyebrow = slug, title, desc, w, h, eyebrow
        self.zones, self.edges, self.nodes, self.over = [], [], [], []
        self.N, self.masks, self.segs = {}, [], []

    # ----- primitives -----
    def zone(self, x, y, w, h, label, dashed=True):
        lw = len(label) * 5.4 + 14
        self.zones.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{ink(.025)}" stroke="{ink(.22)}" stroke-width="0.8"'
            + (' stroke-dasharray="4,4"' if dashed else "") + "/>"
            f'<rect x="{x + 8}" y="{y + 4}" width="{lw:g}" height="12" rx="2" fill="{PAPER}"/>'
            f'<text x="{x + 8 + lw / 2:g}" y="{y + 13}" fill="{SOFT}" font-size="7" font-family="{MONO}" text-anchor="middle" letter-spacing="0.14em">{esc(label.upper())}</text>')

    def node(self, id, x, y, w, h, name, sub=None, kind="backend", tag=None, badge=None, chip=None, shape="box", rx=6):
        self.N[id] = (x, y, w, h)
        fill, stroke, dash = KINDS[kind]
        dd = f' stroke-dasharray="{dash}"' if dash else ""
        if shape == "diamond":
            cx, cy = x + w / 2, y + h / 2
            pts = f"{cx:g},{y} {x + w},{cy:g} {cx:g},{y + h} {x},{cy:g}"
            s = [f'<polygon points="{pts}" fill="{PAPER}"/>',
                 f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="1"{dd}/>']
        else:
            rr = h // 2 if shape == "pill" else rx
            s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rr}" fill="{PAPER}"/>',
                 f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rr}" fill="{fill}" stroke="{stroke}" stroke-width="1"{dd}/>']
        top = y
        tcol = ACCENT if kind == "focal" else SOFT
        if tag:
            tw = len(tag) * 5.2 + 10
            s.append(f'<rect x="{x + 8}" y="{y + 6}" width="{tw:g}" height="12" rx="2" fill="transparent" stroke="{tcol}" stroke-opacity="0.55" stroke-width="0.8"/>'
                     f'<text x="{x + 8 + tw / 2:g}" y="{y + 15}" fill="{tcol}" font-size="7" font-family="{MONO}" text-anchor="middle" letter-spacing="0.08em">{esc(tag)}</text>')
            top = y + 18
        if badge:
            bw = len(badge) * 5.2 + 10
            s.append(f'<rect x="{x + w - bw - 8:g}" y="{y + 6}" width="{bw:g}" height="12" rx="2" fill="transparent" stroke="{SOFT}" stroke-opacity="0.55" stroke-width="0.8"/>'
                     f'<text x="{x + w - bw / 2 - 8:g}" y="{y + 15}" fill="{SOFT}" font-size="7" font-family="{MONO}" text-anchor="middle">{esc(badge)}</text>')
        names = name.split("\n")
        subs = [] if sub is None else (sub if isinstance(sub, list) else [sub])
        block = 14 * len(names) + 12 * len(subs) + (30 if chip else 0)
        ty = top + ((y + h) - top - block) / 2
        for i, n in enumerate(names):
            s.append(f'<text x="{x + w / 2:g}" y="{ty + 11 + 14 * i:g}" fill="{INK}" font-size="12" font-weight="700" font-family="{SANS}" text-anchor="middle">{esc(n)}</text>')
        by = ty + 14 * len(names)
        for i, t in enumerate(subs):
            s.append(f'<text x="{x + w / 2:g}" y="{by + 9 + 12 * i:g}" fill="{MUTED}" font-size="9" font-family="{MONO}" text-anchor="middle">{esc(t)}</text>')
        if chip:
            cy = by + 12 * len(subs) + 4
            s.append(f'<rect x="{x + 10}" y="{cy:g}" width="{w - 20}" height="24" rx="4" fill="{ink(.05)}" stroke="{MUTED}" stroke-width="0.8"/>'
                     f'<text x="{x + 18}" y="{cy + 15.5:g}" fill="{INK}" font-size="11" font-weight="700" font-family="{SANS}">{esc(chip[0])}</text>'
                     f'<text x="{x + w - 18}" y="{cy + 15.5:g}" fill="{MUTED}" font-size="9" font-family="{MONO}" text-anchor="end">{esc(chip[1])}</text>')
        self.nodes.append("".join(s))

    def dot(self, x, y, end=False):
        if end:
            self.nodes.append(f'<circle cx="{x}" cy="{y}" r="8" fill="none" stroke="{INK}" stroke-width="1.2"/><circle cx="{x}" cy="{y}" r="5" fill="{INK}"/>')
        else:
            self.nodes.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{INK}"/>')
        self.N[f"dot{x}_{y}"] = (x - 6, y - 6, 12, 12)

    def label_mask(self, cx, cy, text, w=None):
        w = w or len(text) * 5.2 + 12
        self.masks.append((cx - w / 2, cy - 6, w, 12))
        return (f'<rect x="{cx - w / 2:g}" y="{cy - 6:g}" width="{w:g}" height="12" rx="2" fill="{PAPER}"/>'
                f'<text x="{cx:g}" y="{cy + 3:g}" fill="{SOFT}" font-size="8" font-family="{MONO}" text-anchor="middle" letter-spacing="0.06em">{esc(text)}</text>')

    def edge(self, pts=None, label=None, seg=0, side="above", kind="default", dashed=False, d=None, at=None, r=8, marker="arrow"):
        col = {"default": MUTED, "accent": ACCENT, "link": LINK}[kind]
        mk = {"default": "arrow", "accent": "arrow-accent", "link": "arrow-link"}[kind]
        if marker == "open":
            mk = "arrow-open"
        path = d or rpath(pts, r)
        s = (f'<path d="{path}" fill="none" stroke="{col}" stroke-width="{1 if dashed else 1.2}"'
             + (' stroke-dasharray="5,4"' if dashed else "") + (f' marker-end="url(#{self.slug}-{mk})"' if marker else "") + "/>")
        if pts:
            for a, b in zip(pts, pts[1:]):
                self.segs.append((a, b))
        if label:
            if at:
                cx, cy = at
            else:
                (x0, y0), (x1, y1) = pts[seg], pts[seg + 1]
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                w = len(label) * 5.2 + 12
                if y0 == y1:
                    cx, cy = mx, my + (-14 if side == "above" else 14)
                else:
                    cx, cy = mx + (w / 2 + 8) * (1 if side == "right" else -1), my
            s += self.label_mask(cx, cy, label)
        self.edges.append(s)

    def legend(self, items):
        y = self.H - 36
        s = [f'<line x1="40" y1="{y - 12}" x2="{self.W - 40}" y2="{y - 12}" stroke="{ink(.10)}" stroke-width="0.8"/>',
             f'<text x="40" y="{y + 4}" fill="{MUTED}" font-size="8" font-family="{MONO}" letter-spacing="0.14em">LEGEND</text>']
        x = 104
        for kind, k, text in items:
            if kind == "box":
                f, st, dash = KINDS[k]
                s.append(f'<rect x="{x}" y="{y - 4}" width="20" height="12" rx="3" fill="{f}" stroke="{st}" stroke-width="1"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")
                s.append(f'<text x="{x + 28}" y="{y + 5}" fill="{MUTED}" font-size="9" font-family="{MONO}">{esc(text)}</text>')
            else:
                col = {"default": MUTED, "accent": ACCENT, "link": LINK}[k.replace("-d", "")]
                s.append(f'<line x1="{x}" y1="{y + 2}" x2="{x + 24}" y2="{y + 2}" stroke="{col}" stroke-width="1.2"' + (' stroke-dasharray="5,4"' if k.endswith("-d") else "") + "/>")
                s.append(f'<text x="{x + 32}" y="{y + 5}" fill="{MUTED}" font-size="9" font-family="{MONO}">{esc(text)}</text>')
            x += 44 + len(text) * 5.6 + 24
        self.over.append("".join(s))

    # ----- output -----
    def svg(self):
        sl = self.slug
        mk = "".join(f'<marker id="{sl}-{n}" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{c}"/></marker>'
                     for n, c in (("arrow", MUTED), ("arrow-accent", ACCENT), ("arrow-link", LINK)))
        mk += f'<marker id="{sl}-arrow-open" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polyline points="0 0, 8 3, 0 6" fill="none" stroke="{MUTED}" stroke-width="1.2"/></marker>'
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" role="img" aria-labelledby="{sl}-title {sl}-desc" font-family="{SANS}">'
                f'<title id="{sl}-title">{esc(self.title)}</title><desc id="{sl}-desc">{esc(self.desc)}</desc><defs>{mk}</defs>'
                f'<rect width="100%" height="100%" fill="{PAPER}"/>' + "".join(self.zones) + "".join(self.edges) + "".join(self.nodes) + "".join(self.over) + "</svg>")

    def page(self):
        return (f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{esc(self.title)}</title>'
                f'<style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:{SANS};background:{PAPER};color:{INK};padding:3rem 2rem}}'
                f'.frame{{max-width:1200px;margin:0 auto}}.diagram-container{{width:100%;overflow-x:auto}}'
                f'.eyebrow{{font-family:{MONO};font-size:.66rem;letter-spacing:.18em;text-transform:uppercase;color:{MUTED};margin-bottom:.5rem}}'
                f'h1{{font-size:1.75rem;font-weight:400;letter-spacing:-.01em;margin-bottom:1.5rem}}svg{{width:100%;min-width:{self.W}px;display:block}}'
                f'@media print{{.diagram-container{{overflow-x:visible}}svg{{min-width:0}}}}</style></head><body><div class="frame">'
                f'<p class="eyebrow">{esc(self.eyebrow)} · WorkHub · Ampera Technologies</p><h1>{esc(self.title)}</h1><div class="diagram-container">{self.svg()}</div></div></body></html>')

    def check(self):
        w = []
        for (a, b) in self.segs:
            if a[0] != b[0] and a[1] != b[1]:
                w.append(f"diagonal segment {a}->{b}")
        ids = list(self.N.items())
        for m, (mx, my, mw, mh) in enumerate(self.masks):
            for k, (x, y, ww, hh) in ids:
                if mx < x + ww and mx + mw > x and my < y + hh and my + mh > y:
                    w.append(f"label mask {m} overlaps node {k}")
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                (k1, (x1, y1, w1, h1)), (k2, (x2, y2, w2, h2)) = ids[i], ids[j]
                if x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2:
                    w.append(f"nodes overlap {k1}/{k2}")
        for k, (x, y, ww, hh) in ids:
            if x < 8 or y < 8 or x + ww > self.W - 8 or y + hh > self.H - 8:
                w.append(f"node {k} outside canvas")
        return w

    def save(self, outdir):
        os.makedirs(outdir, exist_ok=True)
        open(os.path.join(outdir, self.slug + ".html"), "w", encoding="utf-8").write(self.page())
        tmp = os.path.join(tempfile.gettempdir(), self.slug + "_png.html")
        open(tmp, "w", encoding="utf-8").write(
            f'<!DOCTYPE html><html><head><meta charset="UTF-8"><style>*{{margin:0;padding:0}}body{{background:{PAPER}}}svg{{display:block;width:{self.W}px;height:{self.H}px}}</style></head><body>{self.svg()}</body></html>')
        png = os.path.abspath(os.path.join(outdir, self.slug + ".png"))
        if os.path.exists(png):
            os.remove(png)
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                        f"--window-size={self.W},{self.H + 120}", "--virtual-time-budget=1500", f"--screenshot={png}",
                        "file:///" + tmp.replace("\\", "/")], capture_output=True, timeout=90)
        from PIL import Image
        im = Image.open(png)
        im.crop((0, 0, self.W * 2, self.H * 2)).save(png)
        return png
