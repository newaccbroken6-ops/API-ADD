export default async function handler(req, res) {
  // Handle CORS
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  const { eat_token } = req.query;

  if (!eat_token) {
    return res.status(400).json({
      error: "EAT token is required"
    });
  }

  try {
    // Make request to the external service
    const externalUrl = `https://danger-access-token.vercel.app/eat-to-access?eat_token=${encodeURIComponent(eat_token)}`;
    const response = await fetch(externalUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });

    const data = await response.json();
    
    // Return the response from the external service
    res.status(response.status).json(data);
    
  } catch (error) {
    res.status(500).json({
      error: `Failed to retrieve access token: ${error.message}`
    });
  }
}