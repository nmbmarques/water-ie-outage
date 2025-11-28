// server.js
const express = require("express");
const axios = require("axios");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3000;

const BASE_URL =
  "https://services2.arcgis.com/OqejhVam51LdtxGa/arcgis/rest/services/WaterAdvisoryCR021_DeptView/FeatureServer/0/query";

// Serve static frontend
app.use(express.static(path.join(__dirname, "public")));

// Helpers
function stripHtml(html) {
  if (!html) return "";
  let text = html.replace(/<br\s*\/?>/gi, "\n");
  text = text.replace(/<\/div\s*>/gi, "\n");
  text = text.replace(/<.*?>/g, "");
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .join("\n");
}

function extractReference(description) {
  if (!description) return null;
  const match = description.match(/\b[A-Z]{3}\d{8}\b/);
  return match ? match[0] : null;
}

function formatDate(epoch) {
  if (!epoch && epoch !== 0) return null;
  const d = new Date(epoch);
  if (Number.isNaN(d.getTime())) return null;
  // You can change this format if you want
  return d.toLocaleString("en-IE", { timeZone: "Europe/Dublin" });
}

function normalizeOutage(props) {
  const rawDesc = props.DESCRIPTION || "";
  const plainDesc = stripHtml(rawDesc);
  const reference = props.REFERENCENUM || extractReference(plainDesc);

  return {
    objectid: props.OBJECTID,
    globalid: props.GLOBALID,
    title: props.TITLE || "",
    status: props.STATUS || "",
    location: props.LOCATION || "",
    county: props.COUNTY || "",
    startdate_epoch: props.STARTDATE || null,
    enddate_epoch: props.ENDDATE || null,
    startdate_human: formatDate(props.STARTDATE),
    enddate_human: formatDate(props.ENDDATE),
    reference: reference,
    description: plainDesc,
  };
}

// API route: /api/outages?county=Mayo&refnum=MAY00102991&location=Ballina
app.get("/api/outages", async (req, res) => {
  const county = req.query.county;
  const refnum = (req.query.refnum || "").trim() || null;
  const locationFilter = (req.query.location || "").trim().toLowerCase();

  if (!county) {
    return res.status(400).json({ error: "Missing required parameter: county" });
  }

  const where = `STATUS='Open' AND APPROVALSTATUS='Approved' AND COUNTY='${county}'`;

  const params = {
    f: "json",
    where,
    outFields: "*",
    returnGeometry: "true",
    returnIdsOnly: "false",
    orderByFields: "STARTDATE DESC",
    outSR: "4326",
  };

  try {
    const response = await axios.get(BASE_URL, { params });
    const data = response.data || {};
    const features = data.features || [];

    let outages = features.map((f) =>
      normalizeOutage(f.properties || f.attributes || {})
    );

    // Filter by reference number (if provided)
    if (refnum) {
      outages = outages.filter((o) => o.reference === refnum);
    }

    // Filter by location substring (Ballina)
    if (locationFilter) {
      outages = outages.filter((o) => {
        const loc = (o.location || "").toLowerCase();
        const desc = (o.description || "").toLowerCase();
        return loc.includes(locationFilter) || desc.includes(locationFilter);
      });
    }

    res.json({
      county,
      refnum: refnum || null,
      locationFilter: locationFilter || null,
      count: outages.length,
      outages,
    });
  } catch (err) {
    console.error("Error fetching outages:", err.message);
    res.status(500).json({
      error: "Failed to fetch outage data",
      details: err.message,
    });
  }
});

app.listen(PORT, () => {
  console.log(`Water outage web app listening on port ${PORT}`);
});
