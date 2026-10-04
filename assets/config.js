// Board: edit these values, commit, and the site updates. Dues amounts and due dates live in the database (Board page, Dues settings);
// the numbers below are only shown if the database cannot be reached.
// "sample: true" shows a notice on the resident page that the amounts are placeholders.
window.PINERY = {
  name: "Pinery Filing 11 HOA",
  // Supabase project. The URL and the publishable key are meant to be public. Never put a secret or service_role key here.
  supabase: {
    url: "https://mrmxaxvsiigjozddgztl.supabase.co",
    key: "sb_publishable_mbds4zXeJX9joEOgYUSP6g_ekE_M0pu"
  },
  short: "Pinery 11",
  sample: true,
  dues: {
    amount: 30,             // annual dues per lot, in dollars
    dueMonthDay: "11-01",   // due date each year (MM-DD)
    graceDays: 30,          // days after the due date before the late fee applies
    lateFee: 25,            // dollars
    label: "Annual HOA dues",
    covers: "Catering for the annual meeting and the HOA's legal insurance."
  },
  pay: {
    checkPayee: "Pinery Filing 11 HOA",
    mailTo: ["[Board: mailing address or PO Box]"],
    memo: "Your street address",
    online: { label: "", url: "" },   // optional: paste a payment link to show a Pay online button
    inPerson: "[Board: where and when a check can be dropped off]"
  },
  // Newest first. The board edits this list until announcements move to the database.
  announcements: [
    { date: "2026-10-02", title: "New Pinery 11 website in preview", body: "Dues information and governing documents are being moved here. Sign-in for private balances is coming next." }
  ],
  documents: [
    { title: "Architectural Guidelines and Rules and Regulations", note: "The Pinery Filing No. 11, dated July 10, 2016. 31 pages.", file: "docs/Architectural-Guidelines-Rules-and-Regulations-2016.pdf", page: "guidelines.html" },
    { title: "Notice of the July 25, 2026 Annual Meeting", note: "Agenda and the General Proxy Authority form. Board members' contact details are removed. For the record.", file: "docs/General-Meeting-Notice-2026-07-25.pdf" }
  ],
  contact: { email: "[board email]", note: "The board answers within a few days." }
};
