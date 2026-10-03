#!/usr/bin/env python3
"""Builds guidelines.html from the guidelines PDF text plus the FAQ below.

Run from the site folder:  python3 tools/build_guidelines.py
Needs `pdftotext` (poppler). The PDF text is reproduced as printed, typos included.
"""
import html, re, subprocess, sys, os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = "docs/Architectural-Guidelines-Rules-and-Regulations-2016.pdf"
PDF_OFFSET = 3  # PDF page number = printed page number + 3 (cover and three contents pages)

text = subprocess.run(["pdftotext", "-layout", os.path.join(ROOT, PDF), "-"], capture_output=True, text=True, check=True).stdout.replace("\f", "\n")
lines = text.split("\n")

# ---- find the body (second "I. INTRODUCTION", the one without dot leaders) ----
start = next(i for i, l in enumerate(lines) if re.match(r"^\s*I\.\s+INTRODUCTION\s*$", l))
body = lines[start:]

# ---- blocks: articles and numbered sections; track the printed page each starts on ----
art_re = re.compile(r"^\s*(I{1,3})\.\s+(.+?)\s*$")
sec_re = re.compile(r"^\s*([123]\.\d{1,3})\s{2,}(\S.*)$")
page_re = re.compile(r"^\s*-\s*(\d+)\s*-\s*$")

blocks = []  # dict(kind, id, num, title, lines, page)
cur = None
pending_page_blocks = []  # blocks whose start page is not yet known
for raw in body:
    m = page_re.match(raw)
    if m:
        for b in pending_page_blocks:
            b["page"] = int(m.group(1))
        pending_page_blocks = []
        if cur is not None:
            cur["lines"].append("\x00PAGE")  # page break marker inside the block
        continue
    a = art_re.match(raw)
    s = sec_re.match(raw)
    if a and not s and a.group(1) in ("I", "II", "III"):
        cur = {"kind": "article", "num": a.group(1), "title": a.group(2).strip(), "lines": [], "page": None}
        blocks.append(cur); pending_page_blocks.append(cur); continue
    if s:
        cur = {"kind": "section", "num": s.group(1), "title": None, "head": s.group(2).strip(), "lines": [], "page": None}
        blocks.append(cur); pending_page_blocks.append(cur); continue
    if cur is not None:
        cur["lines"].append(raw)

# ---- split each section heading into title and an inline remainder ----
def split_head(head):
    head = re.sub(r"\s{2,}", " ", head)
    m = re.match(r"^(.*?)\.\s+(See\b.*|Approval is required\.|Not permitted\.|Will not be permitted\.)$", head)
    if m: return m.group(1).strip(), m.group(2).strip()
    return head.rstrip(".").strip(), ""
for b in blocks:
    if b["kind"] == "section":
        t, rest = split_head(b["head"])
        b["title"] = t
        if rest: b["lines"].insert(0, rest)
sections = {b["num"]: b for b in blocks if b["kind"] == "section"}
slug = lambda n: "s" + n.replace(".", "-")
by_title = {re.sub(r"[^a-z]", "", b["title"].lower()): b for b in sections.values()}

# ---- paragraphs / lists ----
item_re = re.compile(r"^\(?([a-z]|[A-C])\)\s+(.*)$")
def esc(s): return html.escape(s, quote=False)
def linkify_see(t):
    m = re.match(r"^See\s+(.+?)\.?$", t)
    if m:
        key = re.sub(r"[^a-z]", "", m.group(1).lower())
        tgt = by_title.get(key)
        if tgt: return f'See <a href="#{slug(tgt["num"])}">{esc(m.group(1))}</a> ({tgt["num"]}).'
    return esc(t)

def join(parts):
    out = ""
    for p in parts:
        p = p.strip()
        if not p: continue
        if out.endswith("-") and re.match(r"^[a-z]", p): out += p
        else: out = (out + " " + p).strip()
    return re.sub(r"\s{2,}", " ", out)

def render_block(b):
    if b["num"] == "2.15": return setbacks_table(b)
    ls = [re.sub(r"^\s{0,}", lambda m: m.group(0), l) for l in b["lines"]]
    # re-join paragraphs that a page break (with a blank line before it) split mid-sentence
    cleaned = []
    i = 0
    while i < len(ls):
        l = ls[i]
        if l == "\x00PAGE":
            # drop trailing blanks before the marker; continue the sentence if it is unfinished
            j = len(cleaned)
            while j > 0 and not cleaned[j - 1].strip(): j -= 1
            prev = cleaned[j - 1].strip() if j else ""
            nxt = next((x for x in ls[i + 1:] if x.strip() and x != "\x00PAGE"), "")
            if prev and not re.search(r"[.:;)”\"]$", prev) and nxt and not item_re.match(nxt.strip()) and not sec_re.match(nxt):
                del cleaned[j:]
                i += 1
                while i < len(ls) and not ls[i].strip(): i += 1
                continue
            i += 1; continue
        cleaned.append(l); i += 1
    out, para, items, itemtype = [], [], [], None
    def flush_para():
        nonlocal para
        t = join(para)
        if t: out.append("<p>" + (linkify_see(t) if t.startswith("See ") else esc(t)) + "</p>")
        para = []
    def flush_items():
        nonlocal items, itemtype
        if items:
            tag = "ol" if itemtype else "ul"
            out.append(f'<{tag} class="gl">' + "".join(f'<li value="{ord(m.lower())-96}"><span class="mk">({m})</span> {esc(join(t))}</li>' if itemtype == "alpha" else f"<li>{esc(join(t))}</li>" for m, t in items) + f"</{tag}>")
        items, itemtype = [], None
    open_item = None
    for l in cleaned:
        s = l.strip()
        if not s:
            open_item = None; flush_para(); continue
        m = item_re.match(s)
        if m:
            mk = m.group(1)
            last = items[-1][0] if items else None
            ok = (not items and mk in ("a", "A")) or (items and (mk == last or ord(mk) == ord(last) + 1))
            if ok:
                flush_para()
                items.append((mk, [m.group(2)])); open_item = items[-1]; itemtype = "alpha"; continue
        if open_item is not None: open_item[1].append(s); continue
        if items: flush_items()
        para.append(s)
    flush_para(); flush_items()
    return "\n".join(out)

def setbacks_table(b):
    return """<p>The minimum principal setback for each residence or Accessory Building from any public street right-of-way (excluding state highways and major county arterials), private street easement or from any other property line shall be:</p>
<div class="table-wrap"><table class="mini"><thead><tr><th></th><th class="r">Dwelling unit</th><th class="r">Accessory building</th></tr></thead><tbody>
<tr><td>Building front</td><td class="r">20 feet</td><td class="r">20 feet</td></tr>
<tr><td>Building sides</td><td class="r">7.5 feet</td><td class="r">10 feet</td></tr>
<tr><td>Building rear</td><td class="r">20 feet</td><td class="r">10 feet</td></tr></tbody></table></div>"""

# ---- FAQ ----
FAQ = [
 ("Approval and exceptions", [
  ("Do I need approval before I change something outside my home or lot?",
   "Usually, yes. The Declaration requires written approval from the Design Review Committee before improvements are started, and the guidelines say anything not listed in them also needs approval. Many everyday jobs are listed as not needing approval when you follow the rules for that item, for example repainting in the same colors or replacing landscaping plants.",
   ["1.1", "2.1", "3.1"]),
  ("What can I do without asking?",
   "Examples the guidelines say need no approval when the stated conditions are met: re-staining or repainting in substantially the same colors, replacing or adding plants that keep the lot's look or save water, repairing a driveway without expanding it, flower gardens, vegetable gardens in a side or rear yard, satellite dishes up to two and a half feet across, garage-mounted basketball backboards, solar LED lights, replacing a mailbox, holiday decorations that come down promptly, and matching screen doors or shutters.",
   ["2.66", "2.54", "2.32", "2.41", "2.42", "2.8", "2.11", "2.57", "2.58", "2.63", "2.29", "2.84"]),
  ("How do I ask for approval?",
   "Send the Committee a drawing or plan before work starts. It should be drawn to a scale of 1/4 inch to 1 foot, show your lot lines and the proposed improvement, describe the materials and colors, and include your name, address and phone number. Submit two copies with the $10 review fee. Plans sent without the fee are returned unapproved.",
   ["3.2", "3.3", "3.4"]),
  ("Where do I send my request?",
   "The 2016 guidelines give the Committee's address as the Master Association's, 6950 Pinery Parkway South, Parker, Colorado 80134. That is the address as printed in 2016, so check with the board for the current one.",
   ["1.4", "3.3"]),
  ("How long does the Committee have to answer?",
   "Forty-five days after it has received everything it asked for. If the Committee does not send a disapproval or a request for more information within those 45 days, the request is treated as approved.",
   ["3.5", "3.6"]),
  ("After approval, how long do I have to build?",
   "Work must begin within 180 days of approval or the approval becomes void and you must reapply. Work must be finished within nine months of approval unless the Committee extends the time.",
   ["3.7"]),
  ("What if my request is denied?",
   "You can appeal to the Board of Directors by written notice within 30 days of the denial, conditions or refusal. After you have used the appeal steps, you may take the decision to a court of law.",
   ["3.9", "3.10"]),
  ("Does approval mean my project meets code and is safe?",
   "No. Approval covers appearance only. You are still responsible for Douglas County permits and building codes, for locating utility lines and easements, and for any damage you cause to them. If the county's rules and these guidelines differ, the more restrictive rule applies.",
   ["3.11", "1.7", "1.8", "2.25"]),
  ("Who is on the Design Review Committee?",
   "Three members appointed by the Master Association's Board of Directors.",
   ["1.3"]),
  ("I bought my home and something on the lot does not meet the guidelines. Do I have to remove it?",
   "Not necessarily. If an earlier owner's improvement was approved in advance, or a previous owner's improvement is nonconforming, the current owner may not have to remove it or be fined, unless at the time of purchase you knew or should have known about it, for example because of a lien or pending suit.",
   ["2.62"]),
  ("What if the guidelines and the Declaration disagree?",
   "The Declaration controls. If a question comes up about what a term or rule means, the Committee's interpretation is final. The board and Committee may also add to or change the guidelines, so confirm you have the latest edition before you start a project.",
   ["1.5", "1.9"]),
 ]),
 ("Everyday rules", [
  ("Where can I park?",
   "No vehicle may be parked regularly, meaning more than three days a week, on a public street in the community. Regular parking belongs in a garage or driveway. Boats, campers, trailers, motor homes, trucks other than pickups and other large vehicles must be kept in a structure designed for them, except guests' vehicles for up to four days. The Association can have a vehicle that sits on the street for more than five days removed at the owner's expense.",
   ["2.67", "2.23", "2.61", "2.52"]),
  ("How many pets can I have, and what are the rules?",
   "Only standard household pets are allowed. No more than two adult pets that mostly use outdoor areas for exercise or waste. Pets may not run at large, and habitually barking, howling or yelping dogs count as a nuisance. Livestock, poultry, rabbits, snakes and exotic animals are prohibited.",
   ["2.71", "2.7"]),
  ("When can I put my trash out?",
   "Not more than 24 hours before the scheduled pickup. Garbage cans must otherwise be screened from view of neighbors and the street, and trash may not be allowed to accumulate on a lot.",
   ["2.102"]),
  ("Can I hang laundry outside?",
   "Temporary clotheslines or hangers in a back or side yard are acceptable if they are not left up for multiple days in a row.",
   ["2.21"]),
  ("Where can I store firewood?",
   "In the side or back yard next to the house, neatly stacked, out of the way of drainage, and screened by planting or matching building materials so it cannot be seen from neighbors, trails or streets.",
   ["2.117", "2.93"]),
  ("What are the rules for outdoor lighting?",
   "Maintaining or replacing existing fixtures needs no approval, and commercially available solar LED lighting of similar brightness is fine. Floodlights and motion-activated security lights need approval. Place lights so they do not shine into neighboring lots.",
   ["2.57"]),
  ("Can I put up a sign?",
   "For sale and for rent signs larger than six square feet are prohibited, as are billboards and poster boards or advertising structures of any kind.",
   ["2.87", "2.4", "2.5"]),
  ("Can I run a business from my home?",
   "Lots are for residential use only. No trade, business or commercial activity is allowed except a permitted business activity described in the Declaration, and nothing may become a nuisance.",
   ["2.16", "1.10"]),
  ("How must I keep up my yard?",
   "Each owner must keep the lot in first-class condition, including pruning, cutting ground cover and weeding. Removing dead trees, branches and plants is routine maintenance and needs no approval. Replacing plants with ones that keep the lot's look or reduce watering, including xeriscaping, also needs no approval, but major re-landscaping that significantly changes the lot's appearance does.",
   ["2.56", "2.54", "2.55"]),
  ("What if my home is damaged?",
   "Start repairs within 30 days, which includes contacting your insurer and contractors. A damaged shed or outbuilding that cannot be repaired must be removed within 60 days. If a home is uninhabitable or a total loss, notify the Master Association board.",
   ["2.26"]),
 ]),
 ("Building and changes", [
  ("What do I need to know before building a fence?",
   "Boundary fences may not exceed five feet and must let light pass through. Privacy fences need approval. Tell adjacent neighbors before replacing a fence. For a new boundary fence where none existed, talk to the neighbors first. If they do not object, no approval is needed, and if they do, the board or Committee decides. Plastic, chicken wire, hog wire, barbed wire, electric, chain link, wire mesh, slump block, concrete block and strand wire fences are not allowed along lot boundaries.",
   ["2.36"]),
  ("Can I add a shed or other outbuilding?",
   "It needs approval. Unless the guidelines say otherwise, the maximum size is 8 by 10 feet and 8 1/2 feet high. It must look like the house, be screened by a fence or plantings, and not unreasonably block a neighbor's view of the mountains or open areas.",
   ["2.2", "2.3"]),
  ("How far from the property lines must I build?",
   "For a house, 20 feet from the front, 7.5 feet at the sides and 20 feet at the rear. For an accessory building, 20 feet front, 10 feet at the sides and 10 feet at the rear. The county's rules also apply, and the stricter one controls.",
   ["2.15", "2.25"]),
  ("Can I change my siding or exterior colors?",
   "Re-staining or repainting in substantially the same colors needs no approval. The guidelines also allow the earth-tone colors on the sample board they refer to. Metal or vinyl siding and exposed mill-finish aluminum or galvanized flashing are not permitted. Newer wood-look materials need approval, and you may be asked for samples.",
   ["2.66", "2.35"]),
  ("Can I build or replace a deck, patio or patio cover?",
   "A new deck needs approval. Replacing a deck that does not substantially change the old one, and routine repair, does not. Open patios and patio covers need approval, and for a new one you should talk to neighbors who can see it and share their feedback with the Committee. Enclosing a patio is an addition and needs detailed plans.",
   ["2.27", "2.70", "2.68", "2.69", "2.3"]),
  ("What about pools, hot tubs and play equipment?",
   "Pools need approval and must be landscaped and screened, and above-ground pools are discouraged. Hot tubs go in the side or rear yard as part of a deck or patio and must not be immediately visible to neighbors, streets or trails. Swing sets, play houses, skateboard ramps and sandboxes need approval and must be in a fenced rear yard. Treehouses are not permitted.",
   ["2.75", "2.48", "2.73", "2.104"]),
  ("Can I install a satellite dish or antenna?",
   "A dish from a commercial satellite provider such as DirecTV, DISH or ViaSat needs no approval if it is no more than two and a half feet across. Shortwave, large or unsightly antennae are not allowed, and the board or Committee decides what counts as large or unsightly. Wind-powered electric generators are not permitted.",
   ["2.8"]),
  ("Can I install solar panels or an air conditioner?",
   "The guidelines say heating and cooling units may not sit on a roof, but they except solar panels. They do not give a separate approval process for solar, and rooftop equipment generally needs approval, so ask the Committee first. Replacing an air conditioner in the same spot needs no approval. A new location should be chosen to limit visibility and noise for neighbors, and roof-mounted air conditioning is prohibited.",
   ["2.47", "2.88", "2.78", "2.6"]),
  ("Does anything affect drainage or utilities?",
   "Changes that significantly affect drainage need approval, and water must be able to flow freely across lots and away from foundations. You maintain the drainage swales and driveway culverts on your lot. All utility lines must be underground, and underground installations need approval.",
   ["2.30", "2.32", "2.107", "2.106"]),
  ("What is never allowed?",
   "Among the things the guidelines prohibit outright: metal or vinyl siding, treehouses, wells, individual water supplies and sewage disposal systems, above-ground storage tanks, oil and gas drilling or mining, dirt or gravel driveways, wind-powered generators, livestock and exotic animals, chain link and similar boundary fences, reflective materials in windows, roof-mounted air conditioning, and discharging firearms except in self-defense.",
   ["2.35", "2.104", "2.114", "2.113", "2.83", "2.95", "2.31", "2.32", "2.8", "2.7", "2.36", "2.115", "2.6", "2.37"]),
 ]),
]

# ---- render ----
def pdf_page(num):
    b = sections[num]
    return (b["page"] or 1) + PDF_OFFSET

def ref_links(nums):
    out = []
    for n in nums:
        if n not in sections: sys.exit("FAQ refers to missing section " + n)
        b = sections[n]
        out.append(f'<a class="ref" href="#{slug(n)}">{n} {esc(b["title"])}</a>')
    return " ".join(out)

def first_pdf(nums): return pdf_page(nums[0])

faq_html = ['<div class="faqcols">']
for cat, qs in FAQ:
    faq_html.append(f'<div class="faqcol"><h3 class="faqcat">{esc(cat)}</h3>')
    for q, a, refs in qs:
        faq_html.append(f'<details class="faq"><summary>{esc(q)}</summary><div class="faqbody"><p>{esc(a)}</p>'
                        f'<p class="refs"><span class="sub">In the guidelines:</span> {ref_links(refs)} '
                        f'<a class="pdflink" href="{PDF}#page={first_pdf(refs)}" target="_blank" rel="noopener">Open PDF page {first_pdf(refs)}</a></p></div></details>')
    faq_html.append('</div>')
faq_html.append('</div>')

toc = []
for b in blocks:
    if b["kind"] == "section":
        toc.append(f'<a href="#{slug(b["num"])}"><span class="n">{b["num"]}</span> {esc(b["title"])}</a>')

main = []
for b in blocks:
    if b["kind"] == "article":
        main.append(f'<h2 class="art" id="art-{b["num"].lower()}">Article {b["num"]}. {esc(b["title"].rstrip(".").title() if b["title"].isupper() else b["title"])}</h2>')
        txt = render_block(b)
        if txt: main.append(txt)
    else:
        n = b["num"]
        main.append(f'<section class="gsec" id="{slug(n)}"><h3><span class="n">{n}</span> {esc(b["title"])}</h3>\n{render_block(b)}\n'
                    f'<p class="pg"><a href="{PDF}#page={pdf_page(n)}" target="_blank" rel="noopener">PDF page {pdf_page(n)}</a> · <a href="#faq">FAQ</a> · <a href="#top">Top</a></p></section>')

doc = open(os.path.join(ROOT, "tools", "guidelines.template.html"), encoding="utf-8").read()
doc = doc.replace("@FAQ@", "\n".join(faq_html)).replace("@TOC@", "\n".join(toc)).replace("@MAIN@", "\n".join(main)).replace("@PDF@", PDF)
open(os.path.join(ROOT, "guidelines.html"), "w", encoding="utf-8").write(doc)
print("sections:", len(sections), "faq entries:", sum(len(q) for _, q in FAQ))
json.dump({n: {"title": b["title"], "page": b["page"]} for n, b in sections.items()}, open("/tmp/sections.json", "w"))
