/**
 * AMLI x HiveMinds — Creative Received Dashboard: data endpoint
 *
 * Reads the "Term - HM (Int)" tab of "Creative Repository Dashboard - AMLI x HM"
 * and returns ONLY aggregated counts (no ad names, scripts or links leave the sheet).
 *
 * Deploy: Deploy > New deployment > Web app
 *   Execute as: Me   |   Who has access: Anyone
 */

const SHEET_ID = '1-CN2Aits9NzmOOY032SRjVQX_qfm62a2_L8KlA9bzVo';
const TAB_NAME = 'Term - HM (Int)';
const FIRST_DATA_ROW = 4;            // rows 1-3 are headers

// ---- Classification rules (edit here) ----
const ANNUAL_DEAL = ['kpbusiness', 'angelinvestment', 'moneypurse', 'marathibrothers',
                     'easyhaifinance', 'easyfinance', 'anujpaul', 'aswinonfinance'];
const NANO_FACE_TYPES = ['nano', 'hminfluencerugc', 'geoads'];
const NON_BRANDED_STATIC_FACE_TYPES = ['hmai'];   // HmAIBrand counts as Branded

// Column positions (0-based, A = 0)
const COL = { owner: 0, type: 2, name: 3, face: 7, month: 14 };

const MONTHS = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
const MONTH_NAMES = ['January','February','March','April','May','June','July',
                     'August','September','October','November','December'];

function doGet() {
  const sheet = findTab_(SpreadsheetApp.openById(SHEET_ID));
  const lastRow = sheet.getLastRow();
  const rows = lastRow >= FIRST_DATA_ROW
    ? sheet.getRange(FIRST_DATA_ROW, 1, lastRow - FIRST_DATA_ROW + 1, 15).getDisplayValues()
    : [];

  const result = aggregate_(rows);
  result.generatedAt = new Date().toISOString();
  return ContentService.createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}

function aggregate_(rows) {
  const months = {};
  rows.forEach(function (r) {
    const m = monthKey_(r[COL.month]);
    if (!m) return;
    const cls = classify_(r);
    if (!cls) return;
    if (!months[m.key]) months[m.key] = { key: m.key, label: m.label, year: m.year, month: m.month, counts: emptyCounts_() };
    months[m.key].counts[cls]++;
  });
  const list = Object.keys(months).map(function (k) { return months[k]; })
    .sort(function (a, b) { return (a.year - b.year) || (a.month - b.month); });
  return { months: list };
}

function emptyCounts_() {
  return { staticBranded: 0, staticNonBranded: 0,
           videoAnnual: 0, videoNonAnnual: 0, videoNano: 0, videoBranded: 0 };
}

function classify_(r) {
  const type = norm_(r[COL.type]);
  const face = norm_(r[COL.face]);
  const name = norm_(r[COL.name]);
  if (type === 'video') {
    if (NANO_FACE_TYPES.indexOf(face) > -1) return 'videoNano';
    if (face === 'influenceraffiliate') {
      const annual = ANNUAL_DEAL.some(function (a) { return name.indexOf(a) === 0; });
      return annual ? 'videoAnnual' : 'videoNonAnnual';
    }
    return 'videoBranded';
  }
  if (type === 'static' || type === 'gif') {
    return NON_BRANDED_STATIC_FACE_TYPES.indexOf(face) > -1 ? 'staticNonBranded' : 'staticBranded';
  }
  return null;  // blank / other types are ignored
}

// "November'26", "Oct'26", "Sept'26" -> { key: '2026-11', ... }
function monthKey_(raw) {
  const s = String(raw || '').trim().toLowerCase();
  const m = s.match(/^([a-z]+)\W*(\d{2,4})$/);
  if (!m) return null;
  const idx = MONTHS.indexOf(m[1].slice(0, 3));
  if (idx < 0) return null;
  const year = m[2].length === 2 ? 2000 + Number(m[2]) : Number(m[2]);
  const mm = String(idx + 1).padStart(2, '0');
  return { key: year + '-' + mm, label: MONTH_NAMES[idx] + ' ' + year, year: year, month: idx + 1 };
}

function norm_(v) { return String(v || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }

function findTab_(ss) {
  const target = norm_(TAB_NAME);
  const match = ss.getSheets().filter(function (s) { return norm_(s.getName()) === target; })[0];
  if (!match) throw new Error('Tab not found: ' + TAB_NAME);
  return match;
}
