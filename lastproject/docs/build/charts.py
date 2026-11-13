"""Charts in the Ampera palette, driven by plan_data so every document shows the same numbers."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import plan_data as P

NAVY, MAG, LAV, TEAL, GREY, LGREY, TINT, INKS = "#002060", "#A82080", "#7870B0", "#156082", "#9AA3B5", "#D9D9D9", "#E8ECF5", "#44546A"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "charts"))
plt.rcParams.update({"font.family": ["Calibri", "DejaVu Sans"], "font.size": 10, "axes.edgecolor": "#8A93A6",
                     "axes.labelcolor": INKS, "xtick.color": INKS, "ytick.color": INKS, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.facecolor": "white"})


def _save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + ".png")
    fig.savefig(p, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def pain_points():
    rows = [("Mobile apps lag the web", 11, "out"), ("Cluttered UI, steep learning curve", 10, "yes"),
            ("Zoho apps do not sync with each other", 10, "yes"), ("Price creep, features locked to top tiers", 9, "part"),
            ("Slow or unhelpful support", 8, "no"), ("Notifications flood, or fail silently", 8, "yes"),
            ("Shallow built-in reports", 7, "no"), ("Slow pages and hangs", 6, "yes"),
            ("Leave approval friction", 6, "part"), ("Timesheet friction", 6, "part"),
            ("Roles, profiles, permission sets confusing", 5, "yes"), ("Payroll rigidity after a pay run", 4, "no")]
    col = {"yes": MAG, "part": LAV, "no": LGREY, "out": "#C9CED9"}
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ys = list(range(len(rows)))[::-1]
    ax.barh(ys, [r[1] for r in rows], color=[col[r[2]] for r in rows], height=0.68)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows])
    for y, r in zip(ys, rows):
        ax.text(r[1] + 0.15, y, str(r[1]), va="center", fontsize=9, color=NAVY, fontweight="bold")
    ax.set_xlabel("Sources raising the issue (forums, docs, review sites)")
    ax.set_xlim(0, 12.5)
    ax.legend(handles=[Rectangle((0, 0), 1, 1, color=MAG), Rectangle((0, 0), 1, 1, color=LAV), Rectangle((0, 0), 1, 1, color=LGREY), Rectangle((0, 0), 1, 1, color="#C9CED9")],
              labels=["Seen in our portal", "Partly seen", "Not visible to an Employee login", "Out of scope (no mobile)"], loc="lower right", frameon=False, fontsize=8.5)
    return _save(fig, "pain_points")


def scope_capacity():
    S = P.sums()
    fig, ax = plt.subplots(figsize=(7.2, 2.5))
    ax.barh([1], [S["m"]], color=NAVY, height=0.5)
    ax.barh([1], [S["s"]], left=[S["m"]], color=LAV, height=0.5)
    ax.barh([1], [S["c"]], left=[S["m"] + S["s"]], color=LGREY, height=0.5, hatch="///", edgecolor="#B5BBC9")
    ax.barh([0], [S["cap"]], color=TEAL, height=0.5)
    ax.axvline(S["cap"], color=MAG, ls="--", lw=1.4)
    ax.text(S["cap"] + 1, 1.42, f"capacity {S['cap']:g} pd", color=MAG, fontsize=9, fontweight="bold")
    ax.text(S["m"] / 2, 1, f"Committed {S['m']:g}", ha="center", va="center", color="white", fontsize=9.5, fontweight="bold")
    ax.text(S["m"] + S["s"] / 2, 1, f"Stretch {S['s']:g}", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
    ax.text(S["m"] + S["s"] + S["c"] / 2, 1, f"Later {S['c']:g}", ha="center", va="center", color=NAVY, fontsize=9.5, fontweight="bold")
    ax.text(S["cap"] / 2, 0, "3 people x 30 working days x 70% focus", ha="center", va="center", color="white", fontsize=9)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Available", "Planned scope"])
    ax.set_xlabel("Person-days (pd)")
    ax.set_xlim(0, S["m"] + S["s"] + S["c"] + 4)
    return _save(fig, "scope_capacity")


def module_stack():
    mods = {}
    for b in P.BACKLOG:
        mods.setdefault(b["mod"], {"M": 0, "S": 0, "C": 0})[b["tier"]] += b["est"]
    order = sorted(mods, key=lambda m: -(mods[m]["M"] * 100 + mods[m]["S"] * 10 + mods[m]["C"]))
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ys = list(range(len(order)))[::-1]
    for t, c, lab in (("M", NAVY, "Committed (Dec 24)"), ("S", LAV, "Stretch"), ("C", LGREY, "Later")):
        left = [sum(mods[m][k] for k in "MSC"[: "MSC".index(t)]) for m in order]
        ax.barh(ys, [mods[m][t] for m in order], left=left, color=c, height=0.66, label=lab,
                hatch="///" if t == "C" else None, edgecolor="#B5BBC9" if t == "C" else c)
    ax.set_yticks(ys)
    ax.set_yticklabels(order)
    ax.set_xlabel("Person-days")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3)
    return _save(fig, "module_stack")


def roadmap():
    fig, ax = plt.subplots(figsize=(7.2, 2.3))
    n = len(P.ALL_DAYS)
    for s in P.SPRINTS:
        ax.add_patch(Rectangle((s["first"], 0.2), s["last"] + 1 - s["first"], 0.6, color=[NAVY, TEAL, LAV, MAG, "#5B6B88"][s["n"] - 1], alpha=0.9))
        ax.text((s["first"] + s["last"] + 1) / 2, 0.5, f"S{s['n']}", ha="center", va="center", color="white", fontweight="bold", fontsize=11)
        ax.text((s["first"] + s["last"] + 1) / 2, 0.08, ["Foundation", "Thin slice", "Leave, approvals", "Payslips", "Release"][s["n"] - 1], ha="center", va="top", fontsize=7.5, color=INKS)
    for d, m, t in P.MILESTONES:
        x = P.IDX[d] + (1 if m != "M0" else 0)
        ax.plot([x, x], [0.8, 1.15], color=MAG, lw=1.3)
        ax.plot([x], [1.15], marker="D", color=MAG, ms=6)
        ax.text(x, 1.25, f"{m}  {d.strftime('%b')} {d.day}", ha="center", fontsize=8.5, color=NAVY, fontweight="bold")
    ax.text(n + 0.4, 0.5, "Dec 25\nholiday", ha="left", va="center", fontsize=8, color=MAG)
    ax.set_xlim(-0.3, n + 4)
    ax.set_ylim(-0.25, 1.6)
    ax.axis("off")
    return _save(fig, "roadmap")


def gantt():
    items = [b for b in P.BACKLOG if b["tier"] == "M"]
    rows = []
    for p in ("JP", "JK", "JS"):
        rows += [("hdr", p)] + [("it", b) for b in sorted([x for x in items if x["owner"] == p], key=lambda b: b["s_idx"])]
    n = len(P.ALL_DAYS)
    fig, ax = plt.subplots(figsize=(11.5, 7.2))
    ytick, ylab = [], []
    y = len(rows)
    for k, (kind, v) in enumerate(rows):
        y_ = len(rows) - k
        if kind == "hdr":
            ax.add_patch(Rectangle((0, y_ - 0.45), n, 0.9, color=TINT, zorder=0))
            ax.text(0.2, y_, f"{P.TEAM[v]['name']}  ·  {P.TEAM[v]['lane']}", va="center", fontsize=9.5, fontweight="bold", color=P.OWNER_COLOR[v])
        else:
            b = v
            ax.barh(y_, b["e_idx"] - b["s_idx"], left=b["s_idx"], height=0.56, color=P.OWNER_COLOR[b["owner"]],
                    edgecolor=MAG if b["thin"] else "none", linewidth=1.6 if b["thin"] else 0, alpha=0.95)
            ax.text(b["e_idx"] + 0.15, y_, f"{b['id']}  {b['title'][:46]}{'...' if len(b['title']) > 46 else ''}", va="center", fontsize=7.2, color=INKS)
    for s in P.SPRINTS:
        ax.axvspan(s["first"], s["last"] + 1, color="#F3F5FA" if s["n"] % 2 else "white", zorder=-2)
        ax.text((s["first"] + s["last"] + 1) / 2, len(rows) + 1.1, f"Sprint {s['n']}", ha="center", fontsize=9, fontweight="bold", color=NAVY)
    for d, m, t in P.MILESTONES[1:]:
        x = P.IDX[d] + 1
        ax.axvline(x, color=MAG, ls="--", lw=1.1, zorder=1)
        ax.text(x, -0.9, f"{m}\n{d.strftime('%b')} {d.day}", ha="center", va="top", fontsize=8, color=MAG, fontweight="bold")
    wk = [i for i, d in enumerate(P.ALL_DAYS) if d.weekday() == 0]
    ax.set_xticks(wk)
    ax.set_xticklabels([P.ALL_DAYS[i].strftime("%b %d").replace(" 0", " ") for i in wk], fontsize=8)
    ax.set_yticks([])
    ax.set_xlim(0, n + 15)
    ax.set_ylim(-0.4, len(rows) + 1.8)
    ax.spines["left"].set_visible(False)
    ax.xaxis.set_ticks_position("top")
    ax.legend(handles=[Rectangle((0, 0), 1, 1, color=P.OWNER_COLOR[p]) for p in P.TEAM] + [Rectangle((0, 0), 1, 1, fill=False, edgecolor=MAG, lw=1.6)],
              labels=[P.TEAM[p]["name"] for p in P.TEAM] + ["In the Dec 1 slice"], loc="upper center", bbox_to_anchor=(0.5, -0.06), frameon=False, fontsize=8.5, ncol=4)
    return _save(fig, "gantt")


def sprint_capacity():
    mx = P.load_matrix()
    cap = [s["cap"] * 3 for s in P.SPRINTS]
    com = [sum(mx[p][i] for p in P.TEAM) for i in range(len(P.SPRINTS))]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    x = range(len(P.SPRINTS))
    ax.bar([i - 0.2 for i in x], cap, 0.38, color=TEAL, label="Capacity (3 people, 70% focus)")
    ax.bar([i + 0.2 for i in x], com, 0.38, color=NAVY, label="Committed")
    for i in x:
        ax.text(i - 0.2, cap[i] + 0.3, f"{cap[i]:g}", ha="center", fontsize=8.5, color=INKS)
        ax.text(i + 0.2, com[i] + 0.3, f"{com[i]:.1f}", ha="center", fontsize=8.5, color=NAVY, fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"S{s['n']}\n{['Foundation', 'Thin slice', 'Leave, approvals', 'Payslips', 'Release'][s['n'] - 1]}\n{len(s['days'])} days" for s in P.SPRINTS], fontsize=8)
    ax.set_ylabel("Person-days")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_ylim(0, max(cap) + 4)
    return _save(fig, "sprint_capacity")


def util_heatmap():
    mx = P.load_matrix()
    names = [P.TEAM[p]["name"] for p in P.TEAM]
    fig, ax = plt.subplots(figsize=(7.2, 2.3))
    for r, p in enumerate(P.TEAM):
        for c, s in enumerate(P.SPRINTS):
            u = mx[p][c] / s["cap"]
            ax.add_patch(Rectangle((c, 2 - r), 0.96, 0.92, color=plt.cm.Blues(0.15 + 0.7 * min(u, 1.1) / 1.1) if u <= 1.02 else MAG))
            ax.text(c + 0.48, 2 - r + 0.46, f"{mx[p][c]:.1f} / {s['cap']:.1f}\n{u * 100:.0f}%", ha="center", va="center", fontsize=8.5,
                    color="white" if u > 0.62 else NAVY, fontweight="bold")
    ax.set_xlim(0, 5)
    ax.set_ylim(0, 3)
    ax.set_xticks([c + 0.48 for c in range(5)])
    ax.set_xticklabels([f"S{s['n']}" for s in P.SPRINTS], fontsize=9)
    ax.set_yticks([2.46, 1.46, 0.46])
    ax.set_yticklabels(names)
    ax.xaxis.set_ticks_position("top")
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
    return _save(fig, "util_heatmap")


def burnup():
    n = len(P.ALL_DAYS)
    items = [b for b in P.BACKLOG if b["tier"] == "M"]
    cum, cumthin = [], []
    for d in range(n):
        tot = tin = 0.0
        for b in items:
            f = max(0.0, min(1.0, (d + 1 - b["s_idx"]) / (b["e_idx"] - b["s_idx"])))
            tot += b["est"] * f
            tin += b["est"] * f if b["thin"] else 0
        cum.append(tot)
        cumthin.append(tin)
    S = P.sums()
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.plot(range(1, n + 1), cum, color=NAVY, lw=2.2, label="Planned cumulative (committed)")
    ax.plot(range(1, n + 1), [2.1 * (d + 1) for d in range(n)], color=TEAL, lw=1.6, ls="--", label="Capacity (2.1 pd per day)")
    ax.axhline(S["m"], color=GREY, lw=1)
    ax.text(1, S["m"] + 0.8, f"committed scope {S['m']:g} pd", fontsize=8.5, color=INKS)
    x1 = P.IDX[P.DEC1] + 1
    ax.axvline(x1, color=MAG, ls=":", lw=1.4)
    ax.text(x1 + 0.2, 4, f"Dec 1 slice: {cumthin[x1 - 1]:.1f} pd", color=MAG, fontsize=9, fontweight="bold")
    ax.set_xlabel("Working day from Nov 13")
    ax.set_ylabel("Person-days")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_xlim(1, n)
    return _save(fig, "burnup")


RISKS = [("R1", "Capacity is tight: committed scope is 91% of focus capacity", 3, 3),
         ("R2", "Entra ID app registration or admin consent is delayed", 2, 3),
         ("R3", "Hosting target is not decided, so deployment work slips", 2, 3),
         ("R4", "One owner per module: a single absence blocks that module", 2, 2),
         ("R5", "Scope creep from stretch and later items", 2, 2),
         ("R6", "Admin-side Zoho behaviour is unknown (Employee login only)", 2, 2),
         ("R7", "Payslip PDFs hold sensitive data; handling rules unclear", 1, 3),
         ("R8", "Dec 1 slice has 4% slack, so one slip moves approvals", 3, 2)]


def risk_map():
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    shade = {1: "#EEF0F6", 2: "#D8D3EA", 3: "#EBC9E1", 4: "#E2A6D0", 6: "#D77DB9", 9: MAG}
    for L in (1, 2, 3):
        for I in (1, 2, 3):
            ax.add_patch(Rectangle((I - 1, L - 1), 1, 1, color=shade[L * I], ec="white", lw=2))
    place = {}
    for rid, _, L, I in RISKS:
        k = place.get((L, I), 0)
        place[(L, I)] = k + 1
        ax.text(I - 0.5 + (k % 2) * 0.28 - 0.14, L - 0.5 + (k // 2) * 0.28 - 0.0, rid, ha="center", va="center", fontsize=9.5, fontweight="bold",
                color="white" if L * I >= 6 else NAVY)
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 3)
    ax.set_xticks([0.5, 1.5, 2.5])
    ax.set_xticklabels(["Low", "Medium", "High"])
    ax.set_yticks([0.5, 1.5, 2.5])
    ax.set_yticklabels(["Low", "Medium", "High"])
    ax.set_xlabel("Impact")
    ax.set_ylabel("Likelihood")
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    return _save(fig, "risk_map")


def feature_matrix():
    feats = ["Timer", "Calendar-style time logging", "Missing-time reminders", "Visible approval trail", "Leave feeds the timesheet",
             "Planned vs actual hours", "Client portal", "AI-drafted timesheet"]
    tools = ["Zoho", "Odoo", "OpenProject", "Plane", "WorkHub plan"]
    Y, H, N = "y", "h", "n"
    data = [[Y, Y, Y, H, Y], [Y, N, Y, N, N], [N, Y, Y, N, N], [H, Y, Y, N, N], [H, Y, N, Y, N], [N, Y, N, N, N], [N, H, N, N, N], [N, Y, N, H, N]]
    wh = ["stretch", "stretch", "stretch", "Dec 24", "Dec 24", "parked", "later", "later"]
    data = [[Y, Y, N, "stretch"], [Y, N, Y, "stretch"], [H, Y, Y, "stretch"], [H, Y, H, "Dec 24"], [N, Y, N, "Dec 24"], [N, Y, H, "parked"], [H, Y, N, "later"], [N, Y, N, "later"]]
    zoho = ["y", "y", "h", "h", "n", "n", "h", "n"]
    odoo = ["y", "n", "y", "y", "y", "y", "y", "y"]
    openp = ["y", "y", "n", "h", "n", "h", "n", "n"]
    plane = ["h", "n", "n", "y", "n", "n", "n", "h"]
    cols = [zoho, odoo, openp, plane]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for r, f in enumerate(feats):
        yy = len(feats) - 1 - r
        ax.text(-0.15, yy, f, ha="right", va="center", fontsize=9, color=INKS)
        for c, col in enumerate(cols):
            s = col[r]
            ax.add_patch(Circle((c + 0.5, yy), 0.2, fc=NAVY if s == "y" else (LAV if s == "h" else "white"), ec=NAVY if s != "n" else "#B5BBC9", lw=1.2))
        ax.add_patch(Rectangle((4.05, yy - 0.28), 0.9, 0.56, fc=TINT, ec="none"))
        ax.text(4.5, yy, wh[r], ha="center", va="center", fontsize=8.5, color=MAG, fontweight="bold")
    for c, t in enumerate(tools):
        ax.text(c + 0.5 if c < 4 else 4.5, len(feats) - 0.15, t, ha="center", va="bottom", fontsize=9.5, fontweight="bold", color=NAVY if c < 4 else MAG)
    ax.set_xlim(-3.6, 5.1)
    ax.set_ylim(-0.7, len(feats) + 0.3)
    ax.axis("off")
    ax.legend(handles=[Circle((0, 0), fc=NAVY, ec=NAVY), Circle((0, 0), fc=LAV, ec=NAVY), Circle((0, 0), fc="white", ec="#B5BBC9")],
              labels=["Found in our research", "Partly (paid tier, admin-configured or hidden)", "Not found in our research"],
              loc="lower center", ncol=3, frameon=False, fontsize=7.8, bbox_to_anchor=(0.35, -0.08))
    return _save(fig, "feature_matrix")


def stacked(name, cats, series, colors, xlabel, figsize=(7.2, 3.6), horizontal=True):
    """Generic stacked bars: series = [(label, [values per cat])]."""
    fig, ax = plt.subplots(figsize=figsize)
    ys = list(range(len(cats)))[::-1]
    left = [0] * len(cats)
    for (lab, vals), c in zip(series, colors):
        ax.barh(ys, vals, left=left, color=c, height=0.66, label=lab)
        left = [a + b for a, b in zip(left, vals)]
    for y, t in zip(ys, left):
        ax.text(t + 0.15, y, f"{t:g}", va="center", fontsize=8.5, color=NAVY, fontweight="bold")
    ax.set_yticks(ys)
    ax.set_yticklabels(cats)
    ax.set_xlabel(xlabel)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    return _save(fig, name)


def budget_bar(name, parts, total_label):
    """One horizontal budget bar split into labelled parts: parts = [(label, ms, color)]."""
    fig, ax = plt.subplots(figsize=(7.2, 1.7))
    left = 0
    for lab, v, c in parts:
        ax.barh([0], [v], left=[left], color=c, height=0.55)
        ax.text(left + v / 2, 0, f"{lab}\n{v} ms", ha="center", va="center", fontsize=8, color="white" if c != LGREY else NAVY, fontweight="bold")
        left += v
    ax.text(left, 0.45, total_label, ha="right", fontsize=9, color=MAG, fontweight="bold")
    ax.set_xlim(0, left)
    ax.set_ylim(-0.5, 0.8)
    ax.axis("off")
    return _save(fig, name)


ALL = [pain_points, scope_capacity, module_stack, roadmap, gantt, sprint_capacity, util_heatmap, burnup, risk_map, feature_matrix]

if __name__ == "__main__":
    for f in ALL:
        print(f.__name__, os.path.basename(f()))
