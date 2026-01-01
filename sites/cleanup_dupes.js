const fs = require('fs');
const path = require('path');

const INDEX_FILE = 'recordings/recordings_index.json';

function cleanup() {
  if (!fs.existsSync(INDEX_FILE)) {
    console.log('Index file not found.');
    return;
  }

  const index = JSON.parse(fs.readFileSync(INDEX_FILE, 'utf8'));
  const seen = new Set();
  const uniqueRecordings = {};
  const toDelete = [];

  console.log(`Initial entries: ${Object.keys(index.recordings).length}`);

  Object.entries(index.recordings).forEach(([id, r]) => {
    const norm = (r.url || '').trim().replace(/\/$/, '');
    if (seen.has(norm)) {
      toDelete.push(id);
    } else {
      seen.add(norm);
      uniqueRecordings[id] = r;
    }
  });

  index.recordings = uniqueRecordings;
  fs.writeFileSync(INDEX_FILE, JSON.stringify(index, null, 2));

  toDelete.forEach(id => {
    const file = path.join('recordings', `${id}.json`);
    if (fs.existsSync(file)) {
      fs.unlinkSync(file);
    }
  });

  console.log(`Cleaned up ${toDelete.length} duplicates.`);
  console.log(`Remaining entries: ${Object.keys(index.recordings).length}`);
}

cleanup();
