# MLB Dashboard Frontend/UI Improvement Plan

## General Principles
- Prioritize data density and scannability for power users and bettors
- Maintain a modern, clean, and readable look
- Ensure visual consistency and a unified design system
- Use color and typography to highlight key numbers and trends

---

## 1. Data Density & Information Architecture
- Show more stats per player/team (not just rank/value)
- Add contextual stats: recent games, splits, trends, hit rates
- Use compact layouts to fit more information per screen

## 2. Visual Consistency & Hierarchy
- Standardize card/table designs (Props page as template)
- Consistent typography scale and color palette
- Use semantic colors (green=positive, red=negative, blue=neutral)
- Reduce unnecessary whitespace

## 3. Sportsbook Features
- Odds movement indicators (arrows/colors)
- "Hot"/popular bet tags
- Real-time updates for odds and scores
- Advanced filters (position, team, prop type, odds range)
- Side-by-side player/team comparison tools

## 4. Page-Specific Suggestions
### Player Props
- Add trend indicators (📈📉) for recent performance
- Show prop hit rate (last 10 games)
- More prominent odds comparison

### Stat Leaders
- Grid/table layout, not just cards
- Show multiple stats per player (BA, HR, RBI, OPS, etc.)
- Sorting and filtering by stat
- Mini sparklines for trends

### Games & Weather
- More games visible at once (denser layout)
- Live game status (inning, score, pitch count)
- Weather icons and impact data
- Starting pitcher vs. opponent stats

### Standings
- Add L10, streak, run differential, playoff odds
- Expandable team details

## 5. Data-First Design
- Scannable, Excel-like tables for power users
- Quick actions and contextual stats
- Big, bold numbers; small descriptive text

## 6. Technical
- Real-time updates (WebSocket)
- Fast caching for snappy UI
- Mobile optimization (touch-friendly, still dense)
- Dark mode

---

**Next Steps:**
- Start with Stat Leaders or enhance Player Props as first redesign target
- Refer to this doc for consistent improvements across all pages 