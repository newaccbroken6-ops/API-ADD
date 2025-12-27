export default function handler(req, res) {
  // Handle CORS
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  const regions = {
    "IND": "India",
    "BR": "Brazil", 
    "US": "United States",
    "SAC": "South America",
    "NA": "North America",
    "BD": "Bangladesh",
    "SG": "Singapore",
    "ME": "Middle East",
    "PK": "Pakistan",
    "EU": "Europe",
    "ID": "Indonesia",
    "VN": "Vietnam",
    "TH": "Thailand",
    "PH": "Philippines",
    "MY": "Malaysia",
    "TR": "Turkey",
    "RU": "Russia",
    "TW": "Taiwan",
    "DEFAULT": "Other Regions"
  };

  res.status(200).json({
    status: true,
    regions: regions
  });
}