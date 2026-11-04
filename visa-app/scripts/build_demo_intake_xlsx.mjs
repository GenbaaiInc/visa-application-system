import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputPath = process.argv[2];
const previewPath = process.argv[3];

if (!outputPath) {
  console.error("Usage: node build_demo_intake_xlsx.mjs <output.xlsx> [preview.png]");
  process.exit(2);
}

const caseData = {
  caseId: "demo-gijinkoku-001",
  applicantName: "SAMPLE ARIA",
  applicantNameLocal: "サンプル アリア",
  nationality: "Nepal",
  sex: "female",
  birthDate: "1998-06-15",
  birthPlace: "Luma City",
  occupation: "Software Developer",
  maritalStatus: "single",
  homeAddress: "77 Demo Lane, Luma City, Nepal",
  email: "sample.aria.demo@example.invalid",
  phone: "+977-01-000-0000",
  passportNumber: "ZZ0000000",
  passportExpiry: "2034-12-31",
  school: "Luminara Technical College",
  degree: "Bachelor of Computer Science",
  graduationDate: "2021-06-30",
  priorEmployer: "DemoSoft Labs Pvt. Ltd.",
  priorEmploymentPeriod: "2021-08 to 2024-03",
  employerName: "株式会社デモリンクAI",
  employerNameEn: "DemoLink AI Inc.",
  employerNumber: "9999999999999",
  employerPostalCode: "9999999",
  employerAddress: "東京都デモ区サンプル町0-0-0",
  employerPhone: "9999999999",
  plannedEntryDate: "2027-03-15",
  plannedPort: "Narita International Airport",
  plannedPeriodYears: 5,
  plannedPeriodMonths: 0,
  japanContactPostalCode: "9999999",
  japanContactAddress: "東京都デモ区サンプル町0-0-0 Demo Residence 101",
  japanContactPhone: "9999999999",
  startDate: "2027-04-01",
  contractType: "雇用 Employment",
  employmentPeriodType: "Fixed-term",
  employmentPeriodYears: 1,
  employmentPeriodMonths: 0,
  jobCategoryPrimary: "情報処理・通信技術",
  monthlySalary: 320000,
  priorEntriesCount: 0,
  priorCoeCount: 0,
  hasAccompanyingMembers: false,
  hasJapanRelativesOrCohabitants: false,
};

function section(title) {
  return [title, "", "", "DEMO / NOT VALID"];
}

const rows = [
  ["Applicant intake sheet demo", "", "", ""],
  ["DEMO / NOT VALID", "Fictional sample for software demonstration only", "", ""],
  ["Case ID", caseData.caseId, "Target status", "Engineer humanities international services"],
  section("Applicant identity"),
  ["Name roman", caseData.applicantName, "Name local", caseData.applicantNameLocal],
  ["Nationality region", caseData.nationality, "Sex", caseData.sex],
  ["Birth date", caseData.birthDate, "Birth place", caseData.birthPlace],
  ["Occupation", caseData.occupation, "Marital status", caseData.maritalStatus],
  ["Home country address", caseData.homeAddress, "Email", caseData.email],
  ["Phone", caseData.phone, "", ""],
  section("Passport"),
  ["Passport number", caseData.passportNumber, "Passport expiry date", caseData.passportExpiry],
  section("Education"),
  ["School name", caseData.school, "Degree", caseData.degree],
  ["Major field", "Computer Science", "Graduation date", caseData.graduationDate],
  section("Employment history"),
  ["Employer", caseData.priorEmployer, "Period", caseData.priorEmploymentPeriod],
  ["Duties", "Python ETL scripts, SQL validation, dashboard back-end support", "", ""],
  section("Entry plan"),
  ["Application type", "certificate_of_eligibility", "Purpose of entry", "技術・人文知識・国際業務"],
  ["Planned entry date", caseData.plannedEntryDate, "Planned port", caseData.plannedPort],
  ["Planned period years", caseData.plannedPeriodYears, "Planned period months", caseData.plannedPeriodMonths],
  section("Japan contact"),
  ["Postal code", caseData.japanContactPostalCode, "Phone", caseData.japanContactPhone],
  ["Address", caseData.japanContactAddress, "", ""],
  section("Immigration history"),
  ["Prior entries count", caseData.priorEntriesCount, "Prior COE applications", caseData.priorCoeCount],
  ["Criminal record", false, "Deportation or departure order", false],
  section("Family"),
  ["Accompanying family members", caseData.hasAccompanyingMembers, "Japan relatives or cohabitants", caseData.hasJapanRelativesOrCohabitants],
  section("Employer"),
  ["Employer name", caseData.employerName, "Employer name english", caseData.employerNameEn],
  ["Corporate number", caseData.employerNumber, "Postal code", caseData.employerPostalCode],
  ["Address", caseData.employerAddress, "Phone", caseData.employerPhone],
  section("Employment terms"),
  ["Start date", caseData.startDate, "Contract type", caseData.contractType],
  ["Employment period type", caseData.employmentPeriodType, "Monthly salary", caseData.monthlySalary],
  ["Employment period years", caseData.employmentPeriodYears, "Employment period months", caseData.employmentPeriodMonths],
  ["Job category primary", caseData.jobCategoryPrimary, "", ""],
  [
    "Activity details",
    "Develops AI-assisted data processing tools, prepares dataset quality reports, implements Python and SQL workflows, and coordinates technical specifications with product and client teams.",
    "",
    "",
  ],
];

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Applicant intake");
sheet.showGridLines = false;

const used = sheet.getRangeByIndexes(0, 0, rows.length, 4);
used.values = rows;
used.format.font = { name: "Arial", size: 10, color: "#111827" };
used.format.wrapText = true;
used.format.verticalAlignment = "center";

for (const address of ["B24", "D24", "B33", "D33", "D34"]) {
  sheet.getRange(address).setNumberFormat("0");
}


sheet.getRange("A1:D1").merge();
sheet.getRange("A1:D1").format.font = { name: "Arial", size: 16, bold: true, color: "#111827" };
sheet.getRange("A1:D1").format.rowHeightPx = 34;

sheet.getRange("A2:D2").format = {
  fill: "#FEE2E2",
  font: { name: "Arial", size: 10, bold: true, color: "#991B1B" },
};

for (let r = 4; r <= rows.length; r += 1) {
  const firstCell = rows[r - 1][0];
  if (
    [
      "Applicant identity",
      "Passport",
      "Education",
      "Employment history",
      "Entry plan",
      "Japan contact",
      "Immigration history",
      "Family",
      "Employer",
      "Employment terms",
    ].includes(firstCell)
  ) {
    const rowRange = sheet.getRange(`A${r}:D${r}`);
    rowRange.format = {
      fill: "#1F2937",
      font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
    };
  }
}

sheet.getRange("A3:D40").format.borders = { preset: "all", style: "thin", color: "#D9D9D9" };
sheet.getRange(`A1:A${rows.length}`).format.columnWidth = 26;
sheet.getRange(`B1:B${rows.length}`).format.columnWidth = 48;
sheet.getRange(`C1:C${rows.length}`).format.columnWidth = 26;
sheet.getRange(`D1:D${rows.length}`).format.columnWidth = 42;
sheet.getRange("B37").setNumberFormat("#,##0");
sheet.freezePanes.freezeRows(3);

workbook.recalculate();

const inspect = await workbook.inspect({
  kind: "table",
  range: `Applicant intake!A1:D${rows.length}`,
  include: "values,formulas",
  tableMaxRows: rows.length,
  tableMaxCols: 4,
});
console.log(`Workbook inspect completed for Applicant intake A1:D${rows.length}.`);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 50 },
  summary: "final formula error scan",
});
console.log(errors.ndjson || "Formula error scan completed with no matches.");

if (previewPath) {
  await fs.mkdir(path.dirname(previewPath), { recursive: true });
  const preview = await workbook.render({
    sheetName: "Applicant intake",
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
