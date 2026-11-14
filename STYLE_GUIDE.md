# CoinFlow — "Brushed MSX" Dark Theme · Style Guide

Implementation brief for restyling **coinflow-fullstack** (Flask + Jinja + vanilla JS, one stylesheet at `app/static/css/style.css`).
The look combines a **Mac OS X Panther brushed-metal window**, the **beige/graphite colours of a DEC VT220 terminal** and the **rainbow stripes of an 80s "BASIC MSX" book cover**. Dark mode only (no light theme yet).

Design reference (canvas): Portfolio, Log In, Sign Up, Newsletter and Dialogs boards in the "CoinFlow — Retro Dark Mode Study" design.

---

## 0. Scope and ground rules

- **Restyle, don't re-architect.** Keep every existing route, template block, element `id`, `data-*` attribute and JS hook (`.hidden`, `.active`, `.profit`, `.loss`, `.delete-button`, `#tab-assets`, `#transactions-body`, `[data-open-popup]`, `[data-close-popup]`, `[data-toggle]`, `[data-sensitive]`, `form[data-loading]` …). JS must keep working unchanged except for the small edits listed in §8.
- Replace `style.css` wholesale using the tokens in §2. Where markup must change, the change is listed in §7.
- **One font family for everything** (§3). Remove the Google Fonts `<link>`s from `base.html`.
- Work test-first (§10): add the template/markup assertions to `tests/test_app.py`, watch them fail, then implement.

---

## 1. Concept in one line per layer

| Layer | Treatment | Where |
|---|---|---|
| Desktop | Near-black warm charcoal with a soft top spotlight | `body` |
| Window | Brushed dark metal panel, 10px radius, deep drop shadow | wraps header + main + footer on app pages; the auth box |
| Brand band | 8 stacked MSX stripes, full width | under the app header, under the auth window title, bottom of paper cards |
| Paper | Beige "book cover" card with dark ink | hero summary, asset card, about cards, newsletter subscribe card, alerts |
| Well | Recessed dark area (inset shadow) | Assets/Transactions panel, empty states |
| Controls | Panther "textured" pill buttons (secondary) + amber MSX **keycap** (primary) | nav, logout, tabs, delete; primary CTAs |

---

## 2. Design tokens (paste into `:root`)

```css
:root {
  /* Desktop + metal */
  --desk:          #1C1B1A;   /* page background (MSX cover charcoal) */
  --desk-deep:     #121110;
  --desk-glow:     #34322F;   /* top spotlight */
  --metal:         #2C2B29;   /* window base */
  --metal-hi:      #383633;
  --metal-lo:      #262523;
  --edge:          #0C0C0B;   /* 1px control/window borders */
  --well:          rgba(12, 12, 11, 0.45);
  --well-solid:    #121110;
  --input-bg:      #161514;

  /* Paper (VT220 bezel / MSX cover beige) */
  --paper:         #D8CFAF;
  --paper-input:   #F2EBD3;
  --paper-border:  #8C846A;
  --ink:           #1C1B1A;   /* text on paper */
  --ink-2:         #4A463B;   /* secondary text on paper (≥ 4.5:1 on --paper) */
  --ink-3:         #2E2B24;   /* body copy on paper */

  /* Text on dark */
  --text-hi:       #F1EAD2;   /* headings, active labels */
  --text:          #E7E0C9;   /* body */
  --text-2:        #CFC7AE;   /* labels, secondary */
  --text-3:        #B3AC97;   /* captions, table headers, footer */
  --text-off:      #8D877A;   /* disabled ("Coming soon") */
  --placeholder:   #8D877A;

  /* Accent + signal */
  --amber:         #E6B42A;   /* primary action, focus ring, active tab, links */
  --amber-hover:   #F3CB55;
  --amber-shade:   #8C6A10;   /* keycap "depth" shadow */
  --amber-tint:    rgba(230, 180, 42, 0.12);
  --amber-on-dark: #F3D27A;   /* amber text on dark backgrounds */
  --profit:        #9BD77F;   /* on dark */
  --loss:          #F29A84;   /* on dark */
  --profit-ink:    #2C5A1E;   /* on paper */
  --loss-ink:      #8E2A2A;   /* on paper */
  --danger:        #B83A26;   /* destructive button fill (5:1 with #FFF7EE) */
  --danger-shade:  #7A2014;
  --bitcoin:       #F7931A;

  /* MSX stripes — in this order, top to bottom */
  --s1: #3FB4C8;  /* cyan   */
  --s2: #2E5FA8;  /* blue   */
  --s3: #6BA43A;  /* green  */
  --s4: #7A5A9E;  /* purple */
  --s5: #8E2A2A;  /* maroon */
  --s6: #D2412E;  /* red    */
  --s7: #E07A2E;  /* orange */
  --s8: #E6B42A;  /* yellow */

  /* Type */
  --font: 'Lucida Grande', 'Lucida Sans Unicode', 'Lucida Sans', Geneva, Verdana, sans-serif;

  /* Shape + depth */
  --r-window: 10px;
  --r-card:   4px;
  --r-well:   6px;
  --r-pill:   999px;
  --shadow-window: 0 30px 70px rgba(0,0,0,.65), inset 0 1px 0 rgba(255,255,255,.08);
  --shadow-paper:  0 6px 16px rgba(0,0,0,.45);
  --shadow-well:   inset 0 1px 4px rgba(0,0,0,.6), 0 1px 0 rgba(255,255,255,.05);
  --bevel-pill:    inset 0 1px 0 rgba(255,255,255,.18);
  --press-pill:    inset 0 1px 3px rgba(0,0,0,.7), 0 1px 0 rgba(255,255,255,.08);

  /* Spacing (4px base) */
  --sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px;
  --sp-5: 20px; --sp-6: 24px; --sp-7: 28px; --sp-8: 32px;
}
```

### Reusable backgrounds

```css
/* page */
body {
  background-color: var(--desk);
  background-image: radial-gradient(ellipse at 50% 0%, var(--desk-glow) 0%, var(--desk) 60%, var(--desk-deep) 100%);
  background-attachment: fixed;
}

/* brushed metal: fine horizontal hairlines over a vertical sheen */
.window {
  background-color: var(--metal);
  background-image:
    repeating-linear-gradient(0deg,
      rgba(255,255,255,.022) 0 1px, transparent 1px 2px, rgba(0,0,0,.05) 2px 3px),
    linear-gradient(var(--metal-hi), var(--metal-lo) 40%, var(--metal));
  border: 1px solid #0A0A09;
  border-radius: var(--r-window);
  box-shadow: var(--shadow-window);
  overflow: hidden;
}

/* 8-stripe brand band; use height 5px under the app header, 4px elsewhere */
.stripe-band {
  height: 40px; /* 8 × 5px */
  background: linear-gradient(
    var(--s1) 0 12.5%, var(--s2) 0 25%, var(--s3) 0 37.5%, var(--s4) 0 50%,
    var(--s5) 0 62.5%, var(--s6) 0 75%, var(--s7) 0 87.5%, var(--s8) 0 100%);
}
.stripe-band--thin { height: 32px; } /* 8 × 4px */
```

**Contrast checks (all pass WCAG AA 4.5:1 for body text):** `--text` on `--metal`, `--text-3` on `--metal`, `--ink-2` on `--paper`, `--ink` on `--amber`, `--profit`/`--loss` on `--metal`, `--profit-ink` on `--paper`, `#FFF7EE` on `--danger`. `--text-off` (3.96:1) is only for disabled items, which WCAG exempts. Never put `--amber` text on `--paper` (too low) — use `--ink` there.

---

## 3. Typography

One family everywhere — the classic Mac OS X UI face, with system fallbacks:

```css
body, button, input, select, textarea { font-family: var(--font); }
```

- Mac: Lucida Grande · Windows: Lucida Sans Unicode · others: Geneva → Verdana. No web font download.
- Only **regular (400)** and **bold (700)** exist in Lucida Grande — never use 500/600/800/900.
- **All numbers** (amounts, prices, IDs, dates in tables) use `font-variant-numeric: tabular-nums;` so columns line up. Put it on `.hero-value`, `.transactions-table td`, `.asset-card`, `.price-hint`.
- Uppercase + letter-spacing gives the MSX "cover" voice without a display font.

| Role | Size / line-height | Weight | Case / tracking | Colour | Used for |
|---|---|---|---|---|---|
| Wordmark | 20px / 1 | bold | UPPER, .02em | `--text-hi` | "COINFLOW" in header (16px, .08em in auth title bar) |
| Hero label | 34px / 1 | bold | UPPER, .01em | `--ink` | "BTC", "TOTAL" |
| Hero value | 30px / 1.2 | regular | tabular | `--ink` | amounts |
| Page title | 26–28px / 1.2 | bold | sentence | `--text-hi` (dark) / `--ink` (paper) | "Log In", "Subscribe to our Newsletter" |
| Section title | 18–22px / 1.3 | bold | sentence | `--text-hi` | "Past Newsletters", "An online Bitcoin tracker…" |
| Card title | 15px / 1.3 | bold | UPPER, .04em | `--ink` | about cards |
| Primary button | 15–17px | bold | UPPER, .02–.04em | `--ink` | keycaps |
| Body | 14px / 1.5 | regular | — | `--text` / `--ink-3` | default |
| Label | 12px | bold | — | `--text-2` | form labels |
| Table header | 11px | bold | UPPER, .1em | `--text-3` | `th` |
| Caption / footer | 12px | regular | — | `--text-3` | footer, hints |

---

## 4. Layout

- App pages: `.home-container` → padding `36px 24px 56px`; inside it **one `.window`** with `max-width: 1120px; margin: 0 auto;`.
- Window order: `.app-header` → `.stripe-band` → `<main>` (padding `26px 22px 28px`, `display:flex; flex-direction:column; gap:24px`) → `.site-footer`.
- Auth pages: centred `.auth-box.window` `max-width: 420px`, then `.about-section` and footer below, both `max-width: 1120px`, page gap `56px`.
- All rows use flex/grid with `flex-wrap: wrap`; nothing has a fixed width that breaks below 360px.
- Wide tables scroll inside their own box (`.transactions-panel { overflow-x: auto; }`, table `min-width: 760px`).

Breakpoints (replace existing media queries):

```css
@media (max-width: 860px) {
  .app-header { justify-content: center; }
  .hero-children { border-right: 0; border-bottom: 1px solid rgba(28,27,26,.18); }
  .hero-children:last-child { border-bottom: 0; }
}
@media (max-width: 480px) {
  .home-container { padding: 12px 8px 32px; }
  .hero-children h2 { font-size: 28px; }
  .hero-value span { font-size: 24px; }
}
```

---

## 5. Components (CSS mapped to existing class names)

### 5.1 Buttons

**Primary — MSX keycap** (`.btn-blue`, `.auth-form button`, `.popup button[type=submit]`). Keep the class name `.btn-blue` to avoid template churn, or rename to `.btn-primary` everywhere (preferred; update templates).

```css
.btn-primary, .btn-blue, .auth-form button, .popup button[type="submit"] {
  height: 52px; padding: 0 22px;
  border: 2px solid var(--edge); border-radius: var(--r-card);
  background: var(--amber); color: var(--ink);
  box-shadow: 0 4px 0 var(--amber-shade);
  font: bold 17px/1 var(--font); letter-spacing: .02em; text-transform: uppercase;
  cursor: pointer; transition: transform .05s, box-shadow .05s, background .15s;
}
.btn-primary:hover  { background: var(--amber-hover); }
.btn-primary:active { transform: translateY(3px); box-shadow: 0 1px 0 var(--amber-shade); }
.btn-primary:disabled { opacity: .6; cursor: wait; transform: none; }
/* form submits: height 48px, 16px text, width 100% */
```

**Secondary — Panther textured pill** (`.logout-button`, `.nav a`, `.delete-button`, `.close-button`, Unsubscribe, Cancel).

```css
.pill {
  display: inline-flex; align-items: center; justify-content: center;
  height: 30px; padding: 0 14px;
  border: 1px solid var(--edge); border-radius: var(--r-pill);
  background: linear-gradient(#55524D, #3B3936);
  box-shadow: var(--bevel-pill);
  color: var(--text); font: bold 14px var(--font); text-decoration: none; cursor: pointer;
}
.pill:hover { background: linear-gradient(#5E5B55, #44423E); }
.pill.active, .pill[aria-current="page"] {           /* pressed-in */
  background: linear-gradient(#1E1D1C, #2A2927);
  box-shadow: var(--press-pill); color: var(--text-hi);
}
```
- Icon-only pills (delete, close): `36×32px`, padding 0, 14px stroke icon in `--text`. **Must** have `aria-label`.
- Danger (confirm delete): keycap shape with `background: var(--danger); color: #FFF7EE; box-shadow: 0 3px 0 var(--danger-shade);`.

**Focus (all interactive elements):**
```css
:focus-visible { outline: 2px solid var(--amber); outline-offset: 2px; }
```

### 5.2 App header (`partials/app_header.html`)

- Flex row, `wrap`, `justify-content: space-between`, `gap: 12px`, `padding: 10px 16px`, transparent (sits on the window metal).
- **Left:** wordmark "COINFLOW" (keep the `logo.svg` image if wanted, 24px, before the text).
- **Centre `.nav`:** links are `.pill`; the active one is `.pill.active` (keep the existing Jinja `active` logic). `.disabled-link` = same pill geometry but `border-color: #22211F; background: none; box-shadow: none; color: var(--text-off); cursor: default;` with `title="Coming soon"` and `aria-disabled="true"`.
- **Right:** username in `--text-2` (drop the user.svg or tint it), then Log Out as `.pill` (non-bold).
- No traffic-light window buttons.
- Directly after `</header>`: `<div class="stripe-band" aria-hidden="true"></div>`.

### 5.3 Hero summary (`.hero`) — ONE paper card

```css
.hero {
  background: var(--paper); color: var(--ink);
  border-radius: var(--r-card); box-shadow: var(--shadow-paper);
  overflow: hidden; display: flex; flex-direction: column;
}
.hero-row { display: flex; flex-wrap: wrap; align-items: stretch; }
.hero-children {
  flex: 1 1 280px; padding: 20px 24px 18px;
  display: flex; flex-direction: column; align-items: flex-start; gap: 4px;
  border-right: 1px solid rgba(28,27,26,.18);
}
.hero-children:last-child { flex: 0 1 260px; justify-content: center; border-right: 0; }
.hero-children h2 { margin: 0; font: bold 34px/1 var(--font); letter-spacing: .01em; text-transform: uppercase; }
.hero-value { display: flex; align-items: center; gap: 8px; }
.hero-value span { font-size: 30px; font-variant-numeric: tabular-nums; }
.hero-sub { margin: 0; color: var(--ink-2); }
.hero-sub.profit { color: var(--profit-ink); }
.hero-sub.loss   { color: var(--loss-ink); }
.eye-toggle {                       /* 44×44 touch target */
  width: 44px; height: 44px; display: grid; place-items: center;
  border: 0; border-radius: 50%; background: rgba(28,27,26,.08); cursor: pointer;
}
.eye-toggle img { width: 22px; height: 22px; filter: brightness(0) saturate(0) opacity(.85); } /* ink-coloured icon */
.hero .stripe-band--thin { margin-top: auto; }
```
Content is **left-aligned**. The three columns are BTC · TOTAL · ADD TRANSACTION; the 8-stripe band runs across the bottom of the card.
Ideally show only the number in `.hero-sub`'s value and wrap it in a `<span>` so the label stays `--ink-2` and the number is `--ink` (or profit/loss ink).

### 5.4 Assets / Transactions panel (`.user-assets-transactions`)

```css
.user-assets-transactions {
  background: var(--well); border-radius: var(--r-well);
  box-shadow: var(--shadow-well); padding: 14px 16px 18px;
}
```

**Tabs (`.button-tabs`) — segmented capsule in a recessed track:**
```css
.button-tabs {
  display: inline-flex; gap: 3px; padding: 3px; margin-bottom: 14px;
  border-radius: 17px; background: var(--well-solid);
  box-shadow: inset 0 1px 3px rgba(0,0,0,.8);
}
.button-tabs button {
  height: 28px; padding: 0 16px; border: 0; border-radius: 14px;
  background: transparent; color: var(--text-2); font: 13px var(--font); cursor: pointer;
}
.button-tabs button.active { background: var(--amber); color: var(--ink); font-weight: bold; }
```
Remove the old `#tab-assets-button` / `#tab-transactions-button` rules. Also set `aria-selected` in `setActiveTab()` (§8).

**Asset card (`.asset-card.bitcoin`) — small paper card:**
- `width: 210px`, paper background, `--shadow-paper`, radius 4px, padding 14px, column gap 6px, left-aligned.
- Bitcoin logo 40px; name "BITCOIN" bold 20px uppercase; price tabular; meta line 12px `--ink-2`.
- Bottom: 6px horizontal mini-band of 4 stripe colours (`--s1 --s3 --s7 --s4`), equal widths.

**Add asset (`.add-asset-card`):** `210px × min 160px`, `2px dashed #6E685B`, transparent, `--text-2`, bold 15px uppercase text "+ ADD ASSET" (the plus.svg can stay, tinted light). Hover: border `--text-3`.

**Transactions table:**
```css
.transactions-table { width: 100%; min-width: 760px; border-collapse: collapse; }
.transactions-table th {
  padding: 6px 10px; text-align: left;
  font: bold 11px var(--font); letter-spacing: .1em; text-transform: uppercase; color: var(--text-3);
}
.transactions-table td {
  padding: 10px; border-top: 1px solid rgba(255,255,255,.07);
  font-size: 13px; font-variant-numeric: tabular-nums; color: var(--text);
}
.transactions-table td:first-child { font-weight: bold; color: var(--text-hi); font-size: 14px; }
.transactions-table td:nth-child(2) { color: var(--text-3); }           /* transaction id */
.transactions-table th:nth-child(n+4), .transactions-table td:nth-child(n+4) { text-align: right; }
.transactions-table tbody tr:hover td { background: rgba(255,255,255,.03); }
.transactions-table td.profit { color: var(--profit); }
.transactions-table td.loss   { color: var(--loss); }
```
**Stripe chip per row (signature detail):** each transaction gets a stripe colour, cycling `--s1, --s3, --s7, --s4, --s2, --s5, --s6, --s8` by row index. Render it as an 18×18px, 2px-radius square in a new first column (`aria-hidden="true"`, header cell visually hidden text "Stripe"). See §8 for the JS. Order of rows: newest first.

**Delete button:** icon-only pill (trash icon, 14px), `aria-label="Delete transaction"`. Replace the text "Delete".

**Empty state (`.empty-state`, `.placeholder-text`):** `display:flex; align-items:center; gap:14px; padding:18px; border:2px dashed #4A4740; border-radius:4px; color:var(--text-3);` with a 34px-wide mini 4-stripe stack on the left.

### 5.5 Forms

**Dark inputs (auth, popup):**
```css
.auth-form input, .popup input {
  height: 40px; padding: 0 12px; box-sizing: border-box; width: 100%;
  border: 1px solid var(--edge); border-radius: var(--r-card);
  background: var(--input-bg); color: var(--text-hi);
  box-shadow: inset 0 1px 3px rgba(0,0,0,.7), 0 1px 0 rgba(255,255,255,.06);
  font: 14px var(--font); font-variant-numeric: tabular-nums;
}
input::placeholder { color: var(--placeholder); }
.popup input:disabled { background: #22211F; color: var(--text-3); }
input[type="date"] { color-scheme: dark; }
```
**Labels:** visible label above every field — 12px bold `--text-2`, `gap: 6px`. The auth forms currently use placeholders only; **add `<label>`s** (§7).

**Paper inputs (newsletter card):** `background: var(--paper-input); border: 1px solid var(--paper-border); box-shadow: inset 0 1px 2px rgba(0,0,0,.25); color: var(--ink); height: 44px;` label 12px bold `--ink-3`.

### 5.6 Auth pages (`auth/_layout.html`, `login.html`, `register.html`)

- `.auth-box` = `.window`, `max-width: 420px; width: 100%`.
- `.auth-header` = window title bar: height 40px, centred wordmark "COINFLOW" (bold 16px, .08em). Followed by `.stripe-band--thin`.
- Form padding `26px 28px 28px`, column gap 16px.
- Title row: `<h1>` (26px bold `--text-hi`) on the left, the toggle link (`.auth-toggle`: "Register" / "Log In") on the right as an amber bold link.
- Submit keycap is full-width, height 48px ("LOG IN" / "SIGN UP").
- Under the button, centred 12px `--text-3`: "New here? Register" / "Already have an account? Log In".
- Register password hint "At least 6 characters" under the field (11px `--text-3`) instead of inside the placeholder.

**About section (`.about-section`):** `h2` 22px bold `--text-hi` (remove the old `::after` underline). The four `.about-content` blocks become paper cards in `grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px;`. Each card: top 6px band of two stripe colours (pairs in order: s1+s2, s3+s4, s5+s6, s7+s8), padding `16px 18px 18px`, title 15px bold uppercase, body 13px/1.5 `--ink-3`, lists with 18px indent.

### 5.7 Newsletter page (`dashboard/newsletter.html`)

- First `.content-card` (subscribe/subscribed) = **paper card** with the 8-stripe band at the bottom. Left-aligned; `h1` 28px bold `--ink`; subtitle `--ink-2`; email field + SUBSCRIBE keycap side by side (wrap on mobile, input max 420px). Subscribed state: "You are subscribed with **email**" then Unsubscribe as a `.pill`.
- "Past Newsletters" and "Articles" = **wells** (`.user-assets-transactions` style) with `h1` → 18px bold `--text-hi` and the dashed empty state "Nothing yet.".
- `#newsletter-loading` text in `--text-3`.

### 5.8 Popup — Add Investment (`#investment-popup`)

- `.popup-overlay`: `position:fixed; inset:0; background: rgba(10,10,9,.85); display:grid; place-items:center; padding:16px; z-index:100;`
- `.popup` = `.window`, `width: min(440px, 100%)`.
- Header row: `h2` "Add Investment" 18px bold `--text-hi` left, `.close-button` icon pill right (replace the "✖" glyph with an inline SVG X, keep `aria-label="Close"`), padding `14px 18px`, then `.stripe-band--thin`.
- Form padding `20px 22px 24px`, gap 14px, dark inputs.
- `.price-hint`: `padding: 8px 12px; border-radius:4px; background: var(--amber-tint); color: var(--amber-on-dark); font-size:13px;` hide when empty (`.price-hint:empty { display:none; }`).
- Submit = full-width keycap "SUBMIT".

### 5.9 SweetAlert2 popups (loading, success, error, confirm)

Theme them as **paper cards** via CSS overrides (no plugin change):
```css
.swal2-popup {
  background: var(--paper) !important; color: var(--ink) !important;
  border-radius: var(--r-card) !important; box-shadow: 0 20px 50px rgba(0,0,0,.7) !important;
  font-family: var(--font) !important;
  border-bottom: 8px solid transparent;
  border-image: linear-gradient(90deg, var(--s1), var(--s2), var(--s3), var(--s4), var(--s5), var(--s6), var(--s7), var(--s8)) 1;
}
.swal2-title { color: var(--ink) !important; font-size: 18px !important; font-weight: bold !important; }
.swal2-html-container { color: var(--ink-2) !important; font-size: 13px !important; }
.swal2-backdrop-show { background: rgba(10,10,9,.85) !important; }
.swal2-styled.swal2-confirm { /* keycap */
  background: var(--amber) !important; color: var(--ink) !important;
  border: 2px solid var(--edge) !important; border-radius: 4px !important;
  box-shadow: 0 3px 0 var(--amber-shade) !important; font-weight: bold !important; text-transform: uppercase;
}
.swal2-styled.swal2-cancel { /* pill */
  background: linear-gradient(#55524D, #3B3936) !important; color: var(--text) !important;
  border: 1px solid var(--edge) !important; border-radius: 999px !important;
}
.swal2-styled:focus { box-shadow: 0 0 0 2px var(--amber) !important; }
.swal2-loader { border-color: var(--amber) transparent var(--amber) transparent !important; }
```
For the delete confirmation, add `customClass: { confirmButton: 'swal-danger' }` and style `.swal-danger` with `--danger` / `--danger-shade` and light text.

### 5.10 Footer (`partials/footer.html`)

Inside the window on app pages (after `</main>`), below the about section on auth pages.
`display:flex; flex-wrap:wrap; justify-content:space-between; gap:8px; padding:12px 22px 16px; border-top:1px solid rgba(255,255,255,.06); font-size:12px; color:var(--text-3);`
Left: "Made for Bitcoiners. © CoinFlow {{ current_year }}. All Rights Reserved." Right: Privacy Policy · Terms of Service · Contact as links in `--text-2` (they're currently plain text — keep as text if there are no routes, but don't style them as links then).

---

## 6. Iconography

- Line icons, 1.3–1.8px stroke, rounded joins, coloured with `currentColor` where possible.
- Existing SVGs in `static/img/` are dark-on-light; either recolour them (`fill`/`stroke` → `currentColor`, then inline them) or tint with CSS filters. Eye icons on paper use ink colour; plus/user icons on dark use `--text-2`.
- No emoji in UI (the footer's ❤️ is dropped).

---

## 7. Markup changes (minimal)

1. **`base.html`** — delete the three Google Fonts lines (`preconnect` ×2 + stylesheet).
2. **`partials/app_header.html`**
   - add `class="pill"` to each nav `<a>` and to `.logout-button`; keep the `active` class logic; add `aria-current="page"` to the active link.
   - add `aria-disabled="true"` to each `.disabled-link`.
   - replace the logo `<span>CoinFlow</span>` with `<span>COINFLOW</span>` (or use `text-transform`).
   - after `</header>` add `<div class="stripe-band" aria-hidden="true"></div>`.
3. **`dashboard/index.html` and `dashboard/newsletter.html`**
   - wrap the header include, `<main>` content and the footer include in `<div class="window">…</div>` inside `.home-container`; wrap the sections in `<main class="app-main">`.
   - hero: wrap the three `.hero-children` in `<div class="hero-row">` and append `<div class="stripe-band--thin stripe-band" aria-hidden="true"></div>` as the last child of `.hero`.
   - transactions `<thead>`: add a first `<th><span class="visually-hidden">Stripe</span></th>`; give the empty last `<th>` the text `<span class="visually-hidden">Actions</span>`.
   - `.button-tabs` buttons: add `aria-selected` (`true` on Assets by default) and `aria-controls="tab-assets"` / `"tab-transactions"`.
   - close button: replace `✖` with an inline SVG X.
4. **`auth/_layout.html`, `login.html`, `register.html`**
   - add `window` class to `.auth-box`; add `<div class="stripe-band stripe-band--thin" aria-hidden="true"></div>` after `.auth-header`.
   - move the `{% block toggle %}` link into the form title row (next to `<h1>`).
   - wrap each input in `<label>Username <input …></label>` (keep `name`, `autocomplete`, `required`, `minlength`).
   - add the helper line under the submit button.
5. **`partials/footer.html`** — remove the emoji; keep `current_year`.

Add a utility once:
```css
.visually-hidden { position:absolute; width:1px; height:1px; margin:-1px; padding:0; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; border:0; }
```

---

## 8. JS changes (small)

- **`dashboard.js` › `renderHoldings`**: prepend a stripe cell to each row and use an icon for delete:
  ```js
  const STRIPES = ['--s1','--s3','--s7','--s4','--s2','--s5','--s6','--s8'];
  // inside holdings.forEach((holding, index) => { ... })
  const chipCell = document.createElement('td');
  const chip = document.createElement('span');
  chip.className = 'stripe-chip';
  chip.setAttribute('aria-hidden', 'true');
  chip.style.background = `var(${STRIPES[index % STRIPES.length]})`;
  chipCell.appendChild(chip);
  row.prepend(chipCell);          // do this AFTER the profit/loss cell lookup, or change row.children[5] → [6]
  deleteButton.setAttribute('aria-label', 'Delete transaction');
  deleteButton.innerHTML = '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M2 4h10M5 4V2.5h4V4M3.5 4l.7 8h5.6l.7-8" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>';
  ```
  `.stripe-chip { display:block; width:18px; height:18px; border-radius:2px; }`
  ⚠️ The profit/loss cell index shifts by one once the chip cell exists.
- **`dashboard.js` › tab switcher**: also set `button.setAttribute('aria-selected', active)`.
- **`main.js`**: remove `confirmButtonColor: '#0088cc'` and `'#c04848'` (the CSS theme handles colours); add `customClass: { confirmButton: 'swal-danger' }` in `confirmAction`.

---

## 9. Accessibility checklist

- Every control is a real `<button>`/`<a>`/`<input>` with a visible or `aria-label` name; icon-only buttons have `aria-label`.
- Touch targets ≥ 44px for eye toggles and primary actions; pills are 30–32px tall but have ≥ 8px spacing.
- Visible `:focus-visible` ring (amber, 2px, offset 2px) on every interactive element — on paper and on metal.
- Decorative stripes/chips are `aria-hidden="true"`; profit/loss is conveyed by the sign (+/−) as well as colour.
- Dialog: `role="dialog" aria-modal="true" aria-labelledby="popup-title"` (already present); move focus into it on open and back to the trigger on close; Esc closes.
- Text contrast per §2; don't use opacity to dim text (use the token colours).

---

## 10. Implementation order (test-first)

1. **Tests (red):** in `tests/test_app.py` add assertions that render pages and check for:
   - no `fonts.googleapis.com` in `base.html` output;
   - `class="stripe-band` present on login, register, dashboard and newsletter pages;
   - `.hero-row` and `.window` on the dashboard;
   - `<label` wrapping the `username` and `password` inputs on login/register;
   - `aria-current="page"` on the active nav link;
   - the Stripe/Actions visually-hidden header cells.
2. **Tokens + base (green-ish):** new `:root`, `body`, typography, `.window`, `.stripe-band`, `.pill`, `.btn-primary`, focus ring, `.visually-hidden`.
3. Header + footer partials.
4. Dashboard: hero, tabs, asset cards, table, empty state, popup.
5. JS tweaks (§8).
6. Auth layout + about cards.
7. Newsletter.
8. SweetAlert theme.
9. Responsive pass at 1280 / 860 / 390px; keyboard-only pass; run the full test suite.

**Definition of done:** all tests pass; every page matches the design boards at 1280px; no horizontal page scroll at 390px (only the table box scrolls); every interactive element is reachable and visibly focused by keyboard; no other font files are requested.
