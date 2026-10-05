#!/usr/bin/env python3
"""Splits the thumbnail/title work into waves (editors/waves/), in the order that pays off most.
Needs editors/thumbnail-priority-*.csv and editors/thumbnail-jobs.csv (scripts/thumbnail-priority.py) and data/channel-videos.tsv.
  wave-1  group A: many impressions, low CTR            -> new thumbnail (Pro model)
  wave-2  group R: big before, quiet now                -> new thumbnail + new title (Pro)
  wave-3  everything else YouTube shows right now       -> new thumbnail (Flash), most impressions first
  wave-4  group B: good CTR, few impressions            -> new title only
  wave-5  revive: timeless how-to/fix videos outside the exports, winning topics, most lifetime views first
          -> new title + thumbnail together (year in the title may be updated); top WAVE5, the rest in wave-6
  rest    everything else: optional, cheapest model, or skip
Group D (works well) is never in a wave.
"""
import collections, csv, os, re

WAVE5 = 400
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREND = re.compile(r"\bhaul\b|try[- ]?on|unboxing|\bnews\b|update \d|event|giveaway|leak|rumou?r|price drop|black friday|"
                   r"prime day|\bworth it\b|\bshould you\b|nobody|\bnever\b|honest|vs\.?\b|review\b|tested\b", re.I)
HOWTO = re.compile(r"\bhow to\b|\bfix\b|not working|\berror\b|\bproblem\b|\bsetup\b|\bset up\b|\binstall\b|\bdownload\b|"
                   r"\bdelete\b|\bchange\b|\breset\b|\bactivate\b|\blogin\b|\blog in\b|\bsign up\b|\bcreate\b|\badd\b|\bremove\b|"
                   r"\bconnect\b|\brecover\b|\bunlock\b|\benable\b|\bdisable\b", re.I)
STOP = set("how to the a an and or in on of for with your you is it this my me i do does can get without what why when from by at "
           "as are be all new 2023 2024 2025 2026 vs not use using step guide easy fast quick updated tutorial htr gg rocket glimpse "
           "that before watch first will here's here really actually way best into tips set setup make".split())


def words(t):
    w = [x for x in re.findall(r"[a-z0-9+']+", t.lower()) if x not in STOP and len(x) > 2]
    return set(w) | {a + " " + b for a, b in zip(w, w[1:])}


def main():
    pri = {}
    for ch in ("htr", "gg"):
        for r in csv.DictReader(open(os.path.join(ROOT, "editors", "thumbnail-priority-%s.csv" % ch), encoding="utf-8-sig")):
            pri[r["Video"].rsplit("/", 1)[1]] = r
    jobs = list(csv.DictReader(open(os.path.join(ROOT, "editors", "thumbnail-jobs.csv"), encoding="utf-8")))
    life_views = {}
    for line in open(os.path.join(ROOT, "data", "channel-videos.tsv"), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 5:
            life_views[p[0]] = int(p[1]) if p[1].isdigit() else 0

    # Topic strength: average 90-day views of videos sharing a word/pair, from the analysed videos.
    topic = collections.defaultdict(list)
    for vid, r in pri.items():
        imp = int(r["Impressions 90d"])
        for k in words(r["Title"]):
            topic[k].append(imp)
    strong = {k for k, v in topic.items() if len(v) >= 3 and sum(v) / len(v) >= 400}

    def imp(j): return int(pri[j["video_id"]]["Impressions 90d"]) if j["video_id"] in pri else 0
    waves = {"wave-1-A-new-thumbnail": [], "wave-2-R-thumbnail-and-title": [], "wave-3-shown-now-new-thumbnail": [],
             "wave-4-B-new-title": [], "wave-5-revive-title-and-thumbnail": [], "rest-optional": []}
    for j in jobs:
        g, vid = j["group"], j["video_id"]
        if g == "A":
            waves["wave-1-A-new-thumbnail"].append((-imp(j), j, "Shown a lot, clicked rarely: the thumbnail is the problem"))
        elif g == "R":
            waves["wave-2-R-thumbnail-and-title"].append((-int(pri[vid]["Impressions lifetime"]), j,
                                                          "Proven topic (big lifetime impressions), quiet now: refresh both"))
        elif g == "B":
            waves["wave-4-B-new-title"].append((-imp(j), j, "People click when they see it, but YouTube rarely shows it: title/search words"))
        elif imp(j) > 0:
            waves["wave-3-shown-now-new-thumbnail"].append((-imp(j), j, "YouTube shows it now: a better thumbnail turns these impressions into clicks"))
        else:
            t = j["title"]
            hits = len(words(t) & strong)
            lv = life_views.get(vid, 0)
            if HOWTO.search(t) and not TREND.search(t) and (lv >= 100 or (hits >= 2 and lv >= 20)):
                waves["wave-5-revive-title-and-thumbnail"].append((-(lv * (1.5 if hits else 1)), j,
                    "Timeless how-to/fix%s%s" % (", winning topic" if hits else "", ", %d lifetime views" % life_views.get(vid, 0))))
            else:
                waves["rest-optional"].append((-life_views.get(vid, 0), j, "Little chance: trend/opinion title or no proof of demand"))

    # Wave 5 is capped so the manual work stays focused; the next ones move to wave 6.
    w5 = sorted(waves["wave-5-revive-title-and-thumbnail"], key=lambda r: r[0])
    waves["wave-5-revive-title-and-thumbnail"], waves["wave-6-revive-later"] = w5[:WAVE5], w5[WAVE5:]
    out = os.path.join(ROOT, "editors", "waves")
    os.makedirs(out, exist_ok=True)
    for name, rows in waves.items():
        rows.sort(key=lambda r: r[0])
        with open(os.path.join(out, name + ".csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["video_id", "title", "tool", "channel", "old_thumbnail_url", "group", "impressions_90d", "lifetime_views", "why"])
            for _, j, why in rows:
                w.writerow([j["video_id"], j["title"], j["tool"], j["channel"], j["old_thumbnail_url"], j["group"],
                            imp(j), life_views.get(j["video_id"], ""), why])
        print("%-36s %5d" % (name, len(rows)))


if __name__ == "__main__":
    main()
