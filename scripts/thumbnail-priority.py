#!/usr/bin/env python3
"""Sorts videos into groups A-D from YouTube Studio exports, so editors fix the right thumbnails and titles first.

Input:  data/studio/<CH>-90days.csv and <CH>-lifetime.csv ("Table data.csv" from Studio > Analytics > Advanced mode >
        Content, sorted by Thumbnail impressions, with Thumbnail impressions + Thumbnail click-through rate columns).
        These files are private (revenue) and git-ignored.
Output: editors/thumbnail-priority-<ch>.csv  every analysed video with its group and what to do
        editors/thumbnail-jobs.csv           input for the thumbnail tool (groups A, R, B first, then C)
Groups (from the last 90 days, only videos with >= MIN_IMP impressions, compared with the channel's median CTR):
  A  many impressions, CTR clearly below median  -> new thumbnail first (sorted by clicks we miss)
  B  CTR above median, few impressions           -> new title (search words); keep the thumbnail
  D  CTR fine                                    -> don't touch
  R  big in lifetime, (almost) no impressions now -> proven topic: new thumbnail + title ("revive")
  C  everything else (little data)               -> bulk new thumbnail, no manual work
Old music uploads (DJ remix etc.) and Shorts are left out.
"""
import csv, importlib.util, os, re, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_IMP = 1000
CHANNELS = {"HTR": "How To Rocket", "GG": "Guide Glimpse"}
MUSIC = re.compile(r"\bdj\b|remix|\bsong\b|bass mix|\blagu\b|joget|[ऀ-ॿ]|[\U0001D400-\U0001D7FF]", re.I)

spec = importlib.util.spec_from_file_location("lists", os.path.join(ROOT, "scripts", "build-editor-lists.py"))
lists = importlib.util.module_from_spec(spec); spec.loader.exec_module(lists)


def load(name):
    path = os.path.join(ROOT, "data", "studio", name + ".csv")
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8-sig")) if r.get("Content") and r["Content"] != "Total"]
    out = {}
    for r in rows:
        if not r.get("Video publish time"):
            continue
        imp = float(r.get("Thumbnail impressions") or 0)
        ctr = float(r.get("Thumbnail click-through rate (%)") or 0)
        out[r["Content"]] = {"title": r["Video title"], "dur": int(r["Duration"] or 0), "imp": imp, "ctr": ctr,
                             "views": float(r.get("Views") or 0), "published": r["Video publish time"]}
    return out


def tool_of(lines_for, title):
    kind, lines = lines_for(title)
    m = re.match(r"👉 Try (.+?) \(affiliate\)", lines[0]) if kind == "tool" else None
    return m.group(1) if m else ""


def main():
    lines_for = lists.make_matcher(lists.load_tools())
    jobs, known = [], set()
    for ch, cname in CHANNELS.items():
        recent, life = load(ch + "-90days"), load(ch + "-lifetime")
        ids = set(recent) | set(life)
        known |= ids   # includes group D, which stays out of the jobs
        vids = {}
        for vid in ids:
            v = dict(life.get(vid) or recent[vid])
            if MUSIC.search(v["title"]) or 0 < v["dur"] <= 60:
                continue
            r, l = recent.get(vid, {}), life.get(vid, {})
            vids[vid] = {"title": v["title"], "published": v["published"], "imp90": r.get("imp", 0), "ctr90": r.get("ctr", 0),
                         "views90": r.get("views", 0), "impL": l.get("imp", 0), "ctrL": l.get("ctr", 0)}
        enough = [v for v in vids.values() if v["imp90"] >= MIN_IMP]
        med_ctr = statistics.median(v["ctr90"] for v in enough)
        med_imp = statistics.median(v["imp90"] for v in enough)
        life_top = sorted((v["impL"] for v in vids.values()), reverse=True)
        life_cut = life_top[min(len(life_top) - 1, 150)] if life_top else 0

        rows = []
        for vid, v in vids.items():
            missed = 0
            if v["imp90"] >= MIN_IMP:
                if v["ctr90"] < 0.75 * med_ctr:
                    g, todo = "A", "New thumbnail first"
                    missed = v["imp90"] * (med_ctr - v["ctr90"]) / 100
                elif v["ctr90"] >= 1.25 * med_ctr and v["imp90"] < med_imp:
                    g, todo = "B", "New title (search words); keep thumbnail"
                else:
                    g, todo = "D", "Don't touch (description links only)"
            elif v["impL"] >= life_cut and v["impL"] > 0:
                g, todo = "R", "Proven topic, now quiet: new thumbnail + title"
            else:
                g, todo = "C", "Bulk new thumbnail (no manual work)"
            rows.append((g, missed, vid, v, todo))
        order = {"A": 0, "R": 1, "B": 2, "D": 3, "C": 4}
        rows.sort(key=lambda r: (order[r[0]], -r[1], -r[3]["imp90"], -r[3]["impL"]))

        out = os.path.join(ROOT, "editors", "thumbnail-priority-%s.csv" % ch.lower())
        with open(out, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Group", "What to do", "Video", "Title", "Tool", "Impressions 90d", "CTR 90d %",
                        "Missed clicks 90d", "Impressions lifetime", "CTR lifetime %", "Published"])
            for g, missed, vid, v, todo in rows:
                w.writerow([g, todo, "https://youtu.be/" + vid, v["title"], tool_of(lines_for, v["title"]), int(v["imp90"]),
                            v["ctr90"], int(missed), int(v["impL"]), v["ctrL"], v["published"]])
        for g, missed, vid, v, todo in rows:
            if g != "D":
                jobs.append((order[g], -missed, vid, v["title"], tool_of(lines_for, v["title"]), cname, g))
        count = {k: sum(1 for r in rows if r[0] == k) for k in "ARBDC"}
        print("%s: median CTR %.1f%%, groups %s, missed clicks in A (90 days): %d"
              % (ch, med_ctr, count, sum(r[1] for r in rows if r[0] == "A")))

    # Videos missing from the Studio exports (too few impressions) are group C too, so nothing is left out.
    listed = {j[2] for j in jobs} | known
    for line in open(os.path.join(ROOT, "data", "channel-videos.tsv"), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 5 or p[0] in listed or p[4] not in CHANNELS.values() or MUSIC.search(p[3]):
            continue
        try:
            if 0 < float(p[2]) <= 60:
                continue
        except ValueError:
            pass
        listed.add(p[0])
        jobs.append((order["C"], 0, p[0], p[3], tool_of(lines_for, p[3]), p[4], "C"))
    jobs.sort()
    with open(os.path.join(ROOT, "editors", "thumbnail-jobs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["video_id", "title", "tool", "channel", "old_thumbnail_url", "group"])
        for _, _, vid, title, tool, cname, g in jobs:
            w.writerow([vid, title, tool, cname, "https://i.ytimg.com/vi/%s/maxresdefault.jpg" % vid, g])


if __name__ == "__main__":
    main()
