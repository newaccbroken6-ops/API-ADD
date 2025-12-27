import { createCipheriv, createDecipheriv } from 'crypto';

// Protobuf mock implementation since we can't use Python protobuf in Node.js
// Using a simplified approach for the Vercel deployment

// Encryption setup
const key = Buffer.from([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56]);
const iv = Buffer.from([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37]);
const freefire_version = "OB51";

// Function to decode JWT without verification
function decodeJwt(token) {
  try {
    const parts = token.split('.');
    if (parts.length < 2) {
      return null;
    }
    const payloadB64 = parts[1] + "=".repeat((4 - parts[1].length % 4) % 4); // padding fix
    const payload = JSON.parse(Buffer.from(payloadB64, 'base64').toString());
    return payload;
  } catch (e) {
    return null;
  }
}

// Function to get server URL based on region
function getServerUrl(lockRegion) {
  const region = lockRegion.toUpperCase();
  
  // Region to URL mapping
  const regionMap = {
    "IND": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",  // Indonesia
    "ME": "https://clientbp.ggblueshark.com/SetPlayerGalleryShowInfo",   // Middle East
    "VN": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   // Vietnam
    "BD": "https://clientbp.ggwhitehawk.com/SetPlayerGalleryShowInfo",   // Bangladesh
    "PK": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   // Pakistan
    "SG": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   // Singapore
    "BR": "https://client.us.freefiremobile.com/SetPlayerGalleryShowInfo", // Brazil
    "NA": "https://client.us.freefiremobile.com/SetPlayerGalleryShowInfo", // North America
    "ID": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   // Indonesia
    "RU": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   // Russia
    "TH": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   // Thailand
    "TW": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo"    // Taiwan
  };
  
  // If region mapping exists, use that URL
  if (region in regionMap) {
    return regionMap[region];
  } else {
    // Default URL for all other regions
    return "https://client.ind.freefiremobile.com/SetPlayerGalleryShowInfo";
  }
}

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

  const { token, itemid } = req.query;

  if (!token || !itemid) {
    return res.status(400).json({
      status: false,
      message: "Missing token or itemid parameter"
    });
  }

  // Decode JWT to get lock_region
  const payload = decodeJwt(token);
  if (!payload) {
    return res.status(400).json({
      status: false,
      message: "Invalid JWT token"
    });
  }

  const lockRegion = payload.lock_region || "IND";
  const url = getServerUrl(lockRegion);

  // Process item IDs
  const itemIds = itemid.split('/').slice(0, 15);
  if (!itemIds.length) {
    return res.status(400).json({
      status: false,
      message: "At least one item ID required"
    });
  }

  // For Vercel deployment, we'll create a simplified encrypted payload
  // In a real implementation, you'd need to properly implement the protobuf serialization
  // For now, we'll create a mock encrypted payload
  
  // Create a mock encrypted data (in a real implementation, this would be the protobuf data)
  const mockData = JSON.stringify({
    field_1: 1,
    field_2: itemIds.map((id, index) => ({
      field_1: index % 2 === 0 ? 2 : 13,
      field_4: 1,
      field_6: { field_6: parseInt(id) || 0 }
    }))
  });

  // Encrypt the mock data
  const cipher = createCipheriv('aes-128-cbc', key, iv);
  let encryptedData = cipher.update(mockData, 'utf8', 'binary');
  encryptedData += cipher.final('binary');
  const encryptedBuffer = Buffer.from(encryptedData, 'binary');

  const headers = {
    "Authorization": `Bearer ${token}`,
    "X-Unity-Version": "2018.4.11f1",
    "X-GA": "v1 1",
    "ReleaseVersion": freefire_version,
    "Content-Type": "application/octet-stream",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
    "Accept-Encoding": "gzip"
  };

  try {
    // Make request to the actual Free Fire server
    const externalResponse = await fetch(url, {
      method: 'POST',
      headers: headers,
      body: encryptedBuffer
    });

    const currentTime = Math.floor(Date.now() / 1000);
    const addProfileList = itemIds.map((itemId, index) => ({
      add_time: currentTime,
      [`item_id${index + 1}`]: parseInt(itemId)
    }));

    if (externalResponse.status === 200) {
      return res.status(200).json({
        message: "Item added to profile",
        status: true,
        lock_region: lockRegion,
        server_used: url,
        "Add-profile": addProfileList,
        response_code: externalResponse.status
      });
    } else {
      const errorText = await externalResponse.text();
      return res.status(400).json({
        status: false,
        message: `External server returned status ${externalResponse.status}`,
        lock_region: lockRegion,
        server_used: url,
        external_response: errorText,
        request_size: encryptedBuffer.length,
        response_code: externalResponse.status
      });
    }
  } catch (error) {
    return res.status(500).json({
      status: false,
      message: `External request failed: ${error.message}`
    });
  }
}